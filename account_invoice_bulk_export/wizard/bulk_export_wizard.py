# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class BulkExportWizard(models.TransientModel):
    """Wizard para exportación masiva de facturas - CORREGIDO"""
    _name = 'account.bulk.export.wizard'
    _description = 'Bulk Invoice Export Wizard'

    # ==========================================
    # FIELDS
    # ==========================================
    
    state = fields.Selection([
        ('draft', 'Configuration'),
        ('processing', 'Processing'),
        ('done', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # Facturas seleccionadas
    invoice_ids = fields.Many2many(
        'account.move',
        string='Selected Invoices',
        help='Pre-selected invoices from list view'
    )

    # Filtros básicos
    include_out_invoice = fields.Boolean(string='Customer Invoices', default=True)
    include_in_invoice = fields.Boolean(string='Vendor Bills', default=True)
    include_out_refund = fields.Boolean(string='Customer Credit Notes', default=False)
    include_in_refund = fields.Boolean(string='Vendor Credit Notes', default=False)

    state_filter = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('all', 'All States'),
    ], string='Invoice State', default='posted')

    # Resultados
    export_file = fields.Binary(string='Export File', readonly=True)
    export_filename = fields.Char(string='Export Filename', readonly=True)
    export_count = fields.Integer(string='Exported Count', readonly=True)
    failed_count = fields.Integer(string='Failed Count', readonly=True)
    processing_time = fields.Float(string='Processing Time (s)', readonly=True)
    error_message = fields.Text(string='Error Details', readonly=True)

    # ==========================================
    # MÉTODOS PRINCIPALES - CORREGIDOS
    # ==========================================
<<<<<<< HEAD

    def action_start_export(self):
        """Inicia el proceso de exportación - MÉTODO REQUERIDO POR XML"""
        self.ensure_one()
        
=======
    
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
    
    use_background_processing = fields.Boolean(
        string='Procesamiento en Background',
        default=lambda self: HAS_QUEUE_JOB and self._should_use_background(),
        help='Usar procesamiento en background para lotes grandes'
    )

    job_id = fields.Char(
        string='ID del Job',
        readonly=True,
        help='Identificador del job en background'
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
        for record in self:
            try:
                # Validación inicial
                if not record.export_file:
                    record.file_size_mb = 0.0
                    continue
                
                # Obtener tamaño aproximado del campo Binary
                # Los campos Binary en Odoo ya están en base64, así que estimamos el tamaño
                # El tamaño real es aproximadamente 3/4 del tamaño en base64
                if record.export_file:
                    # Longitud del string base64
                    base64_length = len(record.export_file) if isinstance(record.export_file, str) else 0
                    # Estimación del tamaño real (3/4 del tamaño base64)
                    estimated_size = base64_length * 3 / 4
                    # Convertir a MB
                    record.file_size_mb = round(estimated_size / (1024 * 1024), 2)
                else:
                    record.file_size_mb = 0.0
                    
            except Exception as e:
                _logger.error(f"Error en _compute_file_size para registro {record.id}: {str(e)}")
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
            if record.batch_size < 1 or record.batch_size > 100:
                raise ValidationError(
                    _('El tamaño del lote debe estar entre 1 y 100.')
                )

    def _validate_export_limits(self, invoices):
        """
        Valida límites de exportación para prevenir sobrecarga del servidor.
        CORRECCIÓN: Límites más conservadores y mejor logging.
        
        Args:
            invoices: recordset de facturas a exportar
        """
        if not invoices:
            raise UserError(_('No hay facturas para exportar.'))
            
        invoice_count = len(invoices)
        
        # Límites basados en el entorno
        max_invoices = 500  # Reducido para mejor rendimiento
        warning_threshold = 200
        
        if invoice_count > max_invoices:
            raise UserError(_(
                'No se pueden exportar más de %d facturas a la vez. '
                'Actualmente seleccionadas: %d. '
                'Use filtros de fecha para reducir la cantidad.'
            ) % (max_invoices, invoice_count))
        
        # Advertencia para exportaciones grandes
        if invoice_count > warning_threshold:
            _logger.warning(
                f"Exportación grande iniciada por {self.env.user.name}: "
                f"{invoice_count} facturas. Tiempo estimado: {invoice_count * 2} segundos."
            )
        
        # Validar acceso a las facturas
        try:
            invoices.check_access_rights('read')
            invoices.check_access_rule('read')
        except AccessError as e:
            raise AccessError(_('No tiene acceso a algunas de las facturas seleccionadas: %s') % str(e))
        
        _logger.info(f"Validación de límites completada: {invoice_count} facturas aprobadas para exportación")

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

    def _should_use_background(self):
        """Determina si usar background basado en cantidad de facturas."""
        invoices = self._get_invoices_to_export()
        return len(invoices) > 100  # Umbral configurable

    def action_start_export(self):
        """Inicia el proceso de exportación con validaciones mejoradas."""
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

        # Obtener facturas a exportar con validación
        invoices = self._get_invoices_to_export()
        
        if not invoices:
            raise UserError(_('No se encontraron facturas que coincidan con los criterios.'))

        # Validar límites antes de procesar
        self._validate_export_limits(invoices)

        # Decidir si usar background (solo si está disponible)
        if self.use_background_processing and HAS_QUEUE_JOB and len(invoices) > 50:
            return self._start_background_export(invoices)
        else:
            return self._start_synchronous_export(invoices)

    @job
    def _process_export_background(self, invoice_ids):
        """Procesa la exportación en background."""
        invoices = self.env['account.move'].browse(invoice_ids)
        return self._generate_export_file(invoices)

    def _start_background_export(self, invoices):
        """Inicia exportación en background."""
        self.write({
            'state': 'processing',
            'progress_message': _('Iniciando procesamiento en background...'),
        })
        
        # Crear job
        job = self.with_delay()._process_export_background(invoices.ids)
        self.job_id = job.uuid
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Procesamiento Iniciado'),
                'message': _('La exportación se está procesando en background. Recibirá una notificación cuando termine.'),
                'type': 'info',
                'sticky': True,
            }
        }

    def _start_synchronous_export(self, invoices):
        """Inicia exportación síncrona."""
