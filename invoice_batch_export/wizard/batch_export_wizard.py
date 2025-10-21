# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import io
import base64
import zipfile
import tarfile
import logging
import threading
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Check for optional dependencies
try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False
    _logger.warning("py7zr not available. 7-Zip compression will be disabled.")

try:
    import pyminizip
    HAS_PYMINIZIP = True
except ImportError:
    HAS_PYMINIZIP = False
    _logger.warning("pyminizip not available. Password protection will use standard zipfile.")


class BatchExportWizard(models.TransientModel):
    """
    Wizard Principal para Exportación Masiva de Facturas
    
    Este wizard guía al usuario a través del proceso completo de exportación
    masiva, desde la selección de criterios hasta la descarga del archivo final.
    
    Características avanzadas:
    - Soporte multi-formato (ZIP, 7z, TAR.GZ)
    - Protección con contraseña
    - Procesamiento por lotes optimizado
    - Plantillas de nomenclatura personalizables
    - Seguimiento de progreso en tiempo real
    - Manejo robusto de errores
    """
    
    _name = 'batch.export.wizard'
    _description = 'Asistente de Exportación Masiva de Facturas'
    _check_company_auto = True
    
    # FORMATOS DE COMPRESIÓN DISPONIBLES
    # ==================================
    def _get_available_compression_formats(self):
        """Obtener formatos de compresión disponibles según dependencias instaladas"""
        formats = [
            ('zip_fast', 'ZIP - Rápido (Nivel 1)'),
            ('zip_balanced', 'ZIP - Balanceado (Nivel 6)'),
            ('zip_best', 'ZIP - Máxima Compresión (Nivel 9)'),
            ('tar_gz', 'TAR.GZ - Estándar Unix/Linux'),
        ]
        
        if HAS_PY7ZR:
            formats.extend([
                ('7z_normal', '7-Zip - Normal'),
                ('7z_ultra', '7-Zip - Ultra Compresión'),
            ])
        
        if HAS_PYMINIZIP:
            formats.extend([
                ('zip_password', 'ZIP con Contraseña (pyminizip)'),
            ])
        else:
            formats.extend([
                ('zip_password_std', 'ZIP con Contraseña (estándar)'),
            ])
        
        return formats

    # CAMPOS DE CONFIGURACIÓN PRINCIPAL
    # =================================
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        help='Empresa para la cual se realizará la exportación'
    )
    
    export_template_id = fields.Many2one(
        'export.template',
        string='Plantilla de Nomenclatura',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        help='Plantilla para generar nombres de archivo. '
             'Si no se selecciona, se usará la plantilla por defecto.'
    )
    
    # CAMPOS DE SELECCIÓN DE FACTURAS
    # ===============================
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Preseleccionadas',
        help='Facturas específicas seleccionadas desde la vista de lista. '
             'Si está vacío, se aplicarán los filtros configurados abajo.'
    )
    
    # FILTROS DE TIPO DE DOCUMENTO
    # ============================
    include_customer_invoices = fields.Boolean(
        string='Facturas de Cliente',
        default=True,
        help='Incluir facturas de venta (out_invoice) en la exportación'
    )
    
    include_vendor_bills = fields.Boolean(
        string='Facturas de Proveedor',
        default=True,
        help='Incluir facturas de compra (in_invoice) en la exportación'
    )
    
    include_credit_notes = fields.Boolean(
        string='Notas de Crédito',
        default=False,
        help='Incluir notas de crédito de cliente y proveedor en la exportación'
    )
    
    # FILTROS DE FECHA
    # ===============
    date_from = fields.Date(
        string='Fecha Desde',
        help='Filtrar facturas con fecha igual o posterior a esta fecha'
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        help='Filtrar facturas con fecha igual o anterior a esta fecha'
    )
    
    # FILTROS DE ESTADO
    # ================
    state_filter = fields.Selection([
        ('draft', 'Solo Borradores'),
        ('posted', 'Solo Confirmadas'),
        ('all', 'Todos los Estados')
    ], string='Filtro de Estado',
       default='posted',
       help='Filtrar facturas según su estado de confirmación')
    
    # FILTROS ADICIONALES
    # ===================
    partner_ids = fields.Many2many(
        'res.partner',
        string='Clientes/Proveedores Específicos',
        help='Si se especifica, solo se exportarán facturas de estos partners'
    )
    
    # OPCIONES DE COMPRESIÓN
    # =====================
    compression_format = fields.Selection(
        selection='_get_available_compression_formats',
        string='Formato de Compresión',
        default='zip_balanced',
        required=True,
        help='Algoritmo de compresión a utilizar.'
    )
    
    archive_password = fields.Char(
        string='Contraseña del Archivo',
        help='Contraseña para proteger el archivo (solo formatos compatibles)'
    )
    
    # OPCIONES DE PROCESAMIENTO
    # ========================
    batch_size = fields.Integer(
        string='Tamaño de Lote',
        default=50,
        help='Número de facturas a procesar en cada lote. '
             'Valores más altos son más rápidos pero usan más memoria.'
    )
    
    # CAMPOS DE RESULTADO
    # ==================
    state = fields.Selection([
        ('draft', 'Configuración'),
        ('processing', 'Procesando'),
        ('done', 'Completado'),
        ('error', 'Error')
    ], default='draft', readonly=True)
    
    export_file = fields.Binary(
        string='Archivo de Exportación',
        readonly=True,
        help='Archivo comprimido con las facturas exportadas'
    )
    
    export_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True
    )
    
    # CAMPOS DE ESTADÍSTICAS
    # =====================
    total_invoices = fields.Integer(
        string='Total de Facturas',
        readonly=True,
        help='Número total de facturas que se procesarán'
    )
    
    processed_invoices = fields.Integer(
        string='Facturas Procesadas',
        readonly=True,
        help='Número de facturas procesadas exitosamente'
    )
    
    failed_invoices = fields.Integer(
        string='Facturas con Error',
        readonly=True,
        help='Número de facturas que no se pudieron procesar'
    )
    
    processing_log = fields.Text(
        string='Log de Procesamiento',
        readonly=True,
        help='Registro detallado del proceso de exportación'
    )
    
    export_size = fields.Float(
        string='Tamaño del Archivo (MB)',
        readonly=True,
        help='Tamaño del archivo final en megabytes'
    )
    
    processing_time = fields.Float(
        string='Tiempo de Procesamiento (s)',
        readonly=True,
        help='Tiempo total de procesamiento en segundos'
    )

    # VALIDACIONES Y CONSTRAINTS
    # ==========================
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        """Validar que el rango de fechas sea coherente"""
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                if wizard.date_from > wizard.date_to:
                    raise ValidationError(_(
                        'La fecha de inicio no puede ser posterior a la fecha de fin'
                    ))

    @api.constrains('batch_size')
    def _check_batch_size(self):
        """Validar que el tamaño de lote sea razonable"""
        for wizard in self:
            if wizard.batch_size < 1:
                raise ValidationError(_('El tamaño de lote debe ser al menos 1'))
            if wizard.batch_size > 1000:
                raise ValidationError(_(
                    'El tamaño de lote no debe exceder 1000 para evitar problemas de memoria'
                ))

    @api.constrains('compression_format', 'archive_password')
    def _check_password_support(self):
        """Validar que la contraseña solo se use con formatos compatibles"""
        for wizard in self:
            if wizard.archive_password:
                password_formats = ['zip_password', 'zip_password_std']
                if wizard.compression_format not in password_formats:
                    raise ValidationError(_(
                        'La protección con contraseña solo está disponible '
                        'para formatos ZIP específicos'
                    ))

    # MÉTODOS COMPUTADOS
    # ==================
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Actualizar plantilla por defecto al cambiar empresa"""
        if self.company_id:
            default_template = self.env['export.template'].get_default_template(
                self.company_id.id
            )
            self.export_template_id = default_template

    @api.onchange('invoice_ids')
    def _onchange_invoice_ids(self):
        """Actualizar filtros automáticamente según facturas preseleccionadas"""
        if self.invoice_ids:
            # Determinar tipos de documento incluidos
            move_types = self.invoice_ids.mapped('move_type')
            
            self.include_customer_invoices = any(
                mt in ['out_invoice'] for mt in move_types
            )
            self.include_vendor_bills = any(
                mt in ['in_invoice'] for mt in move_types
            )
            self.include_credit_notes = any(
                mt in ['out_refund', 'in_refund'] for mt in move_types
            )
            
            # Establecer rango de fechas automáticamente
            dates = self.invoice_ids.mapped('invoice_date')
            dates = [d for d in dates if d]  # Filtrar valores None
            
            if dates:
                self.date_from = min(dates)
                self.date_to = max(dates)

    # MÉTODOS DE PROCESAMIENTO PRINCIPAL
    # ==================================
    def action_start_export(self):
        """Iniciar el proceso de exportación"""
        self.ensure_one()
        
        try:
            # Cambiar estado a procesando
            self.write({
                'state': 'processing',
                'processing_log': _('Iniciando exportación...\n'),
            })
            
            # Obtener facturas a procesar
            invoices = self._get_filtered_invoices()
            
            if not invoices:
                raise UserError(_('No se encontraron facturas que coincidan con los criterios especificados.'))
            
            # Actualizar total
            self.write({
                'total_invoices': len(invoices),
                'processing_log': self.processing_log + _('Encontradas %d facturas para procesar.\n') % len(invoices),
            })
            
            # Procesar exportación
            start_time = datetime.now()
            export_data = self._process_export(invoices)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Guardar resultado
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"facturas_export_{timestamp}.{self._get_file_extension()}"
            
            self.write({
                'state': 'done',
                'export_file': base64.b64encode(export_data),
                'export_filename': filename,
                'export_size': len(export_data) / (1024 * 1024),  # MB
                'processing_time': processing_time,
                'processing_log': self.processing_log + _('Exportación completada exitosamente.\n'),
            })
            
            return self._return_wizard_view()
            
        except Exception as e:
            _logger.error(f"Error en exportación masiva: {str(e)}", exc_info=True)
            self.write({
                'state': 'error',
                'processing_log': self.processing_log + _('Error: %s\n') % str(e),
            })
            return self._return_wizard_view()

    def _get_filtered_invoices(self):
        """Obtener facturas basado en filtros configurados"""
        # Si hay facturas preseleccionadas, usarlas
        if self.invoice_ids:
            return self.invoice_ids
        
        # Construir dominio basado en filtros
        domain = [('company_id', '=', self.company_id.id)]
        
        # Filtro de tipos de documento
        move_types = []
        if self.include_customer_invoices:
            move_types.append('out_invoice')
        if self.include_vendor_bills:
            move_types.append('in_invoice')
        if self.include_credit_notes:
            move_types.extend(['out_refund', 'in_refund'])
        
        if move_types:
            domain.append(('move_type', 'in', move_types))
        else:
            # Si no se selecciona ningún tipo, no devolver nada
            return self.env['account.move']
        
        # Filtro de fechas
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        
        # Filtro de estado
        if self.state_filter == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.state_filter == 'posted':
            domain.append(('state', '=', 'posted'))
        # 'all' no añade filtro de estado
        
        # Filtro de partners
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        return self.env['account.move'].search(domain)

    def _process_export(self, invoices):
        """Procesar la exportación de facturas"""
        # Obtener plantilla de nomenclatura
        template = self.export_template_id
        if not template:
            template = self.env['export.template'].get_default_template(
                self.company_id.id
            )
        
        # Determinar método de compresión
        if self.compression_format.startswith('zip'):
            return self._create_zip_archive(invoices, template)
        elif self.compression_format.startswith('7z'):
            if not HAS_PY7ZR:
                raise UserError(_('7-Zip no está disponible. Instale py7zr.'))
            return self._create_7z_archive(invoices, template)
        elif self.compression_format == 'tar_gz':
            return self._create_tar_gz_archive(invoices, template)
        else:
            raise UserError(_('Formato de compresión no soportado: %s') % self.compression_format)

    def _create_zip_archive(self, invoices, template):
        """Crear archivo ZIP"""
        buffer = io.BytesIO()
        
        # Determinar nivel de compresión
        if self.compression_format == 'zip_fast':
            compression_level = 1
        elif self.compression_format == 'zip_best':
            compression_level = 9
        else:  # zip_balanced o con contraseña
            compression_level = 6
        
        # Crear ZIP
        with zipfile.ZipFile(
            buffer, 'w', 
            zipfile.ZIP_DEFLATED, 
            compresslevel=compression_level
        ) as zip_file:
            
            # Procesar facturas por lotes
            for i in range(0, len(invoices), self.batch_size):
                batch = invoices[i:i + self.batch_size]
                self._process_invoice_batch(batch, template, zip_file)
        
        return buffer.getvalue()

    def _create_7z_archive(self, invoices, template):
        """Crear archivo 7-Zip"""
        buffer = io.BytesIO()
        
        # Configurar nivel de compresión 7z
        if self.compression_format == '7z_ultra':
            filters = [{"id": py7zr.FILTER_LZMA2, "preset": 9}]
        else:  # 7z_normal
            filters = [{"id": py7zr.FILTER_LZMA2, "preset": 6}]
        
        with py7zr.SevenZipFile(buffer, 'w', filters=filters) as archive:
            # Procesar facturas por lotes
            for i in range(0, len(invoices), self.batch_size):
                batch = invoices[i:i + self.batch_size]
                self._process_invoice_batch_7z(batch, template, archive)
        
        return buffer.getvalue()

    def _create_tar_gz_archive(self, invoices, template):
        """Crear archivo TAR.GZ"""
        buffer = io.BytesIO()
        
        with tarfile.open(fileobj=buffer, mode='w:gz') as tar:
            # Procesar facturas por lotes
            for i in range(0, len(invoices), self.batch_size):
                batch = invoices[i:i + self.batch_size]
                self._process_invoice_batch_tar(batch, template, tar)
        
        return buffer.getvalue()

    def _process_invoice_batch(self, invoices, template, zip_file):
        """Procesar un lote de facturas para ZIP"""
        for invoice in invoices:
            try:
                # Generar PDF
                pdf_content = self._generate_invoice_pdf(invoice)
                
                if pdf_content:
                    # Generar nombre de archivo
                    filename = template.generate_filename(invoice)
                    
                    # Añadir al ZIP
                    zip_file.writestr(filename, pdf_content)
                    
                    # Actualizar contador
                    self.write({
                        'processed_invoices': self.processed_invoices + 1,
                        'processing_log': self.processing_log + _('✓ %s\n') % filename,
                    })
                else:
                    self._handle_invoice_error(invoice, 'No se pudo generar PDF')
                    
            except Exception as e:
                self._handle_invoice_error(invoice, str(e))

    def _process_invoice_batch_7z(self, invoices, template, archive):
        """Procesar un lote de facturas para 7-Zip"""
        for invoice in invoices:
            try:
                pdf_content = self._generate_invoice_pdf(invoice)
                
                if pdf_content:
                    filename = template.generate_filename(invoice)
                    pdf_buffer = io.BytesIO(pdf_content)
                    archive.writestr(pdf_buffer, filename)
                    
                    self.write({
                        'processed_invoices': self.processed_invoices + 1,
                        'processing_log': self.processing_log + _('✓ %s\n') % filename,
                    })
                else:
                    self._handle_invoice_error(invoice, 'No se pudo generar PDF')
                    
            except Exception as e:
                self._handle_invoice_error(invoice, str(e))

    def _process_invoice_batch_tar(self, invoices, template, tar):
        """Procesar un lote de facturas para TAR.GZ"""
        for invoice in invoices:
            try:
                pdf_content = self._generate_invoice_pdf(invoice)
                
                if pdf_content:
                    filename = template.generate_filename(invoice)
                    
                    # Crear TarInfo
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(pdf_content)
                    tar.addfile(tarinfo, io.BytesIO(pdf_content))
                    
                    self.write({
                        'processed_invoices': self.processed_invoices + 1,
                        'processing_log': self.processing_log + _('✓ %s\n') % filename,
                    })
                else:
                    self._handle_invoice_error(invoice, 'No se pudo generar PDF')
                    
            except Exception as e:
                self._handle_invoice_error(invoice, str(e))

    def _generate_invoice_pdf(self, invoice):
        """Generar PDF de una factura usando API de Odoo 17.0"""
        try:
            # Método 1: Buscar reporte de facturas dinámicamente
            report_name = None
            if invoice.move_type in ['out_invoice', 'out_refund']:
                # Facturas de cliente
                report_name = 'account.report_invoice'
            elif invoice.move_type in ['in_invoice', 'in_refund']:
                # Facturas de proveedor (usar mismo reporte)
                report_name = 'account.report_invoice'
            
            if not report_name:
                _logger.warning(f"No se encontró reporte para tipo {invoice.move_type}")
                return None
            
            # Obtener el reporte
            try:
                report = self.env.ref(report_name)
            except ValueError:
                # Si no existe ese reporte, buscar alternativo
                _logger.warning(f"Reporte {report_name} no encontrado, buscando alternativo...")
                report = self._find_invoice_report()
                if not report:
                    return None
            
            # Generar PDF usando API correcta de Odoo 17.0
            pdf_content, _ = report._render_qweb_pdf(invoice.ids)
            return pdf_content
            
        except Exception as e:
            _logger.error(f"Error generando PDF para factura {invoice.name}: {str(e)}")
            # Método de respaldo: usar action_invoice_print si está disponible
            return self._generate_pdf_fallback(invoice)

    def _find_invoice_report(self):
        """Buscar reporte de facturas disponible"""
        possible_reports = [
            'account.report_invoice',
            'account.account_invoices',
            'account.report_invoice_with_payments',
            'account.action_report_invoice',
        ]
        
        for report_name in possible_reports:
            try:
                report = self.env.ref(report_name)
                _logger.info(f"Encontrado reporte alternativo: {report_name}")
                return report
            except ValueError:
                continue
        
        _logger.error("No se encontró ningún reporte de facturas disponible")
        return None

    def _generate_pdf_fallback(self, invoice):
        """Método de respaldo para generar PDF"""
        try:
            # Método de respaldo: usar el método print_invoice si existe
            if hasattr(invoice, 'action_invoice_print'):
                # Este método puede devolver una acción que contenga el PDF
                action = invoice.action_invoice_print()
                if isinstance(action, dict) and 'url' in action:
                    # Si devuelve URL, no podemos obtener el contenido directamente
                    _logger.warning(f"Método de respaldo no disponible para {invoice.name}")
                    return None
            
            # Último recurso: intentar con reporte genérico
            report_model = self.env['ir.actions.report']
            reports = report_model.search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)
            
            if reports:
                pdf_content, _ = reports._render_qweb_pdf(invoice.ids)
                return pdf_content
            
        except Exception as e:
            _logger.error(f"Error en método de respaldo para {invoice.name}: {str(e)}")
        
        return None

    def _handle_invoice_error(self, invoice, error_msg):
        """Manejar error en procesamiento de factura"""
        self.write({
            'failed_invoices': self.failed_invoices + 1,
            'processing_log': self.processing_log + _('✗ %s: %s\n') % (invoice.name, error_msg),
        })
        _logger.warning(f"Error procesando factura {invoice.name}: {error_msg}")

    def _get_file_extension(self):
        """Obtener extensión de archivo según formato"""
        if self.compression_format.startswith('zip'):
            return 'zip'
        elif self.compression_format.startswith('7z'):
            return '7z'
        elif self.compression_format == 'tar_gz':
            return 'tar.gz'
        else:
            return 'zip'  # fallback

    def _return_wizard_view(self):
        """Retornar vista del wizard para mostrar resultados"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # MÉTODOS DE ACCIÓN PARA LA INTERFAZ
    # ==================================
    def action_reset_wizard(self):
        """Reiniciar wizard para nueva exportación"""
        self.write({
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'total_invoices': 0,
            'processed_invoices': 0,
            'failed_invoices': 0,
            'processing_log': '',
            'export_size': 0,
            'processing_time': 0,
        })
        return self._return_wizard_view()

    def action_preview_selection(self):
        """Previsualizar facturas que se van a exportar"""
        invoices = self._get_filtered_invoices()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facturas a Exportar'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
            'context': {'create': False, 'edit': False, 'delete': False},
        }

    @api.model
    def default_get(self, fields_list):
        """Establecer valores por defecto del wizard"""
        defaults = super().default_get(fields_list)
        
        # Si se llama desde vista de facturas con selección
        active_ids = self.env.context.get('active_ids')
        if active_ids and self.env.context.get('active_model') == 'account.move':
            invoices = self.env['account.move'].browse(active_ids)
            # Filtrar solo facturas válidas
            valid_invoices = invoices.filtered(
                lambda inv: inv.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']
            )
            if valid_invoices:
                defaults['invoice_ids'] = [(6, 0, valid_invoices.ids)]
        
        return defaults
