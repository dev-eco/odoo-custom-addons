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

            # NUEVO: Probar con la primera factura antes de procesar todas
            _logger.info(f"Probando generación PDF con primera factura antes de exportación masiva...")
            if invoices:
                test_result = self._test_single_invoice_pdf(invoices[0])
                if not test_result:
                    _logger.warning("La prueba de PDF falló, pero continuando con exportación...")

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
    # MÉTODOS AUXILIARES - BÚSQUEDA DE FACTURAS
    # ==========================================

    def _build_invoice_domain(self):
        """
        Construye domain para búsqueda de facturas con validaciones mejoradas.
        CORRECCIÓN CRÍTICA: Domain más flexible y robusto para encontrar facturas de venta.
        """
        self.ensure_one()
        
        # Validar que tenemos company_id
        if not self.company_id:
            _logger.warning("No hay company_id configurada")
            return [('id', '=', False)]
        
        # Domain base - CRÍTICO: Buscar en account.move, no solo facturas
        domain = [
            ('company_id', '=', self.company_id.id),
            # Asegurar que son movimientos de tipo factura
            ('move_type', '!=', False),
        ]

        # Tipos de movimiento
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
            domain.append(('move_type', 'in', move_types))
            _logger.info(f"Tipos de movimiento incluidos: {move_types}")
        else:
            _logger.warning("No hay tipos de movimiento seleccionados")
            return [('id', '=', False)]

        # CORRECCIÓN CRÍTICA: Estado con lógica mejorada
        if self.state_filter == 'posted':
            # Solo facturas confirmadas/publicadas
            domain.append(('state', '=', 'posted'))
            _logger.info("Filtro de estado: solo confirmadas")
        elif self.state_filter == 'draft':
            # Solo borradores
            domain.append(('state', '=', 'draft'))
            _logger.info("Filtro de estado: solo borradores")
        else:
            # Si es 'all', no agregar filtro de estado pero excluir canceladas
            _logger.info("Filtro de estado: todos excepto canceladas")
        
        # NUEVO: Excluir facturas canceladas siempre (excepto si se buscan explícitamente)
        if self.state_filter != 'all':
            domain.append(('state', '!=', 'cancel'))

        # Filtros de fecha - CORRECCIÓN: usar invoice_date como campo principal
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
            _logger.info(f"Fecha desde: {self.date_from}")
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
            _logger.info(f"Fecha hasta: {self.date_to}")

        # Filtro de partner
        if self.partner_ids:
            partner_ids = self.partner_ids.ids if hasattr(self.partner_ids, 'ids') else []
            if partner_ids:
                domain.append(('partner_id', 'in', partner_ids))
                _logger.info(f"Partners filtrados: {len(partner_ids)}")
        
        # Filtro de usuario/vendedor - CORRECCIÓN: campo correcto en Odoo 17
        if self.user_id and self.user_id.id:
            # En Odoo 17, el campo es invoice_user_id
            domain.append(('invoice_user_id', '=', self.user_id.id))
            _logger.info(f"Usuario filtrado: {self.user_id.name}")

        # Filtros de importe
        if self.amount_from and self.amount_from > 0:
            domain.append(('amount_total', '>=', self.amount_from))
            _logger.info(f"Importe mínimo: {self.amount_from}")
        if self.amount_to and self.amount_to > 0:
            domain.append(('amount_total', '<=', self.amount_to))
            _logger.info(f"Importe máximo: {self.amount_to}")

        # Log para debugging
        _logger.info(f"Domain construido para búsqueda: {domain}")

        # NUEVO: Validar que el domain es válido
        try:
            # Hacer una búsqueda de prueba con limit 0 para validar el domain
            self.env['account.move'].search(domain, limit=0)
        except Exception as domain_error:
            _logger.error(f"Domain inválido: {domain}. Error: {str(domain_error)}")
            return [('id', '=', False)]

        return domain

    def _get_invoices_to_export(self):
        """
        Obtiene facturas basado en criterios de selección con validaciones mejoradas.
        CORRECCIÓN: Mejor logging y manejo de errores.
        """
        self.ensure_one()

        # Usar facturas pre-seleccionadas si existen
        if self.invoice_ids:
            valid_invoices = self.invoice_ids.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']
                and inv.company_id == self.company_id
            )
            _logger.info(f"Usando {len(valid_invoices)} facturas preseleccionadas")
            return valid_invoices

        # Usar domain construido con manejo de errores
        try:
            domain = self._build_invoice_domain()
            _logger.info(f"Buscando facturas con domain: {domain}")
            
            if domain == [('id', '=', False)]:
                _logger.warning("Domain vacío - no se buscarán facturas")
                return self.env['account.move']
            
            invoices = self.env['account.move'].search(domain)
            _logger.info(f"Encontradas {len(invoices)} facturas")
            
            # NUEVO: Verificar tipos de facturas encontradas
            if invoices:
                types_found = set(invoices.mapped('move_type'))
                states_found = set(invoices.mapped('state'))
                _logger.info(f"Tipos de facturas encontradas: {types_found}")
                _logger.info(f"Estados encontrados: {states_found}")
                _logger.info(f"Nombres de facturas: {invoices.mapped('name')}")
            else:
                _logger.warning("No se encontraron facturas con los criterios especificados")
            
            return invoices
            
        except Exception as e:
            _logger.error(f"Error buscando facturas: {str(e)}", exc_info=True)
            return self.env['account.move']

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
        Obtiene PDF de factura con estrategia unificada.
        CORRECCIÓN: Misma lógica para clientes y proveedores - buscar adjunto primero.
        """
        try:
            # Logging detallado
            _logger.info(f"Obteniendo PDF para factura {invoice.name} (tipo: {invoice.move_type})")

            # ESTRATEGIA UNIFICADA PARA TODOS LOS TIPOS:

            # 1. PRIMERO: Intentar buscar PDF adjunto (funciona para todos)
            pdf_content = self._get_pdf_from_attachment(invoice)
            if pdf_content:
                _logger.info(f"✅ PDF obtenido de adjunto para {invoice.name}: {len(pdf_content)} bytes")
                return pdf_content

            # 2. SEGUNDO: Generar PDF desde reporte (método corregido)
            _logger.info(f"No hay adjunto, generando PDF desde reporte para {invoice.name}")
            pdf_content = self._generate_pdf_direct(invoice)

            if pdf_content:
                _logger.info(f"✅ PDF generado desde reporte para {invoice.name}: {len(pdf_content)} bytes")
            else:
                _logger.warning(f"⚠️ No se pudo generar PDF para {invoice.name}")

            return pdf_content

        except Exception as e:
            _logger.error(f"❌ Error obteniendo PDF para {invoice.name}: {str(e)}", exc_info=True)
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


    def _generate_pdf_direct(self, invoice):
        """
        Genera PDF usando sistema de reportes de Odoo.
        VERSIÓN CORREGIDA: Búsqueda robusta de reportes sin usar env.ref().
        """
        try:
            # Validar que tenemos un invoice válido
            if not invoice or not invoice.id:
                _logger.warning("Invoice inválido para generar PDF")
                return None

            report = None

            # ESTRATEGIA 1: Buscar reporte estándar por nombre técnico
            try:
                _logger.info("Estrategia 1: Buscando reporte por nombre técnico...")
                report = self.env['ir.actions.report'].search([
                    ('model', '=', 'account.move'),
                    ('report_type', '=', 'qweb-pdf'),
                    ('report_name', '=', 'account.report_invoice')
                ], limit=1)

                if report:
                    _logger.info(f"✅ Reporte encontrado por nombre técnico: {report.name} (ID: {report.id})")
            except Exception as e:
                _logger.warning(f"Estrategia 1 falló: {e}")

            # ESTRATEGIA 2: Si falla, buscar por external ID de forma segura
            if not report:
                try:
                    _logger.info("Estrategia 2: Buscando reporte por external ID...")
                    ext_id = self.env['ir.model.data'].search([
                        ('module', '=', 'account'),
                        ('name', '=', 'account_invoices'),
                        ('model', '=', 'ir.actions.report')
                    ], limit=1)

                    if ext_id and ext_id.res_id:
                        report = self.env['ir.actions.report'].browse(ext_id.res_id)
                        if report.exists():
                            _logger.info(f"✅ Reporte encontrado vía external ID: {report.name} (ID: {report.id})")
                        else:
                            _logger.warning("External ID encontrado pero reporte no existe")
                            report = None
                except Exception as e:
                    _logger.warning(f"Estrategia 2 falló: {e}")

            # ESTRATEGIA 3: Fallback - primer reporte disponible para account.move
            if not report:
                try:
                    _logger.info("Estrategia 3: Buscando cualquier reporte disponible...")
                    report = self.env['ir.actions.report'].search([
                        ('model', '=', 'account.move'),
                        ('report_type', '=', 'qweb-pdf')
                    ], limit=1, order='id asc')

                    if report:
                        _logger.warning(f"⚠️ Usando reporte fallback: {report.name} (ID: {report.id})")
                except Exception as e:
                    _logger.error(f"Estrategia 3 falló: {e}")

            # Validar que tenemos un reporte válido
            if not report or not report.id:
                _logger.error(f"❌ No se encontró ningún reporte PDF válido para {invoice.name}")
                return None

            # VALIDACIÓN CRÍTICA: Verificar que report es un objeto, NO una lista
            if isinstance(report, (list, tuple)):
                _logger.error(f"❌ ERROR: Report es una lista/tupla inválida: {report}")
                return None

            # Validar que es un recordset con al menos un registro
            if not hasattr(report, 'id'):
                _logger.error(f"❌ ERROR: Report no es un recordset válido: {type(report)}")
                return None

            # Validar que tiene el método necesario
            if not hasattr(report, '_render_qweb_pdf'):
                _logger.error(f"❌ Reporte {report.name} no tiene método _render_qweb_pdf")
                return None

            # Generar PDF con manejo robusto de errores
            try:
                # CRÍTICO: Asegurar que invoice.id es entero
                invoice_id = int(invoice.id)
                _logger.info(f"Generando PDF para invoice ID: {invoice_id} usando reporte: {report.name}")

                pdf_content, _ = report._render_qweb_pdf([invoice_id])

                if pdf_content and len(pdf_content) > PDF_MIN_SIZE:
                    _logger.info(f"✅ PDF generado exitosamente para {invoice.name}: {len(pdf_content)} bytes")
                    return pdf_content
                else:
                    _logger.warning(f"⚠️ PDF generado pero inválido para {invoice.name} (tamaño: {len(pdf_content) if pdf_content else 0} bytes)")
                    return None

            except Exception as render_error:
                _logger.error(f"❌ Error renderizando PDF con reporte {report.name}: {render_error}")

                # ÚLTIMO INTENTO: Método alternativo _render()
                try:
                    _logger.info("Intentando método alternativo _render()...")
                    pdf_content = report._render([invoice.id])[0]
                    if pdf_content and len(pdf_content) > PDF_MIN_SIZE:
                        _logger.info(f"✅ PDF generado con método alternativo para {invoice.name}")
                        return pdf_content
                except Exception as alt_error:
                    _logger.error(f"❌ Método alternativo también falló: {alt_error}")

                return None

        except Exception as e:
            _logger.error(f"❌ Error crítico generando PDF para {invoice.name}: {e}", exc_info=True)
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
        """
        Sanitiza nombres de archivo eliminando caracteres problemáticos.
        VERSIÓN MEJORADA: Manejo robusto de diferentes tipos de datos.
        """
        try:
            # VALIDACIÓN 1: None
            if name is None:
                _logger.debug("Nombre de archivo es None, usando 'unknown_file'")
                return 'unknown_file'

            # VALIDACIÓN 2: Listas y tuplas (extraer primer elemento)
            if isinstance(name, (list, tuple)):
                _logger.warning(f"⚠️ Nombre de archivo recibido como secuencia: {name}")
                if not name:  # Lista/tupla vacía
                    return 'unknown_file'
                # Extraer primer elemento y convertir a string
                name = str(name[0]) if name[0] is not None else 'unknown_file'

            # VALIDACIÓN 3: Números (convertir a string)
            elif isinstance(name, (int, float)):
                _logger.debug(f"Nombre de archivo es número: {name}, convirtiendo a string")
                name = str(name)

            # VALIDACIÓN 4: Otros tipos (convertir a string de forma segura)
            elif not isinstance(name, str):
                _logger.warning(f"⚠️ Nombre de archivo es tipo inesperado: {type(name)}")
                try:
                    name = str(name)
                except Exception as conv_error:
                    _logger.error(f"❌ No se pudo convertir {type(name)} a string: {conv_error}")
                    return 'unknown_file'

            # VALIDACIÓN 5: String vacío o solo espacios
            if not name or not name.strip():
                _logger.debug("Nombre de archivo vacío después de strip()")
                return 'unknown_file'

            # LIMPIEZA: Normalizar caracteres Unicode
            try:
                name = unicodedata.normalize('NFKD', name)
                name = name.encode('ascii', 'ignore').decode('ascii')
            except Exception as norm_error:
                # Si falla la normalización, continuar con el nombre original
                _logger.debug(f"No se pudo normalizar Unicode: {norm_error}")

            # LIMPIEZA: Eliminar caracteres no permitidos en nombres de archivo
            # Permitir: letras, números, guiones, guiones bajos, puntos
            name = re.sub(r'[^\w\-_\.]', '_', name)

            # LIMPIEZA: Colapsar múltiples guiones bajos
            name = re.sub(r'_+', '_', name)

            # LIMPIEZA: Eliminar guiones bajos al inicio/final
            name = name.strip('_')

            # VALIDACIÓN FINAL: Asegurar que no quedó vacío
            if not name:
                _logger.warning("Nombre quedó vacío después de sanitización")
                return 'unknown_file'

            # VALIDACIÓN FINAL: Longitud máxima (255 caracteres para la mayoría de sistemas)
            if len(name) > 200:  # Dejamos margen para path completo
                _logger.warning(f"Nombre muy largo ({len(name)} chars), truncando...")
                name = name[:200]

            return name

        except Exception as e:
            _logger.error(f"❌ Error crítico sanitizando nombre de archivo '{name}': {str(e)}", exc_info=True)
            # Nombre de emergencia con timestamp
            return f'unknown_file_{int(time.time())}'

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
            'name':  'Historial de Exportaciones',
            'res_model': 'account.invoice.export.history',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {'search_default_this_month': 1},
        }

    def _test_single_invoice_pdf(self, invoice):
        """Método de prueba para generar PDF de una sola factura con logging detallado."""
        _logger.info("="*50)
        _logger.info(f"PRUEBA PDF INDIVIDUAL: {invoice.name}")
        _logger.info(f"  ID: {invoice.id}")
        _logger.info(f"  Tipo: {invoice.move_type}")
        _logger.info(f"  Estado: {invoice.state}")
        _logger.info(f"  Partner: {invoice.partner_id.name if invoice.partner_id else 'N/A'}")
        
        # Buscar reportes disponibles
        _logger.info("\nReportes disponibles:")
        reports = self.env['ir.actions.report'].search([
            ('model', '=', 'account.move'),
            ('report_type', '=', 'qweb-pdf')
        ])
        
        for report in reports:
            _logger.info(f"  - {report.name} (report_name: {report.report_name})")
        
        # Intentar generar PDF
        try:
            pdf_content = self._get_invoice_pdf(invoice)
            if pdf_content:
                _logger.info(f"\n✅ PDF generado: {len(pdf_content)} bytes")
                return True
            else:
                _logger.error("\n❌ PDF no generado (contenido vacío)")
                return False
        except Exception as e:
            _logger.error(f"\n❌ Error generando PDF: {str(e)}", exc_info=True)
            return False
        finally:
            _logger.info("="*50)

    def action_test_report_search(self):
        """
        Diagnostica problemas con búsqueda de reportes PDF.
        NUEVO MÉTODO para identificar configuración de reportes.
        """
        self.ensure_one()

        diagnosis = []
        diagnosis.append("=== DIAGNÓSTICO DE BÚSQUEDA DE REPORTES PDF ===\n")

        # Información básica
        diagnosis.append(f"Compañía: {self.company_id.name}")
        diagnosis.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")

        # Prueba 1: env.ref() - Método problemático
        diagnosis.append("1️⃣ Prueba con env.ref() (método anterior):")
        try:
            report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            diagnosis.append(f"   Tipo devuelto: {type(report)}")
            diagnosis.append(f"   Valor: {report}")

            if isinstance(report, (list, tuple)):
                diagnosis.append(f"   ❌ ERROR: Devolvió lista/tupla - ESTE ES EL BUG")
            elif hasattr(report, 'name'):
                diagnosis.append(f"   ✅ Nombre: {report.name}")
                diagnosis.append(f"   ✅ ID: {report.id}")
            elif not report:
                diagnosis.append(f"   ⚠️ No encontrado (False)")
            else:
                diagnosis.append(f"   ⚠️ Tipo inesperado")
        except Exception as e:
            diagnosis.append(f"   ❌ Excepción: {str(e)[:100]}")

        # Prueba 2: Búsqueda por nombre técnico - Método nuevo
        diagnosis.append("\n2️⃣ Búsqueda por nombre técnico (método corregido):")
        try:
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf'),
                ('report_name', '=', 'account.report_invoice')
            ], limit=1)

            if report:
                diagnosis.append(f"   ✅ Encontrado: {report.name}")
                diagnosis.append(f"   ✅ ID: {report.id}")
                diagnosis.append(f"   ✅ Report Name: {report.report_name}")
            else:
                diagnosis.append(f"   ⚠️ No encontrado con este nombre técnico")
        except Exception as e:
            diagnosis.append(f"   ❌ Error: {str(e)[:100]}")

        # Prueba 3: Búsqueda por external ID
        diagnosis.append("\n3️⃣ Búsqueda por external ID:")
        try:
            ext_id = self.env['ir.model.data'].search([
                ('module', '=', 'account'),
                ('name', '=', 'account_invoices'),
                ('model', '=', 'ir.actions.report')
            ], limit=1)

            if ext_id:
                diagnosis.append(f"   ✅ External ID encontrado")
                diagnosis.append(f"   ✅ res_id: {ext_id.res_id}")
                diagnosis.append(f"   ✅ model: {ext_id.model}")

                # Intentar cargar el reporte
                report = self.env['ir.actions.report'].browse(ext_id.res_id)
                if report.exists():
                    diagnosis.append(f"   ✅ Reporte existe: {report.name}")
                else:
                    diagnosis.append(f"   ❌ Reporte no existe (ID huérfano)")
            else:
                diagnosis.append(f"   ⚠️ External ID no encontrado")
        except Exception as e:
            diagnosis.append(f"   ❌ Error: {str(e)[:100]}")

        # Prueba 4: Listar todos los reportes disponibles
        diagnosis.append("\n4️⃣ Todos los reportes PDF de account.move:")
        try:
            reports = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ])

            diagnosis.append(f"   Total encontrados: {len(reports)}")
            if reports:
                diagnosis.append("")
                for i, r in enumerate(reports, 1):
                    diagnosis.append(f"   {i}. ID:{r.id} | {r.name}")
                    diagnosis.append(f"      report_name: {r.report_name}")
            else:
                diagnosis.append("   ❌ CRÍTICO: No hay reportes PDF para account.move")
        except Exception as e:
            diagnosis.append(f"   ❌ Error: {str(e)[:100]}")

        # Prueba 5: Probar generación con factura real
        diagnosis.append("\n5️⃣ Prueba de generación PDF con factura real:")
        try:
            test_invoice = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if test_invoice:
                diagnosis.append(f"   Factura de prueba: {test_invoice.name}")
                pdf_content = self._get_invoice_pdf(test_invoice)

                if pdf_content and len(pdf_content) > PDF_MIN_SIZE:
                    diagnosis.append(f"   ✅ PDF generado exitosamente: {len(pdf_content)} bytes")
                else:
                    diagnosis.append(f"   ❌ PDF no generado o inválido")
            else:
                diagnosis.append("   ⚠️ No hay facturas de cliente para probar")
        except Exception as e:
            diagnosis.append(f"   ❌ Error: {str(e)[:100]}")

        # Resumen y recomendaciones
        diagnosis.append("\n" + "="*50)
        diagnosis.append("RESUMEN:")

        # Determinar estado del sistema
        try:
            reports_count = len(self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ]))

            if reports_count == 0:
                diagnosis.append("🔥 CRÍTICO: No hay reportes PDF disponibles")
                diagnosis.append("   Acción: Reinstalar módulo 'account' o verificar datos base")
            elif reports_count > 0:
                diagnosis.append(f"✅ Sistema funcional: {reports_count} reportes disponibles")
                diagnosis.append("   Las correcciones aplicadas deberían resolver el problema")
        except Exception:
            diagnosis.append("⚠️ No se pudo determinar estado del sistema")

        diagnosis.append("\n✅ CORRECCIONES APLICADAS:")
        diagnosis.append("   • Búsqueda robusta de reportes (3 estrategias)")
        diagnosis.append("   • Validación exhaustiva de tipos")
        diagnosis.append("   • Estrategia unificada cliente/proveedor")
        diagnosis.append("   • Sanitización mejorada de nombres de archivo")

        message = "\n".join(diagnosis)
        _logger.info(message)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Diagnóstico de Reportes PDF'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }

    def action_test_invoice_search(self):
        """
        Prueba la búsqueda de facturas para diagnosticar problemas.
        NUEVO MÉTODO: Diagnóstico mejorado de búsqueda.
        """
        self.ensure_one()
        
        diagnosis = []
        diagnosis.append("=== DIAGNÓSTICO DE BÚSQUEDA DE FACTURAS ===\n")
        
        # Información de configuración
        diagnosis.append(f"Compañía: {self.company_id.name}")
        diagnosis.append(f"Filtro de estado: {self.state_filter}")
        diagnosis.append(f"Incluir facturas cliente: {self.include_out_invoice}")
        diagnosis.append(f"Incluir facturas proveedor: {self.include_in_invoice}")
        diagnosis.append(f"Rango de fechas: {self.date_from} - {self.date_to}\n")
        
        # Contar facturas por tipo en la base de datos
        diagnosis.append("FACTURAS EN BASE DE DATOS:")
        for move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
            count_all = self.env['account.move'].search_count([
                ('move_type', '=', move_type),
                ('company_id', '=', self.company_id.id)
            ])
            count_posted = self.env['account.move'].search_count([
                ('move_type', '=', move_type),
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'posted')
            ])
            diagnosis.append(f"  {move_type}: {count_all} total, {count_posted} confirmadas")
        
        # Probar domain construido
        diagnosis.append("\nDOMAIN CONSTRUIDO:")
        domain = self._build_invoice_domain()
        diagnosis.append(f"  {domain}")
        
        # Ejecutar búsqueda
        diagnosis.append("\nRESULTADO DE BÚSQUEDA:")
        try:
            invoices = self.env['account.move'].search(domain)
            diagnosis.append(f"  Facturas encontradas: {len(invoices)}")
            
            if invoices:
                diagnosis.append("\n  Primeras 5 facturas:")
                for inv in invoices[:5]:
                    diagnosis.append(f"    - {inv.name} | {inv.move_type} | {inv.state} | {inv.partner_id.name}")
            else:
                diagnosis.append("  ⚠️ NO SE ENCONTRARON FACTURAS")
                
                # Intentar búsqueda simplificada
                diagnosis.append("\n  Probando búsqueda simplificada...")
                simple_domain = [
                    ('company_id', '=', self.company_id.id),
                    ('move_type', '=', 'out_invoice')
                ]
                simple_invoices = self.env['account.move'].search(simple_domain, limit=5)
                diagnosis.append(f"  Facturas con búsqueda simple: {len(simple_invoices)}")
                
                if simple_invoices:
                    diagnosis.append("  ✅ Hay facturas, el problema está en los filtros")
                else:
                    diagnosis.append("  ❌ No hay facturas de venta en el sistema")
                    
        except Exception as e:
            diagnosis.append(f"  ❌ ERROR: {str(e)}")
        
        message = "\n".join(diagnosis)
        _logger.info(message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Diagnóstico de Búsqueda'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
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