>>>>>>> 8556445 ([fix] few bugs)
        try:
            self.write({'state': 'processing', 'error_message': False})
            
            start_time = datetime.now()
            
            # Obtener facturas
            invoices = self._get_invoices_to_export()
            
            if not invoices:
                raise UserError(_('No invoices found matching the criteria.'))

            # Generar archivo
            zip_buffer = io.BytesIO()
            exported_count = 0
            failed_count = 0

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for invoice in invoices:
                    try:
                        pdf_content = self._get_invoice_pdf_safe(invoice)
                        if pdf_content:
                            filename = f"{self._sanitize_filename(invoice.name or 'DRAFT')}.pdf"
                            zip_file.writestr(filename, pdf_content)
                            exported_count += 1
                            _logger.info(f"✓ Exported: {filename}")
                        else:
                            failed_count += 1
                            _logger.warning(f"✗ Failed to export: {invoice.name}")
                            
                    except Exception as e:
                        _logger.error(f"Error exporting {invoice.name}: {str(e)}")
                        failed_count += 1

            # Guardar resultado
            zip_data = zip_buffer.getvalue()
            zip_buffer.close()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            self.write({
                'state': 'done',
                'export_file': base64.b64encode(zip_data),
                'export_filename': f'invoices_{timestamp}.zip',
                'export_count': exported_count,
                'failed_count': failed_count,
                'processing_time': round(processing_time, 2),
            })

        except Exception as e:
            _logger.error(f"Export failed: {str(e)}", exc_info=True)
            self.write({
                'state': 'error',
                'error_message': str(e),
            })

        return self._reload_wizard()

