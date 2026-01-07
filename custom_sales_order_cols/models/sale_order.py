# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_is_paid = fields.Boolean(
        string='Pagado',
        compute='_compute_is_paid',
        store=True,
        help='Indica si todas las facturas del pedido están pagadas'
    )

    @api.depends('invoice_ids.payment_state')
    def _compute_is_paid(self):
        """Calcula si el pedido está pagado basándose en las facturas"""
        for order in self:
            if not order.invoice_ids:
                # Si no hay facturas, no está pagado
                order.x_is_paid = False
            else:
                # Filtrar solo facturas de cliente (no devoluciones)
                customer_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice'
                )
                if not customer_invoices:
                    order.x_is_paid = False
                else:
                    # Está pagado si todas las facturas están pagadas
                    order.x_is_paid = all(
                        inv.payment_state in ['paid', 'in_payment'] 
                        for inv in customer_invoices
                    )

    def action_toggle_paid(self):
        """Muestra información sobre el estado de pago automático"""
        for order in self:
            if order.invoice_ids:
                customer_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.move_type == 'out_invoice'
                )
                if customer_invoices:
                    paid_invoices = customer_invoices.filtered(
                        lambda inv: inv.payment_state in ['paid', 'in_payment']
                    )
                    message = _(
                        'Estado de pago automático: %d de %d facturas pagadas. '
                        'Facturas: %s'
                    ) % (
                        len(paid_invoices),
                        len(customer_invoices),
                        ', '.join(customer_invoices.mapped('name'))
                    )
                else:
                    message = _('No hay facturas de cliente para este pedido')
            else:
                message = _('No hay facturas asociadas a este pedido')
            
            order.message_post(body=message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }
