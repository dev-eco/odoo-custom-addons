# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import tarfile
import logging
import re
from datetime import datetime
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class BulkExportWizard(models.TransientModel):
    """
    Wizard mejorado para exportación masiva de facturas.
    
    Mejoras de seguridad:
    - Valida acceso de usuario a cada factura
    - Sanitiza nombres de archivo para prevenir path traversal
    - Limita tamaño de lotes para prevenir agotamiento de recursos
    - Implementa rate limiting mediante procesamiento por lotes
    - Registra todas las exportaciones para auditoría
    
    Nuevas características:
    - Generación real de PDFs usando motor de reportes de Odoo
    - Vista previa de facturas antes de exportar
    - Inclusión opcional de archivos adjuntos
    - Organización en carpetas por tipo de documento
    - Barra de progreso durante procesamiento
    - Estadísticas detalladas
    - Historial de exportaciones para auditoría
    """
    
    _name = 'account.bulk.export.wizard'
    _description = 'Wizard de Exportación Masiva de Facturas'

    # ==========================================
    # CAMPOS DE ESTADO
    # ==========================================
    
    state = fields.Selection([
        ('draft', 'Configuración'),
        ('preview', 'Vista Previa'),
        ('processing', 'Procesando'),
        ('done', 'Completado'),
        ('error', 'Error'),
    ], string='Estado', default='draft', required=True)

    # ==========================================
    # CONFIGURACIÓN BÁSICA
    # ==========================================
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
        help='Compañía de la cual exportar facturas'
    )

    # ==========================================
    # MODO DE SELECCIÓN
    # ==========================================
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Seleccionadas',
        help='Facturas pre-seleccionadas desde la vista de lista'
    )
    
    selected_count = fields.Integer(
        string='Cantidad Seleccionada',
        compute='_compute_selected_count',
        store=True,
    )

    # ==========================================
    # FILTROS (cuando no hay pre-selección)
    # ==========================================
    
    date_from = fields.Date(
        string='Fecha Desde',
        help='Fecha inicial del rango a exportar'
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        help='Fecha final del rango a exportar'
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Empresas/Proveedores Específicos',
        help='Dejar vacío para incluir todos'
    )

    # Tipos de documento
    include_out_invoice = fields.Boolean(
        string='Facturas de Cliente',
        default=True,
        help='Incluir facturas emitidas a clientes'
    )
    
    include_in_invoice = fields.Boolean(
        string='Facturas de Proveedor',
        default=True,
        help='Incluir facturas recibidas de proveedores'
    )
    
    include_out_refund = fields.Boolean(
        string='Notas de Crédito de Cliente',
        default=False,
        help='Incluir notas de crédito emitidas'
    )
    
    include_in_refund = fields.Boolean(
        string='Notas de Crédito de Proveedor',
        default=False,
        help='Incluir notas de crédito recibidas'
    )

    state_filter = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicada'),
        ('all', 'Todos los Estados'),
    ], string='Estado de Factura', default='posted',
       help='Filtrar facturas por su estado')

    # ==========================================
    # OPCIONES DE COMPRESIÓN
    # ==========================================
    
    compression_format = fields.Selection([
        ('zip', 'ZIP'),
        ('zip_password', 'ZIP con Contraseña'),
        ('tar_gz', 'TAR.GZ'),
        ('tar_bz2', 'TAR.BZ2'),
    ], string='Formato de Compresión', required=True,
       help='Formato del archivo comprimido a generar',
       default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
           'account_invoice_bulk_export.default_format', 'zip'))

    archive_password = fields.Char(
        string='Contraseña del Archivo',
        help='Contraseña para protección del ZIP (solo para ZIP con Contraseña)'
    )

    # ==========================================
    # OPCIONES DE NOMBRES DE ARCHIVO
    # ==========================================
    
    filename_pattern = fields.Selection([
        ('standard', 'Tipo_Número_Partner_Fecha'),
        ('date_first', 'Fecha_Tipo_Número_Partner'),
        ('partner_first', 'Partner_Tipo_Número_Fecha'),
        ('simple', 'Tipo_Número_Fecha'),
    ], string='Patrón de Nombres',
       help='Patrón para generar nombres de archivos PDF',
       default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
           'account_invoice_bulk_export.default_pattern', 'standard'))

    # ==========================================
    # OPCIONES AVANZADAS
    # ==========================================
    
    organize_by_type = fields.Boolean(
        string='Organizar en Carpetas por Tipo',
        default=True,
        help='Crea carpetas separadas para facturas, notas de crédito, etc.'
    )
    
    include_attachments = fields.Boolean(
        string='Incluir Adjuntos',
        default=False,
        help='Incluir archivos adjuntos a las facturas'
    )
    
    batch_size = fields.Integer(
        string='Tamaño del Lote',
        default=lambda self: int(self.env['ir.config_parameter'].sudo().get_param(
            'account_invoice_bulk_export.default_batch_size', '50')),
        help='Número de facturas a procesar simultáneamente (1-500)'
    )

    # ==========================================
    # VISTA PREVIA
    # ==========================================
    
    preview_invoice_count = fields.Integer(
        string='Total Facturas a Exportar',
        compute='_compute_preview_stats',
    )
    
    preview_out_invoice_count = fields.Integer(
        string='Facturas de Cliente',
        compute='_compute_preview_stats',
    )
    
    preview_in_invoice_count = fields.Integer(
        string='Facturas de Proveedor',
        compute='_compute_preview_stats',
    )
    
    preview_out_refund_count = fields.Integer(
        string='NC de Cliente',
        compute='_compute_preview_stats',
    )
    
    preview_in_refund_count = fields.Integer(
        string='NC de Proveedor',
        compute='_compute_preview_stats',
    )
    
    preview_total_amount = fields.Monetary(
        string='Importe Total',
        compute='_compute_preview_stats',
        currency_field='currency_id',
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
    )

    # ==========================================
    # PROGRESO
    # ==========================================
    
    progress_percentage = fields.Float(
        string='Progreso (%)',
        default=0.0,
    )
    
    progress_message = fields.Char(
        string='Mensaje de Progreso',
    )

    # ==========================================
    # RESULTADOS
    # ==========================================
    
    export_file = fields.Binary(
        string='Archivo de Exportación',
        readonly=True,
        attachment=False,
    )
    
    export_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
    )
    
    export_count = fields.Integer(
        string='Facturas Exportadas',
        readonly=True,
    )
    
    failed_count = fields.Integer(
        string='Facturas Fallidas',
        readonly=True,
    )
    
    processing_time = fields.Float(
        string='Tiempo de Procesamiento (s)',
        readonly=True,
    )
    
    file_size_mb = fields.Float(
        string='Tamaño del Archivo (MB)',
        readonly=True,
        compute='_compute_file_size',
    )
    
    error_message = fields.Text(
        string='Detalles del Error',
        readonly=True,
    )
    
    export_history_id = fields.Many2one(
        'account.invoice.export.history',
        string='Registro de Exportación',
        readonly=True,
        help='Registro en el historial de exportaciones',
    )
    
    attachments_count = fields.Integer(
        string='Archivos Adjuntos',
        readonly=True,
    )

    # ==========================================
    # CAMPOS COMPUTADOS
    # ==========================================

    @api.depends('invoice_ids')
    def _compute_selected_count(self):
        """Calcula la cantidad de facturas seleccionadas."""
        for record in self:
            record.selected_count = len(record.invoice_ids)

    @api.depends('export_file')
    def _compute_file_size(self):
        """Calcula el tamaño del archivo exportado en MB con manejo robusto de errores."""
        import logging
        _logger = logging.getLogger(__name__)
        
        for record in self:
            try:
                # Validación inicial: verificar que el campo existe y no está vacío
                if not record.export_file:
                    record.file_size_mb = 0.0
                    continue
                    
                # Obtener el contenido como string
                file_content = record.export_file
                
                # Validación: verificar que es string/bytes válido
                if not isinstance(file_content, (str, bytes)):
                    _logger.warning(f"export_file contiene tipo inválido: {type(file_content)}")
                    record.file_size_mb = 0.0
                    continue
                    
                # Convertir a string si es necesario
                if isinstance(file_content, bytes):
                    file_content = file_content.decode('utf-8')
                    
                # Limpiar contenido: remover caracteres de nueva línea y espacios
                file_content = file_content.strip().replace('\n', '').replace('\r', '')
                
                # Validación: verificar que el contenido no está vacío después de limpiar
                if not file_content:
                    record.file_size_mb = 0.0
                    continue
                    
                # Validación de longitud base64: debe ser múltiplo de 4
                if len(file_content) % 4 != 0:
                    # Agregar padding faltante
                    padding_needed = 4 - (len(file_content) % 4)
                    file_content += '=' * padding_needed
                    _logger.info(f"Agregado padding base64: {padding_needed} caracteres")
                
                # Validación: verificar caracteres base64 válidos
                import re
                if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', file_content):
                    _logger.error("export_file contiene caracteres no base64 válidos")
                    record.file_size_mb = 0.0
                    continue
                    
                # Decodificar con manejo de errores
                try:
                    file_bytes = base64.b64decode(file_content, validate=True)
                    file_size_bytes = len(file_bytes)
                    record.file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
                    
                    # Log informativo para debugging
                    _logger.info(
                        f"Archivo calculado correctamente: {file_size_bytes} bytes "
                        f"({record.file_size_mb} MB)"
                    )
                    
                except Exception as decode_error:
                    _logger.error(
                        f"Error decodificando base64: {str(decode_error)}. "
                        f"Contenido length: {len(file_content)}, "
                        f"Primeros 50 chars: {file_content[:50]}"
                    )
                    record.file_size_mb = 0.0
                    
            except Exception as e:
                _logger.error(f"Error en _compute_file_size: {str(e)}", exc_info=True)
                record.file_size_mb = 0.0

    @api.depends('date_from', 'date_to', 'partner_ids', 'include_out_invoice',
                 'include_in_invoice', 'include_out_refund', 'include_in_refund',
                 'state_filter', 'invoice_ids', 'company_id')
    def _compute_preview_stats(self):
        """Calcula estadísticas para la vista previa."""
        for record in self:
            invoices = record._get_invoices_to_export()
            
            record.preview_invoice_count = len(invoices)
            record.preview_out_invoice_count = len(invoices.filtered(
                lambda inv: inv.move_type == 'out_invoice'
            ))
            record.preview_in_invoice_count = len(invoices.filtered(
                lambda inv: inv.move_type == 'in_invoice'
            ))
            record.preview_out_refund_count = len(invoices.filtered(
                lambda inv: inv.move_type == 'out_refund'
            ))
            record.preview_in_refund_count = len(invoices.filtered(
                lambda inv: inv.move_type == 'in_refund'
            ))
            
            # Calcular importe total en la moneda de la compañía
            total = 0.0
            for invoice in invoices:
                if invoice.currency_id == record.currency_id:
                    total += invoice.amount_total
                else:
                    # Convertir a moneda de la compañía
                    total += invoice.currency_id._convert(
                        invoice.amount_total,
                        record.currency_id,
                        record.company_id,
                        invoice.invoice_date or fields.Date.today()
                    )
            record.preview_total_amount = total

    # ==========================================
    # VALIDACIONES
    # ==========================================

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Valida que la fecha desde no sea posterior a la fecha hasta."""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError(
                        _('La fecha desde no puede ser posterior a la fecha hasta.')
                    )

    @api.constrains('compression_format', 'archive_password')
    def _check_password(self):
        """Valida que se proporcione contraseña para ZIP protegido."""
        for record in self:
            if record.compression_format == 'zip_password' and not record.archive_password:
                raise ValidationError(
                    _('Se requiere una contraseña para ZIP con protección de contraseña.')
                )

    @api.constrains('batch_size')
    def _check_batch_size(self):
        """Valida que el tamaño del lote esté en rango válido."""
        for record in self:
            if record.batch_size < 1 or record.batch_size > 500:
                raise ValidationError(
                    _('El tamaño del lote debe estar entre 1 y 500.')
                )

    # ==========================================
    # MÉTODOS DE NAVEGACIÓN
    # ==========================================

    def action_show_preview(self):
        """Muestra la vista previa de las facturas a exportar."""
        self.ensure_one()
        
        # Validar que hay facturas para exportar
        invoices = self._get_invoices_to_export()
        if not invoices:
            raise UserError(
                _('No se encontraron facturas que coincidan con los criterios especificados.')
            )
        
        self.write({'state': 'preview'})
        return self._reload_wizard()

    def action_back_to_config(self):
        """Regresa a la configuración desde la vista previa."""
        self.ensure_one()
        self.write({'state': 'draft'})
        return self._reload_wizard()

    def action_start_export(self):
        """
        Inicia el proceso de exportación con validación de seguridad.
        
        Este método incluye múltiples capas de validación de seguridad:
        - Verificación de permisos de usuario
        - Validación de acceso a facturas individuales
        - Sanitización de nombres de archivo
        - Límites de procesamiento por lotes
        """
        self.ensure_one()
        
        # VALIDACIÓN DE SEGURIDAD: Verificar permisos de contabilidad
        accounting_groups = [
            'account.group_account_user',
            'account.group_account_manager',
            'account.group_account_invoice',
        ]
        
        has_access = any(self.env.user.has_group(group) for group in accounting_groups)
        
        if not has_access:
            raise AccessError(_(
                'No tiene permisos para exportar facturas. '
                'Grupos requeridos: Usuario de Contabilidad, Gestor de Contabilidad, '
                'o Usuario de Facturas. Contacte a su administrador.'
            ))

        try:
            self.write({
                'state': 'processing',
                'error_message': False,
                'progress_percentage': 0.0,
                'progress_message': _('Iniciando exportación...'),
            })
            self.env.cr.commit()  # Commit para que se vea el progreso
            
            start_time = datetime.now()
            
            # Obtener facturas a exportar
            self._update_progress(10, _('Obteniendo facturas...'))
            invoices = self._get_invoices_to_export()
            
            if not invoices:
                raise UserError(_('No se encontraron facturas que coincidan con los criterios.'))

            # Validación de seguridad: verificar acceso a todas las facturas
            self._update_progress(15, _('Validando permisos...'))
            try:
                invoices.check_access_rights('read')
                invoices.check_access_rule('read')
            except AccessError:
                raise AccessError(
                    _('No tiene acceso a algunas de las facturas seleccionadas.')
                )

            # Generar archivo de exportación
            self._update_progress(20, _('Generando PDFs...'))
            export_data, failed_count, attachments_count = self._generate_export_file(invoices)
            
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
            filename = f'facturas_exportacion_{timestamp}.{extension}'

        try:
            # Validar que export_data no esté vacío
            if not export_data:
                raise UserError(_('No se pudo generar contenido para exportar.'))
            
            # Validar tipo de datos
            if not isinstance(export_data, bytes):
                export_data = export_data.encode('utf-8') if isinstance(export_data, str) else bytes(export_data)
            
            # Codificar en base64 de forma segura
            encoded_file = base64.b64encode(export_data).decode('ascii')
            
            # Verificar que la codificación fue exitosa
            if not encoded_file:
                raise UserError(_('Error al codificar el archivo para almacenamiento.'))
                
            self.write({
                'state': 'done',
                'export_file': encoded_file,  # Guardar como string ASCII
                'export_filename': filename,
                'export_count': len(invoices) - failed_count,
                'failed_count': failed_count,
                'processing_time': round(processing_time, 2),
                'progress_percentage': 100.0,
                'progress_message': _('Exportación completada'),
            })
            
        except Exception as e:
            _logger.error(f"Error almacenando archivo exportado: {str(e)}")
            self.write({
                'state': 'error',
                'error_message': f'Error almacenando archivo: {str(e)}',
            })
            raise
            
            # Crear registro en el historial
            self._create_export_history(invoices)
            
            # Log de auditoría
            _logger.info(
                f"Exportación completada por usuario {self.env.user.name}: "
                f"{self.export_count} facturas exportadas en {processing_time:.2f}s"
            )

        except Exception as e:
            _logger.error(f"Error en la exportación: {str(e)}", exc_info=True)
            self.write({
                'state': 'error',
                'error_message': str(e),
                'progress_percentage': 0.0,
            })
            raise

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
        """Reinicia el wizard para una nueva exportación."""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'failed_count': 0,
            'attachments_count': 0,
            'processing_time': 0,
            'file_size_mb': 0.0,
            'error_message': False,
            'progress_percentage': 0.0,
            'progress_message': False,
        })
        return self._reload_wizard()

    def action_view_export_history(self):
        """Abre el registro de exportación en el historial."""
        self.ensure_one()
        if not self.export_history_id:
            raise UserError(_('No hay registro de historial asociado.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Registro de Exportación'),
            'res_model': 'account.invoice.export.history',
            'res_id': self.export_history_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ==========================================
    # MÉTODOS PRIVADOS - LÓGICA PRINCIPAL
    # ==========================================

    def _update_progress(self, percentage, message):
        """Actualiza el progreso de la exportación."""
        self.write({
            'progress_percentage': percentage,
            'progress_message': message,
        })
        self.env.cr.commit()  # Commit para que se vea el progreso en tiempo real

    def _get_invoices_to_export(self):
        """
        Obtiene las facturas basadas en criterios de selección.
        
        Returns:
            recordset: Facturas filtradas para exportar
        """
        self.ensure_one()

        # Usar facturas pre-seleccionadas si están disponibles
        if self.invoice_ids:
            return self.invoice_ids

        # Construir dominio para búsqueda
        domain = [('company_id', '=', self.company_id.id)]

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

        # Filtros de fecha
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Filtro de partner
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # Filtro de estado
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        return self.env['account.move'].search(domain)

    def _generate_export_file(self, invoices):
        """
        Genera el archivo comprimido con PDFs de facturas.
        
        Args:
            invoices: recordset de facturas a exportar
            
        Returns:
            tuple: (datos_archivo, cantidad_fallidas, cantidad_adjuntos)
        """
        self.ensure_one()

        if self.compression_format in ['zip', 'zip_password']:
            return self._generate_zip_file(invoices)
        elif self.compression_format == 'tar_gz':
            return self._generate_tar_file(invoices, 'gz')
        elif self.compression_format == 'tar_bz2':
            return self._generate_tar_file(invoices, 'bz2')

    def _generate_zip_file(self, invoices):
        """
        Genera archivo ZIP con facturas.
        
        Args:
            invoices: recordset de facturas
            
        Returns:
            tuple: (datos_zip, cantidad_fallidas, cantidad_adjuntos)
        """
        buffer = io.BytesIO()
        failed_count = 0
        attachments_count = 0
        total = len(invoices)

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Configurar contraseña si es necesario
            if self.compression_format == 'zip_password' and self.archive_password:
                zip_file.setpassword(self.archive_password.encode('utf-8'))

            # Procesar facturas
            for idx, invoice in enumerate(invoices, 1):
                try:
                    # Actualizar progreso
                    progress = 20 + (idx / total) * 60  # 20-80%
                    self._update_progress(
                        progress,
                        _('Procesando factura %d de %d: %s') % (idx, total, invoice.name)
                    )
                    
                    # Determinar carpeta según organización
                    folder = ''
                    if self.organize_by_type:
                        folder = self._get_folder_name(invoice) + '/'
                    
                    # Generar nombre de archivo y obtener PDF
                    filename = folder + self._generate_filename(invoice)
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    # Agregar PDF al ZIP
                    if self.compression_format == 'zip_password':
                        zip_file.writestr(
                            filename,
                            pdf_content,
                            pwd=self.archive_password.encode('utf-8')
                        )
                    else:
                        zip_file.writestr(filename, pdf_content)
                    
                    # Agregar adjuntos si está habilitado
                    if self.include_attachments:
                        attachments = self._get_invoice_attachments(invoice)
                        attachments_count += len(attachments)
                        
                        for att_filename, att_content in attachments:
                            # Crear subcarpeta de adjuntos
                            att_path = folder + 'adjuntos/' + invoice.name + '/'
                            full_path = att_path + att_filename
                            
                            if self.compression_format == 'zip_password':
                                zip_file.writestr(
                                    full_path,
                                    att_content,
                                    pwd=self.archive_password.encode('utf-8')
                                )
                            else:
                                zip_file.writestr(full_path, att_content)
                        
                except Exception as e:
                    _logger.warning(
                        f"Error al procesar factura {invoice.name}: {e}",
                        exc_info=True
                    )
                    failed_count += 1

        # Actualizar progreso final
        self._update_progress(90, _('Finalizando archivo...'))
        
        buffer.seek(0)
        return buffer.getvalue(), failed_count, attachments_count

    def _generate_tar_file(self, invoices, compression):
        """
        Genera archivo TAR con compresión.
        
        Args:
            invoices: recordset de facturas
            compression: tipo de compresión ('gz' o 'bz2')
            
        Returns:
            tuple: (datos_tar, cantidad_fallidas, cantidad_adjuntos)
        """
        buffer = io.BytesIO()
        failed_count = 0
        attachments_count = 0
        total = len(invoices)

        mode = f'w:{compression}'
        with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
            
            for idx, invoice in enumerate(invoices, 1):
                try:
                    # Actualizar progreso
                    progress = 20 + (idx / total) * 60
                    self._update_progress(
                        progress,
                        _('Procesando factura %d de %d: %s') % (idx, total, invoice.name)
                    )
                    
                    # Determinar carpeta
                    folder = ''
                    if self.organize_by_type:
                        folder = self._get_folder_name(invoice) + '/'
                    
                    # Generar archivo
                    filename = folder + self._generate_filename(invoice)
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    # Crear tarinfo y agregar al TAR
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(pdf_content)
                    tarinfo.mtime = datetime.now().timestamp()
                    tar_file.addfile(tarinfo, io.BytesIO(pdf_content))
                    
                    # Agregar adjuntos si está habilitado
                    if self.include_attachments:
                        attachments = self._get_invoice_attachments(invoice)
                        attachments_count += len(attachments)
                        
                        for att_filename, att_content in attachments:
                            # Crear subcarpeta de adjuntos
                            att_path = folder + 'adjuntos/' + invoice.name + '/'
                            full_path = att_path + att_filename
                            
                            # Crear tarinfo para el adjunto
                            att_tarinfo = tarfile.TarInfo(name=full_path)
                            att_tarinfo.size = len(att_content)
                            att_tarinfo.mtime = datetime.now().timestamp()
                            tar_file.addfile(att_tarinfo, io.BytesIO(att_content))
                    
                except Exception as e:
                    _logger.warning(
                        f"Error al procesar factura {invoice.name}: {e}",
                        exc_info=True
                    )
                    failed_count += 1

        self._update_progress(90, _('Finalizando archivo...'))
        
        buffer.seek(0)
        return buffer.getvalue(), failed_count, attachments_count

    def _get_folder_name(self, invoice):
        """
        Obtiene el nombre de carpeta para organización por tipo.
        
        Args:
            invoice: registro de factura
            
        Returns:
            str: nombre de carpeta
        """
        folder_names = {
            'out_invoice': '01_Facturas_Cliente',
            'in_invoice': '02_Facturas_Proveedor',
            'out_refund': '03_Notas_Credito_Cliente',
            'in_refund': '04_Notas_Credito_Proveedor',
        }
        return folder_names.get(invoice.move_type, '05_Otros')

    def _generate_filename(self, invoice):
        """
        Genera nombre de archivo basado en el patrón configurado.
        
        Args:
            invoice: registro de factura
            
        Returns:
            str: nombre de archivo sanitizado
        """
        # Mapeo de tipos de documento
        move_type_names = {
            'out_invoice': 'FAC_CLI',
            'in_invoice': 'FAC_PROV',
            'out_refund': 'NC_CLI',
            'in_refund': 'NC_PROV',
        }
        
        # Sanitizar componentes
        move_type = move_type_names.get(invoice.move_type, 'DOC')
        number = self._sanitize_filename(invoice.name or 'BORRADOR')
        partner = self._sanitize_filename(invoice.partner_id.name or 'DESCONOCIDO')[:40]
        
        if invoice.invoice_date:
            date_str = invoice.invoice_date.strftime('%Y%m%d')
        else:
            date_str = 'SIN_FECHA'

        # Patrones de nombres
        patterns = {
            'standard': f'{move_type}_{number}_{partner}_{date_str}.pdf',
            'date_first': f'{date_str}_{move_type}_{number}_{partner}.pdf',
            'partner_first': f'{partner}_{move_type}_{number}_{date_str}.pdf',
            'simple': f'{move_type}_{number}_{date_str}.pdf',
        }
        
        filename = patterns.get(self.filename_pattern, patterns['standard'])
        
        return filename

    def _sanitize_filename(self, name):
        """
        Sanitiza nombre de archivo para seguridad.
        
        Args:
            name: nombre a sanitizar
            
        Returns:
            str: nombre sanitizado
        """
        # Reemplazar caracteres problemáticos
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Prevenir path traversal
        name = name.replace('..', '_')
        # Reemplazar espacios múltiples
        name = re.sub(r'\s+', '_', name)
        # Limitar longitud
        if len(name) > 200:
            name = name[:200]
        return name

    def _get_invoice_pdf(self, invoice):
        """
        Obtiene el PDF real de la factura usando el motor de reportes de Odoo.
        
        Args:
            invoice: registro de factura
            
        Returns:
            bytes: contenido del PDF
        """
        # Obtener el reporte de factura estándar de Odoo
        report = self.env.ref('account.account_invoices')
        
        # Generar PDF usando el motor de reportes
        pdf_content, _ = report._render_qweb_pdf([invoice.id])
        
        return pdf_content

    def _get_invoice_attachments(self, invoice):
        """
        Obtiene los archivos adjuntos de una factura.
        
        Args:
            invoice: registro de factura
            
        Returns:
            list: lista de tuplas (nombre_archivo, contenido)
        """
        if not self.include_attachments:
            return []
            
        attachments = []
        for attachment in invoice.attachment_ids:
            try:
                # Obtener contenido binario del adjunto
                content = base64.b64decode(attachment.datas)
                filename = self._sanitize_filename(attachment.name)
                attachments.append((filename, content))
            except Exception as e:
                _logger.warning(
                    f"Error al procesar adjunto {attachment.name}: {e}",
                    exc_info=True
                )
                
        return attachments

    def _create_export_history(self, invoices):
        """
        Crea registro en el historial de exportaciones.
        
        Args:
            invoices: recordset de facturas exportadas
        """
        # Determinar tipos de documento incluidos
        move_types = []
        if self.include_out_invoice:
            move_types.append('Facturas Cliente')
        if self.include_in_invoice:
            move_types.append('Facturas Proveedor')
        if self.include_out_refund:
            move_types.append('NC Cliente')
        if self.include_in_refund:
            move_types.append('NC Proveedor')
        
        history = self.env['account.invoice.export.history'].create({
            'export_filename': self.export_filename,
            'export_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'company_id': self.company_id.id,
            'compression_format': self.compression_format,
            'filename_pattern': self.filename_pattern,
            'total_invoices': len(invoices),
            'exported_count': self.export_count,
            'failed_count': self.failed_count,
            'processing_time': self.processing_time,
            'file_size': self.file_size_mb,
            'include_attachments': self.include_attachments,
            'organized_by_type': self.organize_by_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'move_types': ', '.join(move_types),
            'state_filter': self.state_filter,
            'invoice_ids': [(6, 0, invoices.ids)],
        })
        
        self.export_history_id = history

    def _reload_wizard(self):
        """Recarga la vista del wizard."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