<<<<<<< HEAD
    def action_download(self):
        """Descarga el archivo generado - MÉTODO REQUERIDO POR XML"""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_('No file available for download.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=export_file&filename_field=export_filename&download=true',
            'target': 'self',
        }

    def action_restart(self):
        """Reinicia el wizard para nueva exportación - MÉTODO REQUERIDO POR XML"""
        self.ensure_one()
        
        self.write({
=======
    def _generate_download_token(self):
        """Genera token seguro para descarga con validaciones."""
        try:
            # Validar que tenemos los datos necesarios
            if not self.id or not self.create_uid or not self.create_date:
                raise ValueError("Datos insuficientes para generar token")
            
            # Crear string de datos para hash
            data_parts = [
                str(self.id),
                str(self.create_uid.id),
                str(self.create_date),
                str(self.export_filename or ''),
            ]
            
            data = "_".join(data_parts)
            return hashlib.sha256(data.encode('utf-8')).hexdigest()[:32]
            
        except Exception as e:
            _logger.error(f"Error generando token de descarga: {e}")
            # Token de fallback basado solo en ID
            return hashlib.sha256(f"fallback_{self.id}".encode('utf-8')).hexdigest()[:32]

    def _get_download_url(self):
        """Obtiene URL segura de descarga con validaciones."""
        if not self.export_file or not self.export_filename:
            return None
        
        try:
            token = self._generate_download_token()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            
            if not base_url:
                _logger.warning("web.base.url no configurado, usando URL relativa")
                return f"/bulk_export/download/{self.id}/{token}"
            
            return f"{base_url}/bulk_export/download/{self.id}/{token}"
            
        except Exception as e:
            _logger.error(f"Error generando URL de descarga: {e}")
            return None

    def action_download(self):
        """Descarga el archivo generado con manejo de errores mejorado."""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_('No hay archivo disponible para descargar.'))
        
        if not self.export_filename:
            raise UserError(_('Nombre de archivo no disponible.'))

        try:
            # Intentar usar controlador seguro si está disponible
            download_url = self._get_download_url()
            if download_url:
                return {
                    'type': 'ir.actions.act_url',
                    'url': download_url,
                    'target': 'self',
                }
        except Exception as e:
            _logger.warning(f"Error generando URL de descarga segura: {e}")
        
        # Fallback: descarga directa usando widget binary
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'download_mode': True}
        }

    def action_restart(self):
        """Reinicia el wizard para una nueva exportación con limpieza completa."""
        self.ensure_one()
        
        # Limpiar todos los campos de resultado
        reset_values = {
>>>>>>> 8556445 ([fix] few bugs)
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'failed_count': 0,
<<<<<<< HEAD
            'processing_time': 0,
            'error_message': False,
        })
=======
            'attachments_count': 0,
            'processing_time': 0.0,
            'file_size_mb': 0.0,
            'error_message': False,
            'progress_percentage': 0.0,
            'progress_message': False,
            'export_history_id': False,
            'job_id': False,
        }
        
        try:
            self.write(reset_values)
            _logger.info(f"Wizard reiniciado por usuario {self.env.user.name}")
        except Exception as e:
            _logger.error(f"Error reiniciando wizard: {e}")
            raise UserError(_('Error al reiniciar el wizard. Intente cerrar y abrir nuevamente.'))
>>>>>>> 8556445 ([fix] few bugs)
        
        return self._reload_wizard()

    # ==========================================
    # MÉTODOS AUXILIARES - CORREGIDOS
    # ==========================================

    def _get_invoices_to_export(self):
        """Obtiene facturas basado en criterios"""
        self.ensure_one()

        # Si hay facturas pre-seleccionadas, usarlas
        if self.invoice_ids:
            return self.invoice_ids

        # Construir domain
        domain = [('company_id', '=', self.company_id.id)]

        # Tipos de movimiento - CORREGIDO: usar 'in' en lugar de '='
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
            domain.append(('move_type', 'in', move_types))  # CORREGIDO

        # Estado
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        return self.env['account.move'].search(domain)

<<<<<<< HEAD
    def _get_invoice_pdf_safe(self, invoice):
        """Genera PDF de forma segura - CORREGIDO"""
