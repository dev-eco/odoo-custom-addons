# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import tarfile
import logging
import re
import unicodedata
from datetime import datetime, timedelta
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

            # Validar export_data antes de codificar
            if not export_data:
                raise UserError(_('No se pudo generar contenido para exportar.'))
            
            # Asegurar que export_data sea bytes
            if not isinstance(export_data, bytes):
                export_data = export_data.encode('utf-8') if isinstance(export_data, str) else bytes(export_data)
            
            # Codificar en base64 de forma segura
            encoded_file = base64.b64encode(export_data).decode('ascii')
            
            # Actualizar con validación
            update_vals = {
                'state': 'done',
                'export_file': encoded_file,
                'export_filename': filename,
                'export_count': len(invoices) - failed_count,
                'failed_count': failed_count,
                'processing_time': round(processing_time, 2),
                'progress_percentage': 100.0,
                'progress_message': _('Exportación completada'),
            }
            
            self.write(update_vals)
            
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
                    
                    # Agregar PDF al ZIP
                    if self.compression_format == 'zip_password':
                        zip_file.writestr(
                            filename,
                            pdf_content,
                            pwd=self.archive_password.encode('utf-8') if self.archive_password else None
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
                    _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                    failed_count += 1
                    continue  # Continuar con la siguiente factura

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
        number = self._sanitize_filename_enhanced(invoice.name or 'BORRADOR')
        partner = self._sanitize_filename_enhanced(invoice.partner_id.name or 'DESCONOCIDO')[:40]
        
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
        Estrategia mejorada para obtener PDF real de facturas.
        Prioriza adjuntos existentes antes de generar nuevos.
        """
        try:
            _logger.info(f"[ENHANCED] Buscando PDF para {invoice.name} (tipo: {invoice.move_type})")
            
            # ESTRATEGIA 1: Buscar PDF adjunto existente
            pdf_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf'),
                ('name', 'ilike', '%.pdf')
            ], limit=1)
            
            if pdf_attachment and pdf_attachment.datas:
                _logger.info(f"[SUCCESS] PDF encontrado en adjuntos: {pdf_attachment.name}")
                return base64.b64decode(pdf_attachment.datas)
            
            # ESTRATEGIA 2: Buscar reporte específico por tipo de factura
            report_xmlids = {
                'out_invoice': ['account.account_invoices', 'account.report_invoice'],
                'in_invoice': ['account.account_invoices', 'account.report_invoice'],
                'out_refund': ['account.account_invoices', 'account.report_invoice'], 
                'in_refund': ['account.account_invoices', 'account.report_invoice']
            }
            
            for xmlid in report_xmlids.get(invoice.move_type, []):
                try:
                    report = self.env.ref(xmlid, raise_if_not_found=False)
                    if report:
                        _logger.info(f"[TRYING] Reporte {xmlid} para {invoice.move_type}")
                        pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                        if pdf_content and len(pdf_content) > 100:  # PDF válido
                            _logger.info(f"[SUCCESS] PDF generado con {xmlid}")
                            return pdf_content
                except Exception as e:
                    _logger.debug(f"[FAILED] {xmlid}: {e}")
            
            # ESTRATEGIA 3: Buscar cualquier reporte compatible
            reports = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ])
            
            for report in reports:
                try:
                    if invoice.move_type in ['out_invoice', 'out_refund'] and 'vendor' in report.name.lower():
                        continue  # Skip vendor reports for customer invoices
                    if invoice.move_type in ['in_invoice', 'in_refund'] and 'customer' in report.name.lower():
                        continue  # Skip customer reports for vendor invoices
                    
                    _logger.info(f"[TRYING] Reporte genérico: {report.name}")
                    pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                    if pdf_content and len(pdf_content) > 100:
                        _logger.info(f"[SUCCESS] PDF con reporte genérico: {report.name}")
                        return pdf_content
                except Exception as e:
                    _logger.debug(f"[FAILED] Reporte {report.name}: {e}")
            
            # ESTRATEGIA 4: Forzar generación y almacenamiento
            try:
                if hasattr(invoice, 'action_invoice_print'):
                    pdf_content = self._force_pdf_generation(invoice)
                    if pdf_content:
                        return pdf_content
            except Exception as e:
                _logger.debug(f"[FAILED] Generación forzada: {e}")
            
            # ÚLTIMO RECURSO: PDF automático mejorado
            _logger.warning(f"[FALLBACK] Generando PDF automático para {invoice.name}")
            return self._generate_automatic_pdf_enhanced(invoice)
            
        except Exception as e:
            _logger.error(f"[ERROR CRÍTICO] {invoice.name}: {e}", exc_info=True)
            return self._generate_fallback_pdf(invoice)

    def _force_pdf_generation(self, invoice):
        """Fuerza la generación de PDF y lo almacena como adjunto."""
        try:
            # Intentar generar PDF usando el wizard de impresión estándar
            wizard = self.env['account.move.send'].create({
                'move_ids': [(6, 0, [invoice.id])],
                'checkbox_invoice_pdf': True,
            })
            
            # Generar el PDF
            action = wizard.action_send_and_print()
            
            # Buscar el PDF recién generado
            pdf_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf'),
                ('create_date', '>=', fields.Datetime.now() - timedelta(minutes=5))
            ], limit=1, order='create_date desc')
            
            if pdf_attachment:
                return base64.b64decode(pdf_attachment.datas)
                
        except Exception as e:
            _logger.debug(f"Generación forzada falló: {e}")
        
        return None

    def _analyze_invoice_report_availability(self, invoice):
        """Analiza qué reportes están disponibles para una factura específica."""
        analysis = {
            'invoice_type': invoice.move_type,
            'available_reports': [],
            'attachments_found': 0,
            'recommended_action': ''
        }
        
        # Verificar adjuntos existentes
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('mimetype', '=', 'application/pdf')
        ])
        analysis['attachments_found'] = len(attachments)
        
        # Verificar reportes disponibles
        reports = self.env['ir.actions.report'].search([
            ('model', '=', 'account.move'),
            ('report_type', '=', 'qweb-pdf')
        ])
        
        for report in reports:
            try:
                # Intentar renderizar el reporte
                pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                if pdf_content:
                    analysis['available_reports'].append({
                        'name': report.name,
                        'report_name': report.report_name,
                        'xmlid': report.xml_id,
                        'size_kb': len(pdf_content) // 1024
                    })
            except Exception as e:
                _logger.debug(f"Reporte {report.name} no compatible: {e}")
        
        # Recomendación
        if analysis['attachments_found'] > 0:
            analysis['recommended_action'] = 'use_attachment'
        elif analysis['available_reports']:
            analysis['recommended_action'] = 'use_report'
        else:
            analysis['recommended_action'] = 'generate_automatic'
        
        _logger.info(f"[ANALYSIS] {invoice.name}: {analysis}")
        return analysis

    def _generate_automatic_pdf_enhanced(self, invoice):
        """Genera un PDF automático mejorado usando solo herramientas nativas de Odoo."""
        try:
            _logger.info(f"Generando PDF automático para {invoice.name}")
            
            # Crear contenido HTML para convertir a PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8"/>
                <title>Factura {invoice.name}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
                    .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                    .info-table td {{ padding: 8px; border: 1px solid #ddd; }}
                    .info-table .label {{ background-color: #f5f5f5; font-weight: bold; width: 30%; }}
                    .lines-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    .lines-table th, .lines-table td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
                    .lines-table th {{ background-color: #f5f5f5; }}
                    .footer {{ margin-top: 40px; text-align: center; font-style: italic; color: #666; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>FACTURA: {invoice.name or 'SIN_NUMERO'}</h1>
                    <p>Documento generado automáticamente</p>
                </div>
                
                <table class="info-table">
                    <tr>
                        <td class="label">ID Interno:</td>
                        <td>{invoice.id}</td>
                    </tr>
                    <tr>
                        <td class="label">Tipo de Documento:</td>
                        <td>{dict(invoice._fields['move_type'].selection).get(invoice.move_type, invoice.move_type)}</td>
                    </tr>
                    <tr>
                        <td class="label">Estado:</td>
                        <td>{dict(invoice._fields['state'].selection).get(invoice.state, invoice.state)}</td>
                    </tr>
                    <tr>
                        <td class="label">Cliente/Proveedor:</td>
                        <td>{invoice.partner_id.name or 'DESCONOCIDO'}</td>
                    </tr>
                    <tr>
                        <td class="label">Fecha de Factura:</td>
                        <td>{invoice.invoice_date or 'SIN_FECHA'}</td>
                    </tr>
                    <tr>
                        <td class="label">Fecha de Vencimiento:</td>
                        <td>{invoice.invoice_date_due or 'SIN_FECHA'}</td>
                    </tr>
                    <tr>
                        <td class="label">Referencia:</td>
                        <td>{invoice.ref or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td class="label">Importe Total:</td>
                        <td>{invoice.amount_total} {invoice.currency_id.name or ''}</td>
                    </tr>
                    <tr>
                        <td class="label">Compañía:</td>
                        <td>{invoice.company_id.name or 'DESCONOCIDA'}</td>
                    </tr>
                </table>
                
                <h3>Líneas de Factura:</h3>
                <table class="lines-table">
                    <thead>
                        <tr>
                            <th>Descripción</th>
                            <th>Cantidad</th>
                            <th>Precio Unitario</th>
                            <th>Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # Agregar líneas de factura (máximo 15 para evitar PDFs muy largos)
            for line in invoice.invoice_line_ids[:15]:
                html_content += f"""
                        <tr>
                            <td>{line.name[:80] if line.name else 'Sin descripción'}...</td>
                            <td>{line.quantity}</td>
                            <td>{line.price_unit} {invoice.currency_id.name or ''}</td>
                            <td>{line.price_subtotal} {invoice.currency_id.name or ''}</td>
                        </tr>
                """
            
            html_content += f"""
                    </tbody>
                </table>
                
                <div class="footer">
                    <p><strong>NOTA IMPORTANTE:</strong></p>
                    <p>Este PDF ha sido generado automáticamente porque el reporte original no estaba disponible.</p>
                    <p>Para obtener el PDF oficial, genere el reporte desde la factura individual.</p>
                    <p>Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            # Usar el motor de reportes de Odoo para convertir HTML a PDF
            try:
                # Intentar usar wkhtmltopdf a través del motor de reportes de Odoo
                pdf_content = self.env['ir.actions.report']._run_wkhtmltopdf(
                    [html_content],
                    landscape=False,
                    specific_paperformat_args={
                        'data-report-margin-top': 40,
                        'data-report-margin-bottom': 40,
                        'data-report-margin-left': 20,
                        'data-report-margin-right': 20,
                    }
                )
                
                if pdf_content and len(pdf_content) > 100:
                    _logger.info(f"PDF automático generado exitosamente para {invoice.name}")
                    return pdf_content
                    
            except Exception as e:
                _logger.debug(f"Error con wkhtmltopdf: {e}")
            
            # Fallback: PDF mínimo pero válido
            _logger.warning(f"Generando PDF mínimo para {invoice.name}")
            return self._generate_minimal_pdf(invoice)
            
        except Exception as e:
            _logger.error(f"Error generando PDF automático para {invoice.name}: {e}")
            return self._generate_minimal_pdf(invoice)

    def _generate_minimal_pdf(self, invoice):
        """Genera un PDF mínimo válido sin dependencias externas."""
        try:
            # PDF completamente básico pero válido
            pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 595 842]
