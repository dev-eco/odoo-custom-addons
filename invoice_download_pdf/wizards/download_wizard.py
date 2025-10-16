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
    
    # wizards/download_wizard.py - CORRECCIÓN
    @api.model
    def create(self, vals):
        """Sobrescribe el método create para generar las líneas de descarga"""
        res = super(AccountInvoiceDownloadWizard, self).create(vals)
        if res.invoice_ids:
            # Generar líneas para cada factura seleccionada
            for invoice in res.invoice_ids:
                # Verificamos que tenga adjuntos
                pdf_attachments = invoice.attachment_ids.filtered(
                    lambda a: a.mimetype == 'application/pdf'
                )
                
                if not pdf_attachments:
                    # En Odoo 17, podríamos necesitar generar el PDF primero
                    try:
                        # Intentamos imprimir la factura para generar el PDF
                        invoice.action_invoice_print()
                        # Recargamos la factura para obtener los adjuntos actualizados
                        invoice.invalidate_cache()
                        pdf_attachments = invoice.attachment_ids.filtered(
                            lambda a: a.mimetype == 'application/pdf'
                        )
                    except Exception as e:
                        _logger.error(f"Error al generar PDF para factura {invoice.id}: {str(e)}")
                        continue
                
                if pdf_attachments:
                    # Crear línea de descarga con el primer PDF adjunto
                    self.env['account.invoice.download.line'].create({
                        'wizard_id': res.id,
                        'invoice_id': invoice.id,
                        'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                        'attachment_id': pdf_attachments[0].id,
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