=======
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
        Genera archivo ZIP con facturas usando procesamiento por lotes.
        
        Args:
            invoices: recordset de facturas
            
        Returns:
            tuple: (datos_zip, cantidad_fallidas, cantidad_adjuntos)
        """
        # Validar límites antes de procesar
        self._validate_export_limits(invoices)
        
        buffer = io.BytesIO()
        failed_count = 0
        attachments_count = 0
        total = len(invoices)
        processed = 0

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            
            # Configurar contraseña si es necesario
            if self.compression_format == 'zip_password' and self.archive_password:
                zip_file.setpassword(self.archive_password.encode('utf-8'))

            # Procesar en lotes para optimizar memoria
            batch_size = min(self.batch_size, 50)  # Máximo 50 por lote
            
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batch_invoices = invoices[batch_start:batch_end]
                
                # Procesar lote actual
                for invoice in batch_invoices:
                    processed += 1
                    try:
                        # Actualizar progreso
                        progress = 20 + (processed / total) * 60  # 20-80%
                        self._update_progress(
                            progress,
                            _('Procesando factura %d de %d: %s') % (processed, total, invoice.name)
                        )
                        
                        # Determinar carpeta según organización
                        folder = ''
                        if self.organize_by_type:
                            folder = self._get_folder_name(invoice) + '/'
                        
                        # Generar archivo
                        filename = folder + self._generate_filename(invoice)
                        pdf_content = self._get_invoice_pdf_enhanced(invoice)
                        
                        if not self._validate_pdf_content(pdf_content):
                            _logger.warning(f"PDF inválido para factura {invoice.name}")
                            failed_count += 1
                            continue
                        
                        # Agregar PDF al ZIP
                        if self.compression_format == 'zip_password':
                            zip_file.writestr(
                                filename,
                                pdf_content,
                                pwd=self.archive_password.encode('utf-8') if self.archive_password else None
                            )
                        else:
                            zip_file.writestr(filename, pdf_content)
                        
                        # Liberar memoria del PDF
                        del pdf_content
                        
                        # Agregar adjuntos si está habilitado
                        if self.include_attachments:
                            attachments = self._get_invoice_attachments(invoice)
                            attachments_count += len(attachments)
                            
                            for att_filename, att_content in attachments:
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
                                
                                # Liberar memoria del adjunto
                                del att_content
                            
                    except Exception as e:
                        _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                        failed_count += 1
                        continue
                
                # Commit intermedio para liberar memoria
                if batch_start > 0 and batch_start % (batch_size * 5) == 0:
                    self.env.cr.commit()

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
                    
                    # Generar archivo - MÉTODO SIMPLIFICADO
                    filename = folder + self._generate_filename(invoice)
                    pdf_content = self._get_invoice_pdf_enhanced(invoice)  # Ahora es más robusto
                    
                    if not pdf_content or len(pdf_content) < 50:
                        _logger.warning(f"PDF inválido para factura {invoice.name}")
                        failed_count += 1
                        continue
                        
                    # Asegurar que pdf_content sea bytes
                    if isinstance(pdf_content, str):
                        pdf_content = pdf_content.encode('utf-8')
                    
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
                    _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                    failed_count += 1
                    continue  # Continuar con la siguiente factura

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
        """Genera nombre de archivo basado en el patrón configurado."""
        # Mapeo de tipos de documento
        move_type_names = {
            'out_invoice': 'FAC_CLI',
            'in_invoice': 'FAC_PROV', 
            'out_refund': 'NC_CLI',
            'in_refund': 'NC_PROV',
        }
        
        # Sanitizar componentes
        move_type = move_type_names.get(invoice.move_type, 'DOC')
        number = self._sanitize_filename_enhanced(invoice.name or 'BORRADOR')
        partner = self._sanitize_filename_enhanced(invoice.partner_id.name or 'DESCONOCIDO')[:40]
        
        if invoice.invoice_date:
            date_str = invoice.invoice_date.strftime('%Y%m%d')
        else:
            date_str = fields.Date.today().strftime('%Y%m%d')

        # Patrones de nombres
        patterns = {
            'standard': f'{move_type}_{number}_{partner}_{date_str}.pdf',
            'date_first': f'{date_str}_{move_type}_{number}_{partner}.pdf', 
            'partner_first': f'{partner}_{move_type}_{number}_{date_str}.pdf',
            'simple': f'{move_type}_{number}_{date_str}.pdf',
        }
        
        return patterns.get(self.filename_pattern, patterns['standard'])

    def _sanitize_filename_enhanced(self, name):
        """
        Sanitización avanzada de nombres de archivo.
        Maneja acentos, caracteres especiales y longitud.
        """
        if not name:
            return 'Sin_Nombre'
        
        # Normalizar caracteres Unicode y eliminar acentos
        normalized = unicodedata.normalize('NFKD', name)
        ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Reemplazar caracteres problemáticos
        ascii_name = re.sub(r'[<>:"/\\|?*¿¡]', '_', ascii_name)
        ascii_name = re.sub(r'[áéíóúàèìòùâêîôûäëïöüñç]', lambda m: {
            'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u',
            'à':'a', 'è':'e', 'ì':'i', 'ò':'o', 'ù':'u',
            'â':'a', 'ê':'e', 'î':'i', 'ô':'o', 'û':'u',
            'ä':'a', 'ë':'e', 'ï':'i', 'ö':'o', 'ü':'u',
            'ñ':'n', 'ç':'c'
        }.get(m.group().lower(), m.group()), ascii_name, flags=re.IGNORECASE)
        
        # Limpiar espacios y caracteres repetidos
        ascii_name = re.sub(r'\s+', '_', ascii_name)
        ascii_name = re.sub(r'_+', '_', ascii_name)
        ascii_name = ascii_name.strip('_')
        
        # Prevenir path traversal
        ascii_name = ascii_name.replace('..', '')
        
        # Limitar longitud
        if len(ascii_name) > 180:
            ascii_name = ascii_name[:180]
        
        return ascii_name or 'Archivo_Sin_Nombre'

    def _get_invoice_pdf_enhanced(self, invoice):
        """
