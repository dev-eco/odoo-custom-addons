from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def action_prepare_individual_downloads(self):
        """Prepara los PDFs individuales para las facturas seleccionadas"""
        # Verificar que hay facturas seleccionadas
        if not self:
            return
            
        # Filtrar solo facturas publicadas
        valid_invoices = self.filtered(lambda inv: inv.state == 'posted')
        
        if not valid_invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aviso',
                    'message': 'No hay facturas publicadas para descargar',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Crear un asistente con las facturas seleccionadas
        wizard = self.env['account.invoice.download.wizard'].create({
            'invoice_ids': [(6, 0, valid_invoices.ids)]
        })
        
        # Abrir el wizard
        return {
            'name': 'Descargar Facturas',
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice.download.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_invoice_print(self):
        """ Método para imprimir facturas """
        self.ensure_one()
        
        # Para facturas de cliente
        if self.move_type in ('out_invoice', 'out_refund'):
            return self.env.ref('account.account_invoices')._get_report_action(self)
        # Para facturas de proveedor
        else:
            return self.env.ref('account.account_invoices_without_payment')._get_report_action(self)
