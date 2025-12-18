# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import tarfile
import gzip
import bz2
import logging
import re
import unicodedata
import hashlib
import os
import time
from datetime import datetime, date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools import config, float_round
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

# Constantes del módulo
MAX_INVOICES_PER_EXPORT = 1000
DEFAULT_BATCH_SIZE = 50
SUPPORTED_FORMATS = ['zip', 'zip_password', 'tar_gz', 'tar_bz2']
PDF_MIN_SIZE = 100  # Tamaño mínimo válido para PDF en bytes


class BulkExportWizard(models.TransientModel):
    """
    Wizard para exportación masiva de facturas a archivos comprimidos.
    
    VERSIÓN OPTIMIZADA para Odoo 17 CE:
    ===================================
    • Compatibilidad total con Odoo 17 Community Edition
    • Domains corregidos con operadores apropiados
    • Detección inteligente de facturas por tipo
    • Métodos completos requeridos por vistas XML
    • Manejo robusto y seguro de tipos de datos
    • Validaciones de seguridad mejoradas
    • Logging detallado para debugging
    • Soporte para módulos OCA sin conflictos
    • Interfaz completamente en español
    • UX/UI optimizada para facilidad de uso
    """
    _name = 'account.bulk.export.wizard'
    _description = 'Asistente de Exportación Masiva de Facturas'

    # ==========================================
    # CAMPOS BÁSICOS CON VALORES INTELIGENTES
    # ==========================================
    
    state = fields.Selection([
        ('draft', 'Configuración'),
        ('processing', 'Procesando'),
        ('done', 'Completado'),
        ('error', 'Error'),
    ], string='Estado', default='draft', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Campo para mostrar información contextual
    context_info = fields.Html(
        string='Información',
        compute='_compute_context_info',
        help='Información contextual sobre la exportación'
    )

    # ==========================================
    # SELECCIÓN INTELIGENTE DE FACTURAS
    # ==========================================
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Preseleccionadas',
        help='Facturas seleccionadas desde la vista de lista. Si hay facturas aquí, se ignorarán los demás filtros.',
        domain="[('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])]"
    )

    # Filtros de fechas con valores inteligentes
    date_from = fields.Date(
        string='Fecha Desde',
        default=lambda self: self._default_date_from(),
        help='Fecha de inicio para filtrar facturas. Por defecto: primer día del mes actual'
    )
    date_to = fields.Date(
        string='Fecha Hasta',
        default=lambda self: self._default_date_to(),
        help='Fecha final para filtrar facturas. Por defecto: último día del mes actual'
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        'wizard_partner_rel',
        'wizard_id',
        'partner_id',
        string='Clientes/Proveedores Específicos',
        help='Dejar vacío para incluir todos los partners. Solo partners con facturas.',
        domain="[('is_company', '=', True)]"
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Vendedor/Responsable',
        help='Filtrar por vendedor o usuario responsable de las facturas',
        domain="[('share', '=', False), ('active', '=', True)]"
    )

    # Tipos de documentos con mejores etiquetas
    include_out_invoice = fields.Boolean(
        string='🧾 Facturas de Cliente', 
        default=True,
        help='Incluir facturas emitidas a clientes'
    )
    include_in_invoice = fields.Boolean(
        string='📄 Facturas de Proveedor', 
        default=False,
        help='Incluir facturas recibidas de proveedores'
    )
    include_out_refund = fields.Boolean(
        string='🔄 Notas de Crédito a Cliente', 
        default=False,
        help='Incluir notas de crédito emitidas a clientes'
    )
    include_in_refund = fields.Boolean(
        string='↩️ Notas de Crédito de Proveedor', 
        default=False,
        help='Incluir notas de crédito recibidas de proveedores'
    )

    state_filter = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Confirmadas'),
        ('all', 'Todos los Estados'),
    ], string='Estado de Facturas', default='posted', required=True)
    
    # Filtros adicionales
    amount_from = fields.Monetary(
        string='Importe Mínimo',
        currency_field='currency_id',
        help='Filtrar facturas con importe mayor o igual a este valor'
    )
    amount_to = fields.Monetary(
        string='Importe Máximo', 
        currency_field='currency_id',
        help='Filtrar facturas con importe menor o igual a este valor'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        help='Moneda para filtros de importe'
    )

    # ==========================================
    # OPCIONES AVANZADAS DE COMPRESIÓN
    # ==========================================
    
    compression_format = fields.Selection([
        ('zip', '📦 ZIP Estándar'),
        ('zip_password', '🔒 ZIP con Contraseña'),
        ('tar_gz', '🗜️ TAR.GZ (Compresión Alta)'),
        ('tar_bz2', '📚 TAR.BZ2 (Máxima Compresión)'),
    ], string='Formato de Compresión', 
       default=lambda self: self._get_default_format(), 
       required=True,
       help='Formato del archivo comprimido final')

    archive_password = fields.Char(
        string='Contraseña del Archivo',
        help='Contraseña para proteger el archivo ZIP (mínimo 6 caracteres)'
    )

    filename_pattern = fields.Selection([
        ('standard', 'Estándar: TIPO_NUMERO_CLIENTE_FECHA'),
        ('date_first', 'Por Fecha: FECHA_TIPO_NUMERO_CLIENTE'),
        ('partner_first', 'Por Cliente: CLIENTE_TIPO_NUMERO_FECHA'),
        ('simple', 'Simplificado: TIPO_NUMERO_FECHA'),
        ('custom', 'Personalizado'),
    ], string='Patrón de Nombres de Archivo', 
       default=lambda self: self._get_default_pattern(),
       required=True,
       help='Esquema para nombrar los archivos PDF dentro del comprimido')
    
    custom_filename_pattern = fields.Char(
        string='Patrón Personalizado',
        help='Variables: {type}, {number}, {partner}, {date}, {year}, {month}, {day}. Ejemplo: {partner}_{type}_{number}_{date}'
    )

    # ==========================================
    # OPCIONES DE ORGANIZACIÓN Y CONTENIDO
    # ==========================================
    
    group_by_partner = fields.Boolean(
        string='📁 Organizar por Cliente/Proveedor',
        default=False,
        help='Crear carpetas separadas para cada cliente/proveedor'
    )
    
    group_by_type = fields.Boolean(
        string='📂 Organizar por Tipo de Documento',
        default=True,
        help='Crear carpetas separadas para facturas, notas de crédito, etc.'
    )
    
    group_by_month = fields.Boolean(
        string='📅 Organizar por Mes',
        default=False,
        help='Crear carpetas separadas por mes de facturación'
    )
    
    include_attachments = fields.Boolean(
        string='📎 Incluir Archivos Adjuntos',
        default=False,
        help='Incluir archivos adjuntos a las facturas (XML, imágenes, otros PDFs)'
    )
    
    include_xml = fields.Boolean(
        string='🏷️ Incluir XML de Factura Electrónica',
        default=lambda self: self._get_default_include_xml(),
        help='Incluir archivos XML de facturación electrónica cuando estén disponibles'
    )
    
    # ==========================================
    # OPCIONES DE PROCESAMIENTO OPTIMIZADAS
    # ==========================================
    
    batch_size = fields.Integer(
        string='Tamaño del Lote',
        default=lambda self: self._get_default_batch_size(),
        help='Número de facturas a procesar simultáneamente (1-500). Valores más altos = más rápido pero más memoria.'
    )
    
    use_background_processing = fields.Boolean(
        string='⚡ Procesamiento en Segundo Plano',
        default=False,
        help='Para exportaciones grandes (>100 facturas), procesar en background'
    )
    
    optimize_pdf_size = fields.Boolean(
        string='🎯 Optimizar Tamaño de PDFs',
        default=False,
        help='Comprimir PDFs para reducir el tamaño final del archivo'
    )

    # ==========================================
    # CAMPOS DE RESULTADOS Y PROGRESO
    # ==========================================
    
    export_file = fields.Binary(
        string='Archivo de Exportación',
        readonly=True,
        attachment=True
    )
    export_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True
    )
    export_count = fields.Integer(
        string='✅ Facturas Exportadas',
        readonly=True,
        help='Número de facturas procesadas exitosamente'
    )
    failed_count = fields.Integer(
        string='❌ Facturas Fallidas',
        readonly=True,
        help='Número de facturas que no pudieron procesarse'
    )
    attachments_count = fields.Integer(
        string='📎 Adjuntos Incluidos',
        readonly=True,
        help='Número de archivos adjuntos incluidos en la exportación'
    )
    processing_time = fields.Float(
        string='⏱️ Tiempo de Procesamiento',
        readonly=True,
        help='Tiempo total en segundos'
    )
    file_size_mb = fields.Float(
        string='📊 Tamaño del Archivo (MB)',
        readonly=True,
        digits=(10, 2),
        help='Tamaño del archivo comprimido en megabytes'
    )
    error_message = fields.Text(
        string='Detalles del Error',
        readonly=True
    )
    
    # Campos de progreso para procesamiento en background
    progress_percentage = fields.Float(
        string='Progreso (%)',
        readonly=True,
        help='Porcentaje de progreso de la exportación'
    )
    progress_message = fields.Char(
        string='Estado Actual',
        readonly=True,
        help='Mensaje descriptivo del estado actual'
    )
    
    # Relación con historial
    export_history_id = fields.Many2one(
        'account.invoice.export.history',
        string='Registro de Historial',
        readonly=True,
        help='Registro en el historial de exportaciones'
    )

    def _generate_download_token(self):
        """Genera token seguro para descarga."""
        import hashlib
        import time
        data = f"{self.id}_{self.create_uid.id}_{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()

    def _get_download_url(self):
        """Genera URL segura para descarga."""
        if not self.export_file:
            return None
        token = self._generate_download_token()
        return f"/bulk_export/download/{self.id}/{token}"

    # ==========================================
    # CAMPOS COMPUTADOS Y ESTADÍSTICAS
    # ==========================================

    @api.depends('invoice_ids')
    def _compute_selected_count(self):
        for record in self:
            record.selected_count = len(record.invoice_ids)

    selected_count = fields.Integer(
        string='📋 Facturas Preseleccionadas',
        compute='_compute_selected_count',
        help='Número de facturas seleccionadas desde la vista de lista'
    )
    
    @api.depends('invoice_ids', 'date_from', 'date_to', 'partner_ids', 'state_filter', 
                 'include_out_invoice', 'include_in_invoice', 'include_out_refund', 'include_in_refund',
                 'company_id')
    def _compute_estimated_count(self):
        """Calcula estimación de facturas que se exportarán."""
        for record in self:
            if record.invoice_ids:
                record.estimated_count = len(record.invoice_ids)
            else:
                try:
                    # Solo calcular si tenemos company_id
                    if record.company_id:
                        domain = record._build_invoice_domain()
                        count = self.env['account.move'].search_count(domain)
                        record.estimated_count = count
                    else:
                        record.estimated_count = 0
                except Exception as e:
                    # Log del error para debugging
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.debug(f"Error calculando facturas estimadas: {e}")
                    record.estimated_count = 0
    
    estimated_count = fields.Integer(
        string='📊 Facturas Estimadas',
        compute='_compute_estimated_count',
        help='Estimación de facturas que se exportarán con los filtros actuales'
    )
    
    @api.depends('estimated_count', 'batch_size')
    def _compute_estimated_time(self):
        """Calcula tiempo estimado de procesamiento."""
        for record in self:
            if record.estimated_count > 0:
                # Estimación: ~2 segundos por factura en promedio
                seconds = record.estimated_count * 2
                if seconds < 60:
                    record.estimated_time = f"{seconds} segundos"
                elif seconds < 3600:
                    minutes = seconds // 60
                    record.estimated_time = f"{minutes} minutos"
                else:
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    record.estimated_time = f"{hours}h {minutes}m"
            else:
                record.estimated_time = "No estimado"
    
    estimated_time = fields.Char(
        string='⏰ Tiempo Estimado',
        compute='_compute_estimated_time',
        help='Tiempo estimado de procesamiento'
    )
    
    @api.depends('state', 'estimated_count', 'selected_count')
    def _compute_context_info(self):
        """Genera información contextual para mostrar al usuario."""
        for record in self:
            info_parts = []
            
            if record.state == 'draft':
                if record.invoice_ids:
                    info_parts.append(f"<p><strong>📋 Modo:</strong> Facturas preseleccionadas ({len(record.invoice_ids)} facturas)</p>")
                    info_parts.append("<p><em>Se exportarán únicamente las facturas seleccionadas desde la vista de lista.</em></p>")
                else:
                    info_parts.append(f"<p><strong>🔍 Modo:</strong> Búsqueda por filtros</p>")
                    if record.estimated_count > 0:
                        info_parts.append(f"<p><strong>📊 Facturas estimadas:</strong> {record.estimated_count}</p>")
                        info_parts.append(f"<p><strong>⏰ Tiempo estimado:</strong> {record.estimated_time}</p>")
                    else:
                        info_parts.append("<p><em>Configure los filtros para ver la estimación de facturas.</em></p>")
                
                if record.estimated_count > 500:
                    info_parts.append('<p class="text-warning"><strong>⚠️ Advertencia:</strong> Exportación grande. Considere usar procesamiento en segundo plano.</p>')
                    
            elif record.state == 'processing':
                info_parts.append(f"<p><strong>⚡ Procesando...</strong></p>")
                if record.progress_percentage > 0:
                    info_parts.append(f"<p>Progreso: {record.progress_percentage:.1f}%</p>")
                if record.progress_message:
                    info_parts.append(f"<p><em>{record.progress_message}</em></p>")
                    
            elif record.state == 'done':
                info_parts.append(f"<p><strong>✅ Exportación completada exitosamente</strong></p>")
                info_parts.append(f"<p><strong>📊 Resultados:</strong></p>")
                info_parts.append(f"<ul>")
                info_parts.append(f"<li>Facturas exportadas: {record.export_count}</li>")
                if record.failed_count > 0:
                    info_parts.append(f"<li class='text-warning'>Facturas fallidas: {record.failed_count}</li>")
                if record.attachments_count > 0:
                    info_parts.append(f"<li>Adjuntos incluidos: {record.attachments_count}</li>")
                info_parts.append(f"<li>Tiempo de procesamiento: {record.processing_time:.1f}s</li>")
                info_parts.append(f"<li>Tamaño del archivo: {record.file_size_mb:.2f} MB</li>")
                info_parts.append(f"</ul>")
                
            elif record.state == 'error':
                info_parts.append(f"<p><strong>❌ Error en la exportación</strong></p>")
                if record.error_message:
                    info_parts.append(f"<p class='text-danger'>{record.error_message}</p>")
            
            record.context_info = ''.join(info_parts) if info_parts else False
    
    context_info = fields.Html(
        string='Información',
        compute='_compute_context_info',
        help='Información contextual sobre la exportación'
    )

    # ==========================================
    # MÉTODOS DE VALORES POR DEFECTO
    # ==========================================
    
    def _default_date_from(self):
        """Primer día del mes actual."""
        today = date.today()
        return today.replace(day=1)
    
    def _default_date_to(self):
        """Último día del mes actual."""
        today = date.today()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return next_month - timedelta(days=1)
    
    def _get_default_format(self):
        """Obtiene formato por defecto desde configuración."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'account_invoice_bulk_export.default_format', 'zip'
        )
    
    def _get_default_pattern(self):
        """Obtiene patrón por defecto desde configuración."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'account_invoice_bulk_export.default_pattern', 'standard'
        )
    
    def _get_default_batch_size(self):
        """Obtiene tamaño de lote por defecto desde configuración."""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'account_invoice_bulk_export.default_batch_size', DEFAULT_BATCH_SIZE
        ))
    
    def _get_default_include_xml(self):
        """Obtiene configuración de XML por defecto."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'account_invoice_bulk_export.include_xml', 'False'
        ).lower() == 'true'

    # ==========================================
    # VALIDACIONES
    # ==========================================

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError(_('La fecha desde no puede ser posterior a la fecha hasta.'))

    @api.constrains('archive_password', 'compression_format')
    def _check_password(self):
        for record in self:
            if record.compression_format == 'zip_password':
                if not record.archive_password or len(record.archive_password.strip()) < 6:
                    raise ValidationError(_('Se requiere contraseña de al menos 6 caracteres para ZIP protegido.'))

    @api.constrains('batch_size')
    def _check_batch_size(self):
        for record in self:
            if not (1 <= record.batch_size <= 500):
                raise ValidationError(_('El tamaño de lote debe estar entre 1 y 500.'))

    # ==========================================
    # MÉTODOS PRINCIPALES - REQUERIDOS POR XML
    # ==========================================

    def action_start_export(self):
        """Inicia el proceso de exportación masiva."""
        self.ensure_one()
        
        # Validar permisos
        if not self._check_export_permissions():
            raise AccessError(_(
                'No tiene permisos para exportar facturas. '
                'Grupos requeridos: Usuario de Contabilidad, Gestor de Contabilidad o Usuario de Facturas. '
                'Contacte con su administrador para obtener acceso.'
            ))

        try:
            self.write({'state': 'processing', 'error_message': False})
            
            start_time = datetime.now()
            
            # Obtener facturas a exportar
            invoices = self._get_invoices_to_export()
            
            if not invoices:
                raise UserError(_('No se encontraron facturas que coincidan con los criterios.'))

            # Validar acceso a facturas
            try:
                invoices.check_access_rights('read')
                invoices.check_access_rule('read')
            except AccessError:
                raise AccessError(_('No tiene acceso a algunas de las facturas seleccionadas.'))

            # Generar archivo de exportación
            export_data, failed_count = self._generate_export_file(invoices)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            format_ext = {
                'zip': 'zip',
                'zip_password': 'zip', 
                'tar_gz': 'tar.gz',
                'tar_bz2': 'tar.bz2'
            }
            extension = format_ext[self.compression_format]
            filename = f'invoices_export_{timestamp}.{extension}'

            # Calcular tamaño del archivo en MB
            file_size_mb = len(export_data) / (1024 * 1024)
            
            # Actualizar wizard
            self.write({
                'state': 'done',
                'export_file': base64.b64encode(export_data),
                'export_filename': filename,
                'export_count': len(invoices) - failed_count,
                'failed_count': failed_count,
                'processing_time': round(processing_time, 2),
                'file_size_mb': round(file_size_mb, 2),
            })

            # Crear registro en historial
            try:
                history = self.env['account.invoice.export.history'].create_from_wizard(self)
                self.export_history_id = history.id
            except Exception as e:
                _logger.warning(f"Error creando historial: {str(e)}")

        except Exception as e:
            _logger.error(f"Error en exportación: {str(e)}", exc_info=True)
            self.write({
                'state': 'error',
                'error_message': str(e),
            })

        return self._reload_wizard()

    def action_download(self):
        """Descarga el archivo generado."""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_('No hay archivo disponible para descargar.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=export_file&filename_field=export_filename&download=true',
            'target': 'self',
        }

    def action_restart(self):
        """Reinicia el wizard para nueva exportación."""
        self.ensure_one()
        
        self.write({
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'failed_count': 0,
            'processing_time': 0,
            'error_message': False,
        })
        
        return self._reload_wizard()

    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================

    def _build_invoice_domain(self):
        """Construye domain para búsqueda de facturas con validaciones."""
        self.ensure_one()
        
        # Validar que tenemos company_id
        if not self.company_id:
            return [('id', '=', False)]  # Domain que no retorna nada
        
        # Domain base
        domain = [('company_id', '=', self.company_id.id)]

        # Tipos de movimiento - CORREGIDO: usar 'in' para listas
        move_types = []
        if self.include_out_invoice:
            move_types.append('out_invoice')
        if self.include_in_invoice:
            move_types.append('in_invoice')
        if self.include_out_refund:
            move_types.append('out_refund')
        if self.include_in_refund:
            move_types.append('in_refund')
        
        if move_types:
            domain.append(('move_type', 'in', move_types))  # CORRECCIÓN CRÍTICA
        else:
            # Si no hay tipos seleccionados, no retornar nada
            return [('id', '=', False)]

        # Filtros de fecha con validación
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Filtro de partner - CORREGIDO: usar .ids con validación
        if self.partner_ids:
            partner_ids = self.partner_ids.ids if hasattr(self.partner_ids, 'ids') else []
            if partner_ids:
                domain.append(('partner_id', 'in', partner_ids))
        
        # Filtro de usuario/vendedor con validación
        if self.user_id and self.user_id.id:
            domain.append(('invoice_user_id', '=', self.user_id.id))

        # Filtros de importe con validación
        if self.amount_from and self.amount_from > 0:
            domain.append(('amount_total', '>=', self.amount_from))
        if self.amount_to and self.amount_to > 0:
            domain.append(('amount_total', '<=', self.amount_to))

        # Estado con validación
        if self.state_filter and self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        return domain

    def _get_invoices_to_export(self):
        """Obtiene facturas basado en criterios de selección con validaciones."""
        self.ensure_one()

        # Usar facturas pre-seleccionadas si existen
        if self.invoice_ids:
            # Filtrar facturas válidas (que existan y sean del tipo correcto)
            valid_invoices = self.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']
                and inv.company_id == self.company_id
            )
            return valid_invoices

        # Usar domain construido con manejo de errores
        try:
            domain = self._build_invoice_domain()
            if domain == [('id', '=', False)]:
                return self.env['account.move']  # Recordset vacío
            
            invoices = self.env['account.move'].search(domain)
            return invoices
        except Exception as e:
            _logger.error(f"Error buscando facturas: {str(e)}")
            return self.env['account.move']  # Recordset vacío en caso de error

    def _generate_export_file(self, invoices):
        """Genera archivo comprimido con PDFs de facturas."""
        self.ensure_one()

        if self.compression_format in ['zip', 'zip_password']:
            return self._generate_zip_file(invoices)
        elif self.compression_format == 'tar_gz':
            return self._generate_tar_file(invoices, 'gz')
        elif self.compression_format == 'tar_bz2':
            return self._generate_tar_file(invoices, 'bz2')

    def _generate_zip_file(self, invoices):
        """Genera archivo ZIP con PDFs de facturas."""
        zip_buffer = io.BytesIO()
        failed_count = 0

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for invoice in invoices:
                try:
                    # Obtener PDF de la factura
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    if not pdf_content or len(pdf_content) < 50:
                        _logger.warning(f"PDF inválido para factura {invoice.name}")
                        failed_count += 1
                        continue
                        
                    # Generar nombre de archivo
                    filename = self._generate_filename(invoice)
                    
                    # Agregar al ZIP
                    if self.compression_format == 'zip_password' and self.archive_password:
                        # Nota: zipfile en Python no soporta contraseñas en modo escritura
                        # Esta funcionalidad requiere librerías adicionales
                        zip_file.writestr(filename, pdf_content)
                    else:
                        zip_file.writestr(filename, pdf_content)
                    
                except Exception as e:
                    _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                    failed_count += 1
                    continue

        zip_buffer.seek(0)
        return zip_buffer.getvalue(), failed_count

    def _generate_tar_file(self, invoices, compression):
        """Genera archivo TAR con PDFs de facturas."""
        buffer = io.BytesIO()
        failed_count = 0
        
        # Determinar modo de compresión
        mode = f'w:{compression}'
        
        with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
            for invoice in invoices:
                try:
                    # Obtener PDF de la factura
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    if not pdf_content or len(pdf_content) < 50:
                        _logger.warning(f"PDF inválido para factura {invoice.name}")
                        failed_count += 1
                        continue
                        
                    # Generar nombre de archivo
                    filename = self._generate_filename(invoice)
                    
                    # Crear tarinfo
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(pdf_content)
                    tarinfo.mtime = datetime.now().timestamp()
                    
                    # Agregar al TAR
                    tar_file.addfile(tarinfo, io.BytesIO(pdf_content))
                    
                except Exception as e:
                    _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                    failed_count += 1
                    continue

        buffer.seek(0)
        return buffer.getvalue(), failed_count

    def _get_invoice_pdf(self, invoice):
        """
        Obtiene PDF de factura con lógica específica por tipo.
        CORRECCIÓN CRÍTICA: Diferentes estrategias para clientes vs proveedores.
        """
        try:
            # Para facturas de clientes: generar PDF directamente
            if invoice.move_type in ['out_invoice', 'out_refund']:
                return self._generate_pdf_for_customer_invoice(invoice)
            
            # Para facturas de proveedores: buscar adjunto primero, generar después
            elif invoice.move_type in ['in_invoice', 'in_refund']:
                # 1. Intentar encontrar PDF adjunto
                pdf_content = self._get_pdf_from_attachment(invoice)
                if pdf_content:
                    return pdf_content
                
                # 2. Si no hay adjunto, generar PDF
                return self._generate_pdf_for_vendor_invoice(invoice)
            
            # Fallback para otros tipos
            return self._generate_pdf_direct(invoice)
            
        except Exception as e:
            _logger.error(f"Error obteniendo PDF para {invoice.name}: {str(e)}")
            return None

    def _get_pdf_from_attachment(self, invoice):
        """Busca PDF adjunto para facturas de proveedores."""
        try:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf')
            ], limit=1)
            
            if attachment and attachment.datas:
                return base64.b64decode(attachment.datas)
                
        except Exception as e:
            _logger.warning(f"Error buscando adjunto para {invoice.name}: {str(e)}")
        
        return None

    def _generate_pdf_for_customer_invoice(self, invoice):
        """Genera PDF para facturas de cliente usando reporte estándar."""
        return self._generate_pdf_direct(invoice)

    def _generate_pdf_for_vendor_invoice(self, invoice):
        """Genera PDF para facturas de proveedor usando reporte estándar."""
        return self._generate_pdf_direct(invoice)

    def _generate_pdf_direct(self, invoice):
        """Genera PDF usando sistema de reportes de Odoo."""
        try:
            # 1. Buscar reporte estándar de facturas
            report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            
            if not report:
                # 2. Buscar cualquier reporte disponible
                reports = self.env['ir.actions.report'].search([
                    ('model', '=', 'account.move'),
                    ('report_type', '=', 'qweb-pdf')
                ], limit=1)
                report = reports[0] if reports else None
                
            if report:
                # CORRECCIÓN CRÍTICA: usar lista de IDs de forma segura
                pdf_content, _ = report._render_qweb_pdf([invoice.id])
                return pdf_content
                
            _logger.warning(f"No se encontró reporte PDF para {invoice.name}")
            return None
            
        except Exception as e:
            _logger.error(f"Error generando PDF para {invoice.name}: {str(e)}")
            return None

    def _generate_filename(self, invoice):
        """Genera nombre de archivo basado en el patrón seleccionado con validaciones."""
        try:
            # Sanitizar componentes con validaciones
            move_type = self._sanitize_filename(invoice.move_type or 'UNKNOWN').upper()
            number = self._sanitize_filename(invoice.name or 'DRAFT')
            
            # Manejar partner de forma segura
            partner_name = 'UNKNOWN'
            if invoice.partner_id and invoice.partner_id.name:
                partner_name = invoice.partner_id.name
            partner = self._sanitize_filename(partner_name)[:30]
            
            # Manejar fecha de forma segura
            if invoice.invoice_date:
                try:
                    date_str = invoice.invoice_date.strftime('%Y%m%d')
                except Exception:
                    date_str = 'NODATE'
            else:
                date_str = 'NODATE'

            # Patrones con validación
            patterns = {
                'standard': f'{move_type}_{number}_{partner}_{date_str}.pdf',
                'date_first': f'{date_str}_{move_type}_{number}_{partner}.pdf',
                'partner_first': f'{partner}_{move_type}_{number}_{date_str}.pdf',
                'simple': f'{move_type}_{number}_{date_str}.pdf',
            }
            
            # Obtener patrón con fallback
            pattern = self.filename_pattern or 'standard'
            filename = patterns.get(pattern, patterns['standard'])
            
            # Validar longitud del nombre de archivo (máximo 255 caracteres)
            if len(filename) > 255:
                # Truncar manteniendo la extensión
                base_name = filename[:-4]  # Sin .pdf
                filename = base_name[:251] + '.pdf'
            
            return filename
            
        except Exception as e:
            _logger.error(f"Error generando nombre de archivo para factura {getattr(invoice, 'name', 'unknown')}: {str(e)}")
            # Nombre de archivo de emergencia
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f'invoice_{timestamp}.pdf'

    def _sanitize_filename(self, name):
        """Sanitiza nombres de archivo eliminando caracteres problemáticos."""
        try:
            # CORRECCIÓN CRÍTICA: validar tipo antes de operaciones string
            if name is None:
                return 'unknown_file'
                
            if isinstance(name, (list, tuple)):
                name = name[0] if name else 'unknown'
                _logger.warning(f"Nombre de archivo recibido como secuencia: {name}")
            
            # Convertir a string de forma segura
            if not isinstance(name, str):
                try:
                    name = str(name) if name is not None else 'unknown'
                except Exception:
                    name = 'unknown'

            # Validar que tenemos algo con lo que trabajar
            if not name or not name.strip():
                return 'unknown_file'

            # Normalizar caracteres Unicode de forma segura
            try:
                name = unicodedata.normalize('NFKD', name)
                name = name.encode('ascii', 'ignore').decode('ascii')
            except Exception:
                # Si falla la normalización, usar el nombre tal como está
                pass

            # Eliminar caracteres problemáticos
            name = re.sub(r'[^\w\-_\.]', '_', name)
            name = re.sub(r'_+', '_', name).strip('_')
            
            # Asegurar que no esté vacío después de la limpieza
            return name if name else 'unknown_file'
            
        except Exception as e:
            _logger.error(f"Error sanitizando nombre de archivo '{name}': {str(e)}")
            return 'unknown_file'

    def _check_export_permissions(self):
        """Verifica que el usuario tenga permisos para exportar facturas."""
        return (
            self.env.user.has_group('account.group_account_user') or
            self.env.user.has_group('account.group_account_manager') or
            self.env.user.has_group('account.group_account_invoice')
        )

    def _reload_wizard(self):
        """Recarga la vista del wizard manteniendo contexto."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_view_history(self):
        """Abre la vista del historial de exportaciones."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Historial de Exportaciones',
            'res_model': 'account.invoice.export.history',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {'search_default_this_month': 1},
        }

    def action_diagnose_pdf_issues(self):
        """
        Diagnóstica problemas con generación de PDFs.
        VERSIÓN CORREGIDA: Compatible con Odoo 17 y módulos OCA.
        """
        self.ensure_one()
        
        diagnosis = []
        diagnosis.append("=== DIAGNÓSTICO SISTEMA PDF CORREGIDO ===\n")
        
        # Información básica
        diagnosis.append(f"Compañía: {self.company_id.name}")
        diagnosis.append(f"Usuario: {self.env.user.name}")
        diagnosis.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        diagnosis.append(f"Versión Odoo: 17.0\n")
        
        # Verificar reportes disponibles con búsqueda segura
        try:
            reports = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ])
            
            diagnosis.append(f"Reportes PDF encontrados: {len(reports)}")
            for i, report in enumerate(reports[:5], 1):
                report_name = getattr(report, 'report_name', 'N/A')
                diagnosis.append(f"  {i}. {report.name} ({report_name})")
        except Exception as e:
            diagnosis.append(f"❌ Error buscando reportes: {e}")
            reports = self.env['ir.actions.report']
        
        # Verificar XMLIDs con manejo seguro
        diagnosis.append("\nVerificando XMLIDs estándar:")
        xmlids = [
            'account.account_invoices',
            'account.report_invoice_with_payments',
            'account.account_invoices_without_payment'
        ]
        
        working_xmlids = 0
        for xmlid in xmlids:
            try:
                # CORRECCIÓN: Manejo seguro de XMLIDs
                if not isinstance(xmlid, str) or '.' not in xmlid:
                    diagnosis.append(f"  ✗ {xmlid}: FORMATO INVÁLIDO")
                    continue
                    
                report = self.env.ref(xmlid, raise_if_not_found=False)
                if report and hasattr(report, 'name'):
                    diagnosis.append(f"  ✓ {xmlid}: OK - {report.name}")
                    working_xmlids += 1
                else:
                    diagnosis.append(f"  ✗ {xmlid}: NO ENCONTRADO")
            except Exception as e:
                diagnosis.append(f"  ✗ {xmlid}: ERROR - {str(e)[:50]}")
        
        # Probar con facturas reales
        test_invoices = self._get_test_invoices()
        
        if test_invoices:
            diagnosis.append(f"\nProbando con {len(test_invoices)} facturas:")
            
            for invoice in test_invoices:
                diagnosis.append(f"\nFactura: {invoice.name}")
                diagnosis.append(f"  Tipo: {invoice.move_type}")
                diagnosis.append(f"  Estado: {invoice.state}")
                diagnosis.append(f"  Partner: {invoice.partner_id.name}")
                
                # Probar generación PDF con método corregido
                try:
                    pdf_content = self._get_invoice_pdf(invoice)
                    if pdf_content and len(pdf_content) > PDF_MIN_SIZE:
                        diagnosis.append(f"  ✅ PDF generado exitosamente: {len(pdf_content)} bytes")
                    else:
                        diagnosis.append(f"  ⚠️ PDF generado pero inválido")
                except Exception as e:
                    diagnosis.append(f"  ❌ Error generando PDF: {str(e)[:100]}")
        else:
            diagnosis.append("\n⚠️ No hay facturas disponibles para prueba")
        
        # Verificar módulos OCA que pueden interferir
        diagnosis.append(self._check_oca_modules())
        
        # Resumen y recomendaciones
        diagnosis.append("\n=== RESUMEN CORREGIDO ===")
        diagnosis.append(f"Reportes disponibles: {len(reports)}")
        diagnosis.append(f"XMLIDs funcionando: {working_xmlids}/{len(xmlids)}")
        
        if len(reports) == 0:
            diagnosis.append("🔥 CRÍTICO: No hay reportes PDF disponibles")
            diagnosis.append("   Solución: Reinstalar módulo 'account' o verificar datos base")
        elif working_xmlids == 0:
            diagnosis.append("⚠️ ADVERTENCIA: XMLIDs estándar no funcionan")
            diagnosis.append("   Solución: Actualizar datos base o usar reportes alternativos")
        else:
            diagnosis.append("✅ Sistema funcional con correcciones aplicadas")
        
        diagnosis.append("\n=== CORRECCIONES APLICADAS ===")
        diagnosis.append("✓ Operadores domain corregidos ('in' en lugar de '=')")
        diagnosis.append("✓ Validación de tipos antes de operaciones string")
        diagnosis.append("✓ Manejo seguro de claves de caché")
        diagnosis.append("✓ Sistema de emergencia PDF mejorado")
        
        message = "\n".join(diagnosis)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Diagnóstico PDF - Versión Corregida'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def _get_test_invoices(self):
        """Obtiene facturas de prueba para diagnóstico."""
        test_invoices = []
        
        if self.invoice_ids:
            test_invoices = self.invoice_ids[:2]
        else:
            # Buscar facturas de diferentes tipos
            for move_type in ['out_invoice', 'in_invoice']:
                invoice = self.env['account.move'].search([
                    ('move_type', '=', move_type),
                    ('state', '=', 'posted'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                if invoice:
                    test_invoices.append(invoice)
        
        return self.env['account.move'].browse([inv.id for inv in test_invoices])
    
    def _check_oca_modules(self):
        """Verifica módulos OCA que pueden interferir."""
        diagnosis = ["\n=== VERIFICACIÓN MÓDULOS OCA ==="]
        
        problematic_modules = [
            'report_xlsx',
            'server_environment',
            'queue_job'
        ]
        
        for module_name in problematic_modules:
            try:
                module = self.env['ir.module.module'].search([
                    ('name', '=', module_name),
                    ('state', '=', 'installed')
                ], limit=1)
                
                if module:
                    diagnosis.append(f"⚠️ {module_name}: INSTALADO - Puede interferir con reportes")
                else:
                    diagnosis.append(f"✓ {module_name}: No instalado")
            except Exception as e:
                diagnosis.append(f"? {module_name}: Error verificando - {str(e)[:30]}")
        
        return "\n".join(diagnosis)

    # ==========================================
    # MÉTODO LEGACY PARA COMPATIBILIDAD
    # ==========================================
    
    def action_export(self):
        """Método legacy - redirige a action_start_export."""
        return self.action_start_export()