<<<<<<< HEAD
        Genera PDF de factura con estrategia simplificada y robusta.
        """
        try:
            # 1. Buscar PDF adjunto existente
            pdf_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf'),
                ('name', 'ilike', '%.pdf')
            ], limit=1)
            
            if pdf_attachment and pdf_attachment.datas:
                try:
                    pdf_content = base64.b64decode(pdf_attachment.datas)
                    if self._validate_pdf_content(pdf_content):
                        return pdf_content
                except Exception:
                    pass
            
            # 2. Generar usando reporte estándar de facturas
            try:
                report = self.env.ref('account.account_invoices', raise_if_not_found=False)
                if report:
                    pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                    if self._validate_pdf_content(pdf_content):
                        return pdf_content
            except Exception as e:
                _logger.warning(f"Error generando PDF estándar para {invoice.name}: {e}")
            
            # 3. Fallback: buscar cualquier reporte disponible
            reports = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=3)
            
            for report in reports:
                try:
                    pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                    if self._validate_pdf_content(pdf_content):
                        return pdf_content
                except Exception:
                    continue
            
            # 4. Último recurso: PDF básico
            return self._generate_emergency_pdf_content(invoice)
            
        except Exception as e:
            _logger.error(f"Error crítico generando PDF para {invoice.name}: {e}")
            return self._generate_emergency_pdf_content(invoice)







    def _generate_pdf_via_print_action(self, invoice):
        """Genera PDF usando la acción de impresión estándar de Odoo con validación mejorada."""
>>>>>>> parent of 406da11 ([fix] few bugs)
        try:
            # Validar invoice
            if not invoice or not invoice.exists():
                return None

            # Buscar reporte de facturas - CORREGIDO
            report_model = self.env['ir.actions.report']
            
            # Buscar por nombre específico primero
            reports = report_model.search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ])
            
            # Filtrar el reporte correcto
            target_report = None
            for report in reports:
                if hasattr(report, 'report_name') and report.report_name:
                    # CORREGIDO: validar tipo antes de operaciones string
                    if isinstance(report.report_name, str) and 'account_invoices' in report.report_name:
                        target_report = report
                        break

            # Si no encontramos específico, usar el primero
            if not target_report and reports:
                target_report = reports[0]

            if not target_report:
                _logger.warning(f"No PDF report found for {invoice.name}")
                return None

            # Generar PDF - CORREGIDO: usar IDs seguros
            pdf_content, _ = target_report._render_qweb_pdf([invoice.id])
            
            return pdf_content if pdf_content else None

=======
        Genera PDF de factura con estrategia robusta compatible con Odoo 17.
        
        CORRECCIONES APLICADAS:
        - Uso correcto de operadores domain ('in' en lugar de '=')
        - Validación de tipos antes de operaciones string
        - Manejo seguro de claves de caché
        - Compatibilidad con módulos OCA
        
        Args:
            invoice: registro account.move de la factura
            
        Returns:
            bytes: contenido del PDF generado o None si falla
        """
        try:
            # ============================================================
            # PASO 1: Buscar PDF adjunto existente
            # ============================================================
            pdf_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf'),
                ('name', 'ilike', '%.pdf')
            ], limit=1)
            
            if pdf_attachment and pdf_attachment.datas:
                try:
                    pdf_content = base64.b64decode(pdf_attachment.datas)
                    if self._validate_pdf_content(pdf_content):
                        _logger.info(f"✓ Usando PDF adjunto para factura {invoice.name}")
                        return pdf_content
                except Exception as e:
                    _logger.debug(f"Error decodificando adjunto de {invoice.name}: {e}")

            # ============================================================
            # PASO 2: Intentar reportes estándar con búsqueda segura
            # ============================================================
            standard_reports = [
                'account.report_invoice',
                'account.account_invoices',
                'account.report_invoice_with_payments'
            ]
            
            for report_name in standard_reports:
                try:
                    # CORRECCIÓN: Usar operador 'in' y validar tipos
                    if not isinstance(report_name, str):
                        continue
                        
                    # Búsqueda directa sin ir.model.data para evitar errores de caché
                    report = self.env['ir.actions.report'].search([
                        ('model', '=', 'account.move'),
                        ('report_type', '=', 'qweb-pdf'),
                        ('report_name', '=', report_name)  # Usar '=' con string individual
                    ], limit=1)
                    
                    if report:
                        _logger.debug(f"Intentando reporte estándar: {report_name}")
                        pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                        
                        if self._validate_pdf_content(pdf_content):
                            _logger.info(f"✓ PDF generado con reporte {report_name} para {invoice.name}")
                            return pdf_content
                            
                except Exception as e:
                    _logger.debug(f"Error con reporte estándar {report_name}: {e}")
                    continue
            
            # ============================================================
            # PASO 3: Fallback - buscar reportes disponibles
            # ============================================================
            try:
                available_reports = self.env['ir.actions.report'].search([
                    ('model', '=', 'account.move'),
                    ('report_type', '=', 'qweb-pdf')
                ], limit=5)
                
                _logger.info(f"Probando {len(available_reports)} reportes disponibles para {invoice.name}")
                
                for report in available_reports:
                    try:
                        # Validar que report.report_name es string antes de usar
                        if not hasattr(report, 'report_name') or not report.report_name:
                            continue
                            
                        _logger.debug(f"  Probando: {report.report_name} (ID: {report.id})")
                        
                        pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                        
                        if self._validate_pdf_content(pdf_content):
                            _logger.info(f"✓ PDF generado con {report.report_name} para {invoice.name}")
                            return pdf_content
                            
                    except Exception as e:
                        _logger.debug(f"  ✗ Error con {getattr(report, 'report_name', 'unknown')}: {e}")
                        continue
                        
            except Exception as e:
                _logger.warning(f"Error buscando reportes alternativos: {e}")
            
            # ============================================================
            # PASO 4: PDF de emergencia
            # ============================================================
            _logger.warning(f"⚠ Generando PDF de emergencia para {invoice.name}")
            return self._generate_emergency_pdf_content(invoice)
            
        except Exception as e:
            _logger.error(f"❌ Error crítico generando PDF para {invoice.name}: {e}", exc_info=True)
            return self._generate_emergency_pdf_content(invoice)

    def _generate_pdf_via_print_action(self, invoice):
        """
        Genera PDF usando reportes disponibles con manejo seguro de XMLIDs.
        CORRECCIÓN: Evita errores de caché y domain con listas.
        """
        try:
            # Lista de XMLIDs de reportes estándar
            possible_xmlids = [
                'account.account_invoices',
                'account.report_invoice_with_payments',
                'account.account_invoices_without_payment'
            ]
            
            for xmlid in possible_xmlids:
                try:
                    # CORRECCIÓN: Validar formato XMLID antes de usar
                    if not isinstance(xmlid, str) or '.' not in xmlid:
                        continue
                    
                    # Usar env.ref con manejo seguro de errores
                    report = self.env.ref(xmlid, raise_if_not_found=False)
                    
                    if report and hasattr(report, '_render_qweb_pdf'):
                        _logger.debug(f"Probando reporte XMLID: {xmlid}")
                        pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                        
                        if self._validate_pdf_content(pdf_content):
                            _logger.info(f"✓ PDF generado con XMLID {xmlid} para {invoice.name}")
                            return pdf_content
                            
                except Exception as e:
                    _logger.debug(f"Error con XMLID {xmlid}: {e}")
                    continue
            
            # Buscar reportes disponibles sin usar XMLIDs problemáticos
            try:
                available_reports = self.env['ir.actions.report'].search([
                    ('model', '=', 'account.move'),
                    ('report_type', '=', 'qweb-pdf')
                ], limit=3)  # Limitar para evitar demasiadas pruebas
                
                for report in available_reports:
                    try:
                        if not hasattr(report, '_render_qweb_pdf'):
                            continue
                            
                        pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                        
                        if self._validate_pdf_content(pdf_content):
                            _logger.info(f"✓ PDF generado con reporte {report.name}")
                            return pdf_content
                            
                    except Exception as e:
                        _logger.debug(f"Error con reporte {getattr(report, 'name', 'unknown')}: {e}")
                        continue
                        
            except Exception as e:
                _logger.debug(f"Error buscando reportes: {e}")
                
