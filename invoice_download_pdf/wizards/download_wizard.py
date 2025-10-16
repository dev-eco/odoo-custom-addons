from odoo import models, api, fields
from odoo.exceptions import UserError
import base64
import logging

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
    
    @api.model
    def create(self, vals):
        """Sobrescribe el método create para generar las líneas de descarga"""
        res = super(AccountInvoiceDownloadWizard, self).create(vals)
        if res.invoice_ids:
            # Generar líneas para cada factura seleccionada
            for invoice in res.invoice_ids:
                # Primero intentamos obtener el PDF adjunto generado por Odoo
                pdf_attachment = invoice.attachment_ids.filtered(
                    lambda a: a.mimetype == 'application/pdf' and 
                    (a.name.endswith('.pdf') or 'factura' in a.name.lower() or invoice.name in a.name)
                )
                
                # Si no encontramos un adjunto, generamos uno nuevo
                if not pdf_attachment:
                    try:
                        # Generar el PDF para esta factura
                        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                            'account.report_invoice', invoice.ids
                        )
                        
                        # Crear el adjunto
                        attachment_vals = {
                            'name': f"{invoice.name or 'Factura'}.pdf",
                            'datas': base64.b64encode(pdf_content),
                            'res_model': 'account.move',
                            'res_id': invoice.id,
                            'type': 'binary',
                            'mimetype': 'application/pdf',
                        }
                        pdf_attachment = self.env['ir.attachment'].create(attachment_vals)
                    except Exception as e:
                        _logger.error(f"Error al generar PDF para factura {invoice.id}: {str(e)}")
                        continue
                else:
                    # Si hay múltiples, tomamos el primero
                    pdf_attachment = pdf_attachment[0]
                
                # Crear línea de descarga
                self.env['account.invoice.download.line'].create({
                    'wizard_id': res.id,
                    'invoice_id': invoice.id,
                    'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                    'attachment_id': pdf_attachment.id if pdf_attachment else False,
                })
                
        return res

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
    state = fields.Selection(related='invoice_id.state')
    
    def action_download(self):
        """Descargar el PDF individualmente"""
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError('No se encontró un PDF adjunto para esta factura')
        
        # Devolvemos una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
