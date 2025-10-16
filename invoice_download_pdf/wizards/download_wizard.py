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
                    # Asegurar que la factura tenga un PDF adjunto
                    pdf_attachment = invoice.ensure_invoice_pdf()
                    
                    if pdf_attachment:
                        # Crear línea de descarga
                        self.env['account.invoice.download.line'].create({
                            'wizard_id': wizard.id,
                            'invoice_id': invoice.id,
                            'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                            'attachment_id': pdf_attachment.id,
                        })
                    else:
                        # Crear línea sin adjunto para informar al usuario
                        self.env['account.invoice.download.line'].create({
                            'wizard_id': wizard.id,
                            'invoice_id': invoice.id,
                            'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                            'attachment_id': False,
                            'state': 'error',
                            'notes': 'No se pudo generar el PDF',
                        })
        
        return records
    
    def action_download_all(self):
        """Descarga todas las facturas en un archivo ZIP"""
        # Verificar que hay líneas válidas para descargar
        valid_lines = self.download_line_ids.filtered(lambda l: l.attachment_id)
        
        if not valid_lines:
            raise UserError('No hay facturas con PDF disponible para descargar')
        
        if len(valid_lines) == 1:
            # Si solo hay una factura, la descargamos directamente
            return valid_lines[0].action_download()
        
        # Para múltiples facturas, crear un archivo ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for line in valid_lines:
                # Obtener el contenido del PDF
                attachment_data = line.attachment_id.datas
                if attachment_data:
                    pdf_content = base64.b64decode(attachment_data)
                    
                    # Crear un nombre de archivo limpio (sin caracteres problemáticos)
                    clean_name = line.name.replace('/', '_').replace('\\', '_')
                    if not clean_name.lower().endswith('.pdf'):
                        clean_name += '.pdf'
                        
                    # Añadir el PDF al archivo ZIP
                    zip_file.writestr(clean_name, pdf_content)
        
        # Crear un nombre para el archivo ZIP
        company_name = self.env.user.company_id.name or 'company'
        today = fields.Date.today().strftime('%Y%m%d')
        zip_name = f"facturas_{company_name}_{today}.zip"
        zip_name = zip_name.replace(' ', '_')
        
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
            # Si no tiene adjunto, intentar generarlo nuevamente
            pdf_attachment = self.invoice_id.ensure_invoice_pdf()
            if pdf_attachment:
                self.attachment_id = pdf_attachment
            else:
                raise UserError('No se pudo generar el PDF para esta factura')
        
        # Devolvemos una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