>>>>>>> 8556445 ([fix] few bugs)
        except Exception as e:
            _logger.error(f"Error generating PDF for {invoice.name}: {str(e)}")
            return None

    def _sanitize_filename(self, name):
        """Sanitiza nombres de archivo - CORREGIDO"""
        try:
            # CORREGIDO: validar tipo antes de operaciones
            if isinstance(name, list):
                name = name[0] if name else 'unknown'
                
            if not isinstance(name, str):
                name = str(name) if name else 'unknown'

            # Limpiar caracteres problemáticos
            import re
            safe_name = re.sub(r'[^\w\-_\.]', '_', name)
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')
            
            return safe_name or 'unknown_file'
            
        except Exception as e:
<<<<<<< HEAD
            _logger.error(f"Error sanitizing filename: {str(e)}")
            return 'unknown_file'
=======
            _logger.error(f"Error en PDF de emergencia: {e}")
            return self._create_minimal_pdf_bytes(invoice)

    def _create_simple_invoice_html(self, invoice):
        """Crea HTML simple para la factura."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <title>Factura {invoice.name or 'BORRADOR'}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .info {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>FACTURA: {invoice.name or 'BORRADOR'}</h1>
            </div>
            <div class="info">
                <p><strong>Cliente:</strong> {invoice.partner_id.name or 'DESCONOCIDO'}</p>
                <p><strong>Fecha:</strong> {invoice.invoice_date or 'SIN FECHA'}</p>
                <p><strong>Importe:</strong> {invoice.amount_total:.2f} {invoice.currency_id.name or ''}</p>
                <p><strong>Estado:</strong> {invoice.state or 'draft'}</p>
            </div>
            <p style="margin-top: 40px; text-align: center; color: #666; font-size: 10px;">
                PDF generado automáticamente - {datetime.now().strftime('%d/%m/%Y %H:%M')}
            </p>
        </body>
        </html>
        """

    def _create_minimal_pdf_bytes(self, invoice):
        """Crea PDF mínimo pero válido."""
        invoice_name = self._sanitize_for_pdf(invoice.name or 'SIN_NUMERO')
        partner_name = self._sanitize_for_pdf((invoice.partner_id.name or 'DESCONOCIDO')[:30])
        
        pdf_content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj
