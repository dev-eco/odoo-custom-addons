# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BatchExportWizard(models.TransientModel):
    _name = 'batch.export.wizard'
    _description = 'Wizard para Exportación Masiva de Facturas'

    # ==========================================
    # CAMPOS DEL WIZARD
    # ==========================================
    
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company
    )
    
    date_from = fields.Date(
        string='Fecha Desde',
        help='Filtrar facturas desde esta fecha'
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        help='Filtrar facturas hasta esta fecha'
    )
    
    invoice_type = fields.Selection([
        ('out_invoice', 'Facturas de Cliente'),
        ('in_invoice', 'Facturas de Proveedor'),
        ('out_refund', 'Notas de Crédito Cliente'),
        ('in_refund', 'Notas de Crédito Proveedor'),
        ('all', 'Todos los Tipos')
    ], string='Tipo de Documento', default='all')
    
    state_filter = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicadas'),
        ('all', 'Todos los Estados')
    ], string='Estado', default='posted')
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Contactos Específicos',
        help='Dejar vacío para incluir todos los contactos'
    )
    
    # Campos de resultado
    export_file = fields.Binary(
        string='Archivo ZIP',
        readonly=True
    )
    
    export_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True
    )
    
    export_count = fields.Integer(
        string='Facturas Exportadas',
        readonly=True
    )
    
    failed_count = fields.Integer(
        string='Facturas con Error',
        readonly=True
    )
    
    processing_time = fields.Float(
        string='Tiempo de Procesamiento (segundos)',
        readonly=True
    )
    
    error_log = fields.Text(
        string='Log de Errores',
        readonly=True
    )

    # ==========================================
    # MÉTODOS DE VALIDACIÓN
    # ==========================================
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar que las fechas sean coherentes"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError(
                        _('La fecha de inicio no puede ser posterior a la fecha final.')
                    )

    # ==========================================
    # MÉTODOS PRINCIPALES
    # ==========================================
    
    def action_export_invoices(self):
        """Método principal para exportar las facturas"""
        self.ensure_one()
        start_time = datetime.now()
        
        try:
            # 1. Filtrar facturas según criterios
            invoices = self._filter_invoices()
            
            if not invoices:
                raise UserError(_('No se encontraron facturas que coincidan con los criterios.'))
            
            # 2. Crear ZIP con PDFs
            zip_data, export_count, failed_count, error_log = self._create_zip_with_pdfs(invoices)
            
            # 3. Calcular tiempo de procesamiento
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 4. Generar nombre del archivo
            filename = self._generate_filename(export_count)
            
            # 5. Actualizar campos del wizard
            self.write({
                'export_file': base64.b64encode(zip_data),
                'export_filename': filename,
                'export_count': export_count,
                'failed_count': failed_count,
                'processing_time': processing_time,
                'error_log': error_log if error_log else False
            })
            
            # 6. Mostrar notificación de éxito
            message = _('Exportación completada: %d facturas exportadas') % export_count
            if failed_count > 0:
                message += _(', %d facturas con errores') % failed_count
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Exportación Completada'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error('Error en exportación masiva: %s', str(e))
            raise UserError(
                _('Error durante la exportación: %s\n\n'
                  'Verifique los logs del sistema para más detalles.') % str(e)
            )

    def _filter_invoices(self):
        """Filtrar facturas según los criterios del wizard"""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])
        ]
        
        # Filtro por tipo de factura
        if self.invoice_type != 'all':
            domain.append(('move_type', '=', self.invoice_type))
        
        # Filtro por estado
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))
        
        # Filtro por fechas
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        
        # Filtro por contactos específicos
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        
        return self.env['account.move'].search(domain)

    def _create_zip_with_pdfs(self, invoices):
        """Crear archivo ZIP con los PDFs de las facturas"""
        zip_buffer = io.BytesIO()
        export_count = 0
        failed_count = 0
        error_messages = []
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            for invoice in invoices:
                try:
                    # Generar PDF para la factura
                    pdf_content = self._generate_invoice_pdf(invoice)
                    
                    if pdf_content:
                        # Generar nombre del archivo
                        filename = self._generate_pdf_filename(invoice)
                        
                        # Añadir PDF al ZIP
                        zip_file.writestr(filename, pdf_content)
                        export_count += 1
                        
                        _logger.info('PDF generado para factura %s', invoice.name)
                    else:
                        failed_count += 1
                        error_msg = _('No se pudo generar PDF para factura %s') % invoice.name
                        error_messages.append(error_msg)
                        _logger.warning(error_msg)
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = _('Error procesando factura %s: %s') % (invoice.name, str(e))
                    error_messages.append(error_msg)
                    _logger.error('Error procesando factura %s: %s', invoice.name, str(e))
        
        return (
            zip_buffer.getvalue(), 
            export_count, 
            failed_count, 
            '\n'.join(error_messages) if error_messages else False
        )

    def _generate_invoice_pdf(self, invoice):
        """
        Generar PDF para una factura específica usando el motor de reportes de Odoo.
        
        CORRECIÓN CRÍTICA: Usar ir.actions.report en lugar de ir.ui.view
        """
        try:
            # 1. Buscar el reporte de facturas correcto para Odoo 17
            report_name = 'account.report_invoice'
            
            # Método corregido: Buscar el reporte usando ir.actions.report
            report = self.env['ir.actions.report'].search([
                ('report_name', '=', report_name)
            ], limit=1)
            
            if not report:
                # Método de respaldo: Usar el reporte directamente
                try:
                    report = self.env.ref('account.account_invoices')
                except Exception:
                    # Último recurso: Buscar cualquier reporte de facturas
                    report = self.env['ir.actions.report'].search([
                        ('model', '=', 'account.move'),
                        ('report_type', '=', 'qweb-pdf')
                    ], limit=1)
            
            if not report:
                raise UserError(_('No se encontró reporte de facturas configurado.'))
            
            # 2. Generar PDF usando el reporte correcto
            pdf_content, _ = report._render_qweb_pdf(invoice.ids)
            
            return pdf_content
            
        except Exception as e:
            # Método de respaldo usando attachment existente
            _logger.warning(
                'Error en método principal para %s: %s. Intentando método de respaldo.',
                invoice.name, str(e)
            )
            return self._get_pdf_from_attachment(invoice)

    def _get_pdf_from_attachment(self, invoice):
        """
        Método de respaldo: Buscar PDF en attachments existentes
        """
        try:
            # Buscar PDF existente en adjuntos
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf'),
            ], limit=1, order='create_date desc')
            
            if attachment and attachment.datas:
                return base64.b64decode(attachment.datas)
            
        except Exception as e:
            _logger.error('Error en método de respaldo para %s: %s', invoice.name, str(e))
        
        return None

    def _generate_pdf_filename(self, invoice):
        """Generar nombre descriptivo para el archivo PDF"""
        # Sanitizar caracteres especiales
        def sanitize_filename(name):
            if isinstance(name, list):
                # CORRECCIÓN: Si name es una lista, tomar el primer elemento
                name = name[0] if name else 'Unknown'
            
            if not isinstance(name, str):
                name = str(name)
            
            # Reemplazar caracteres problemáticos
            import re
            name = re.sub(r'[<>:"/\\|?*]', '_', name)
            name = re.sub(r'\s+', '_', name)
            return name[:50]  # Limitar longitud
        
        # Obtener datos de la factura
        doc_type = {
            'out_invoice': 'CLIENTE',
            'in_invoice': 'PROVEEDOR', 
            'out_refund': 'NC_CLIENTE',
            'in_refund': 'NC_PROVEEDOR'
        }.get(invoice.move_type, 'DOC')
        
        number = sanitize_filename(invoice.name or 'SIN_NUMERO')
        partner = sanitize_filename(invoice.partner_id.name or 'SIN_CONTACTO')
        date = invoice.invoice_date.strftime('%Y%m%d') if invoice.invoice_date else 'SIN_FECHA'
        
        return f"{doc_type}_{number}_{partner}_{date}.pdf"

    def _generate_filename(self, count):
        """Generar nombre para el archivo ZIP"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        company_code = self.company_id.name[:10].replace(' ', '_')
        return f"Facturas_{company_code}_{count}docs_{timestamp}.zip"

    # ==========================================
    # MÉTODOS DE ACCIÓN DE BOTONES
    # ==========================================
    
    def action_download_zip(self):
        """Acción para descargar el archivo ZIP generado"""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_('No hay archivo para descargar. Primero ejecute la exportación.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=batch.export.wizard&id={self.id}&field=export_file'
                   f'&download=true&filename={self.export_filename}',
            'target': 'self',
        }

    def action_reset_wizard(self):
        """Reiniciar el wizard para una nueva exportación"""
        self.write({
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'failed_count': 0,
            'processing_time': 0.0,
            'error_log': False
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'batch.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
