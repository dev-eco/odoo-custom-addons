from odoo import models, api
from odoo import SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def preview_invoice(self):
        """Método para obtener la acción de vista previa de una factura"""
        self.ensure_one()
        
        # Intentar encontrar informes relacionados con facturas
        if self.move_type in ('out_invoice', 'out_refund'):
            report_ref = 'account.account_invoices'
        else:
            report_ref = 'account.account_invoices_without_payment'
            
        # Buscar el informe por referencia
        try:
            return {
                'type': 'ir.actions.report',
                'report_name': report_ref,
                'report_type': 'qweb-pdf',
                'context': {'active_id': self.id, 'active_model': 'account.move'},
            }
        except:
            # Si falla, buscar cualquier informe válido para facturas
            reports = self.env['ir.actions.report'].sudo().search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1)
            
            if reports:
                return {
                    'type': 'ir.actions.report',
                    'report_name': reports[0].report_name,
                    'report_type': 'qweb-pdf',
                    'context': {'active_id': self.id, 'active_model': 'account.move'},
                }
            
            return False

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