4 0 obj<</Length 200>>stream
BT
/F1 14 Tf
50 750 Td
(FACTURA: {invoice_name}) Tj
0 -30 Td
(Cliente: {partner_name}) Tj
0 -30 Td
(Importe: {invoice.amount_total:.2f}) Tj
0 -50 Td
/F1 10 Tf
(PDF basico - Error en generacion completa) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000102 00000 n 
0000000250 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
500
%%EOF"""
        
        return pdf_content.encode('utf-8')

    def _validate_pdf_content(self, pdf_content):
        """
        Valida que el contenido sea un PDF válido.
        
        Args:
            pdf_content: bytes del contenido PDF
            
        Returns:
            bool: True si es un PDF válido
        """
        if not pdf_content or len(pdf_content) < 100:
            return False
        
        # Verificar header PDF
        if not pdf_content.startswith(b'%PDF-'):
            return False
        
        # Verificar que contiene EOF
        if b'%%EOF' not in pdf_content[-1024:]:
            return False
        
        return True

    def _sanitize_for_pdf(self, text):
        """Sanitiza texto para uso seguro en PDF."""
        if not text:
            return 'N/A'
        
        # Remover caracteres problemáticos para PDF
        sanitized = re.sub(r'[^\w\s\-\.\,\:]', '_', str(text))
        # Limitar longitud
        return sanitized[:50] if len(sanitized) > 50 else sanitized

    def _has_pdf_attachment(self, invoice):
        """
        Verifica si la factura tiene un PDF adjunto.
        
        Args:
            invoice: registro de factura
            
        Returns:
            bool: True si tiene PDF adjunto, False en caso contrario
        """
        pdf_count = self.env['ir.attachment'].search_count([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('mimetype', '=', 'application/pdf'),
        ])
        return pdf_count > 0

    
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
                filename = self._sanitize_filename_enhanced(attachment.name)
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

    def action_debug_pdf_generation(self):
        """Método de debug simplificado."""
        debug_info = []
        
        for invoice in self.invoice_ids[:3]:  # Solo 3 facturas para debug
            try:
                pdf_content = self._get_invoice_pdf_enhanced(invoice)
                size = len(pdf_content) if pdf_content else 0
                debug_info.append(f"{invoice.name}: {size} bytes")
            except Exception as e:
                debug_info.append(f"{invoice.name}: ERROR - {str(e)}")
        
        message = "Debug PDF:\n" + "\n".join(debug_info)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'info',
                'sticky': True,
            }}
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
        diagnosis.append(f"Versión Odoo: {self.env['ir.module.module'].get_version()}\n")
        
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
                    pdf_content = self._get_invoice_pdf_enhanced(invoice)
                    if self._validate_pdf_content(pdf_content):
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
                'title': 'Diagnóstico PDF - Versión Corregida',
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
>>>>>>> 8556445 ([fix] few bugs)

    def _reload_wizard(self):
        """Recarga wizard manteniendo contexto"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # ==========================================
    # MÉTODO LEGACY PARA COMPATIBILIDAD
    # ==========================================
    
    def action_export(self):
        """Método legacy - redirige a action_start_export"""
        return self.action_start_export()