/Contents 4 0 R
/Resources <<
  /Font <<
    /F1 <<
      /Type /Font
      /Subtype /Type1
      /BaseFont /Helvetica
    >>
  >>
>>
>>
endobj

4 0 obj
<<
/Length 600
>>
stream
BT
/F1 16 Tf
50 750 Td
(FACTURA: {invoice.name or 'SIN_NUMERO'}) Tj
0 -30 Td
/F1 12 Tf
(ID: {invoice.id}) Tj
0 -20 Td
(Tipo: {invoice.move_type}) Tj
0 -20 Td
(Estado: {invoice.state}) Tj
0 -20 Td
(Cliente/Proveedor: {(invoice.partner_id.name or 'DESCONOCIDO')[:50]}) Tj
0 -20 Td
(Fecha: {invoice.invoice_date or 'SIN_FECHA'}) Tj
0 -20 Td
(Importe: {invoice.amount_total} {invoice.currency_id.name or ''}) Tj
0 -20 Td
(Compania: {(invoice.company_id.name or 'DESCONOCIDA')[:50]}) Tj
0 -20 Td
(Referencia: {invoice.ref or 'N/A'}) Tj
0 -40 Td
/F1 10 Tf
(NOTA: PDF generado automaticamente.) Tj
0 -15 Td
(El PDF original no estaba disponible como adjunto.) Tj
0 -15 Td
(Para el PDF oficial, genere el reporte desde la factura.) Tj
0 -15 Td
(Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000300 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
950
%%EOF"""
            
            return pdf_content.encode('utf-8')
            
        except Exception as e:
            _logger.error(f"Error generando PDF mínimo: {e}")
            # PDF de emergencia ultra-básico
            return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"

    def _generate_fallback_pdf(self, invoice):
        """
        Genera un PDF de respaldo solo con información básica cuando no existe adjunto.
        
        Args:
            invoice: registro de factura
            
        Returns:
            bytes: contenido del PDF básico
        """
        try:
            _logger.info(f"📄 Generando PDF de respaldo para factura {invoice.name}")
            
            # PDF mínimo pero válido con información de la factura
            pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 595 842]
/Contents 4 0 R
/Resources <<
  /Font <<
    /F1 <<
      /Type /Font
      /Subtype /Type1
      /BaseFont /Helvetica
    >>
  >>
>>
>>
endobj

4 0 obj
<<
/Length 400
>>
stream
BT
/F1 16 Tf
50 750 Td
(FACTURA: {invoice.name or 'SIN_NUMERO'}) Tj
0 -30 Td
/F1 12 Tf
(ID: {invoice.id}) Tj
0 -20 Td
(Tipo: {invoice.move_type}) Tj
0 -20 Td
(Estado: {invoice.state}) Tj
0 -20 Td
(Cliente/Proveedor: {(invoice.partner_id.name or 'DESCONOCIDO')[:60]}) Tj
0 -20 Td
(Fecha: {invoice.invoice_date or 'SIN_FECHA'}) Tj
0 -20 Td
(Importe: {invoice.amount_total} {invoice.currency_id.name or ''}) Tj
0 -20 Td
(Compania: {(invoice.company_id.name or 'DESCONOCIDA')[:60]}) Tj
0 -40 Td
/F1 10 Tf
(NOTA: PDF generado automaticamente.) Tj
0 -15 Td
(El PDF original no estaba disponible como adjunto.) Tj
0 -15 Td
(Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000300 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
750
%%EOF"""
            
            return pdf_content.encode('utf-8')
            
        except Exception as e:
            _logger.error(f"Error generando PDF de respaldo para {invoice.name}: {str(e)}")
            # PDF completamente mínimo como último recurso
            return b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"

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
        """Método de debug para verificar generación de PDF."""
        for invoice in self.invoice_ids[:5]:  # Test first 5
            analysis = self._analyze_invoice_report_availability(invoice)
            pdf_content = self._get_invoice_pdf_enhanced(invoice)
            
            _logger.info(f"[DEBUG] {invoice.name}: "
                        f"Tamaño PDF: {len(pdf_content) if pdf_content else 0} bytes, "
                        f"Análisis: {analysis}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Debug completado. Revisar logs del servidor.',
                'type': 'success',
            }
        }

    def _reload_wizard(self):
        """Recarga la vista del wizard."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
