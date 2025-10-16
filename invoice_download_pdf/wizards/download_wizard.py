from odoo import models, api, fields
from odoo.exceptions import UserError
import base64
import logging
import io
import zipfile

_logger = logging.getLogger(__name__)

class AccountInvoiceDownloadWizard(models.TransientModel):
    _name = 'account.invoice.download.wizard'
    _description = 'Asistente para descargar facturas individuales'
    
    invoice_ids = fields.Many2many('account.move', string='Facturas')
    download_line_ids = fields.One2many(
        'account.invoice.download.line', 
        'wizard_id', 
        string='Facturas para descargar'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribe el método create para generar las líneas de descarga"""
        records = super(AccountInvoiceDownloadWizard, self).create(vals_list)
        
        # Procesamos cada registro creado
        for wizard in records:
            if wizard.invoice_ids:
                # Generar líneas para cada factura seleccionada
                for invoice in wizard.invoice_ids:
                    # Intentamos encontrar el PDF adjunto o generarlo
                    pdf_data = None
                    
                    # 1. Buscar un adjunto PDF existente
                    pdf_attachment = invoice.attachment_ids.filtered(
                        lambda a: a.mimetype == 'application/pdf'
                    )
                    
                    if pdf_attachment:
                        pdf_data = pdf_attachment[0]
                    else:
                        # 2. Si no existe, intentar generarlo
                        try:
                            # Usar el método estándar de impresión de facturas
                            pdf_data = self._generate_invoice_pdf(invoice)
                        except Exception as e:
                            _logger.error(f"Error generando PDF para factura {invoice.id}: {str(e)}")
                    
                    # Crear la línea de descarga
                    line_vals = {
                        'wizard_id': wizard.id,
                        'invoice_id': invoice.id,
                        'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                        'state': 'valid' if pdf_data else 'error',
                    }
                    
                    if pdf_data:
                        line_vals['attachment_id'] = pdf_data.id
                    else:
                        line_vals['notes'] = 'No se pudo generar el PDF'
                    
                    self.env['account.invoice.download.line'].create(line_vals)
        
        return records
    
    def _generate_invoice_pdf(self, invoice):
        """Genera un PDF para una factura usando el mecanismo nativo de Odoo"""
        try:
            # En lugar de buscar un informe específico por XML ID, obtendremos
            # el informe directamente desde la acción de impresión de la factura
            action = invoice.action_invoice_print()
            
            # La acción devuelta contiene la información del informe a utilizar
            if action and action.get('report_name'):
                # Obtener el informe por su nombre
                report = self.env['ir.actions.report']._get_report_from_name(action.get('report_name'))
                if report:
                    # Generar el PDF con todos los parámetros necesarios
                    pdf_content, _ = report._render_qweb_pdf(invoice.ids)
                    
                    # Crear un adjunto
                    attachment_vals = {
                        'name': f"{invoice.name or 'Factura'}.pdf",
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'mimetype': 'application/pdf',
                    }
                    return self.env['ir.attachment'].create(attachment_vals)
                
            # Si no podemos obtener el informe por la acción, intentamos otra aproximación
            # Buscar todos los informes disponibles relacionados con facturas
            reports = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)
            
            if reports:
                # Usar el primer informe encontrado
                pdf_content, _ = reports[0]._render_qweb_pdf(invoice.ids)
                
                # Crear un adjunto
                attachment_vals = {
                    'name': f"{invoice.name or 'Factura'}.pdf",
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'mimetype': 'application/pdf',
                }
                return self.env['ir.attachment'].create(attachment_vals)
            
            # Si todo lo demás falla, intentamos una última aproximación
            # Buscar si la factura ya tiene un PDF adjunto generado anteriormente
            for attachment in invoice.attachment_ids:
                if attachment.mimetype == 'application/pdf' and ('factura' in attachment.name.lower() or 'invoice' in attachment.name.lower()):
                    return attachment
                    
            return False
        except Exception as e:
            _logger.error(f"Error en _generate_invoice_pdf: {str(e)}")
            return False
    
    def action_download_all(self):
        """Descarga todas las facturas en un archivo ZIP"""
        # Verificar que hay líneas válidas para descargar
        valid_lines = self.download_line_ids.filtered(lambda l: l.attachment_id and l.state == 'valid')
        
        if not valid_lines:
            raise UserError('No hay facturas con PDF disponible para descargar')
        
        if len(valid_lines) == 1:
            # Si solo hay una factura, la descargamos directamente
            return valid_lines[0].action_download()
        
        # Para múltiples facturas, crear un archivo ZIP
        zip_buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for line in valid_lines:
                    try:
                        # Obtener el contenido del PDF
                        pdf_content = base64.b64decode(line.attachment_id.datas)
                        
                        # Crear un nombre de archivo limpio
                        clean_name = line.name.replace('/', '_').replace('\\', '_')
                        if not clean_name.lower().endswith('.pdf'):
                            clean_name += '.pdf'
                            
                        # Añadir el PDF al archivo ZIP
                        zip_file.writestr(clean_name, pdf_content)
                    except Exception as e:
                        _logger.error(f"Error al procesar factura {line.invoice_id.id} para ZIP: {str(e)}")
                        continue
            
            # Crear un nombre para el archivo ZIP
            company_name = self.env.user.company_id.name or 'company'
            today = fields.Date.today().strftime('%Y%m%d')
            zip_name = f"facturas_{company_name}_{today}.zip"
            zip_name = zip_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Crear un adjunto con el archivo ZIP
            attachment_vals = {
                'name': zip_name,
                'datas': base64.b64encode(zip_buffer.getvalue()),
                'mimetype': 'application/zip',
            }
            
            attachment = self.env['ir.attachment'].create(attachment_vals)
            
            # Devolver acción para descargar el archivo ZIP
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{attachment.id}?download=true",
                'target': 'self',
            }
        except Exception as e:
            _logger.error(f"Error al crear archivo ZIP: {str(e)}")
            raise UserError(f"Error al crear archivo ZIP: {str(e)}")

class AccountInvoiceDownloadLine(models.TransientModel):
    _name = 'account.invoice.download.line'
    _description = 'Línea de descarga de factura individual'
    
    wizard_id = fields.Many2one('account.invoice.download.wizard', string='Wizard')
    invoice_id = fields.Many2one('account.move', string='Factura', required=True)
    name = fields.Char('Nombre del archivo', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Adjunto PDF')
    company_id = fields.Many2one(related='invoice_id.company_id')
    partner_id = fields.Many2one(related='invoice_id.partner_id')
    invoice_date = fields.Date(related='invoice_id.invoice_date')
    amount_total = fields.Monetary(related='invoice_id.amount_total')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    state = fields.Selection([
        ('valid', 'Válido'),
        ('error', 'Error'),
    ], string='Estado', default='valid')
    notes = fields.Text('Notas')
    
    def action_download(self):
        """Descargar el PDF individualmente"""
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError('No se pudo generar el PDF para esta factura')
        
        # Devolvemos una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
