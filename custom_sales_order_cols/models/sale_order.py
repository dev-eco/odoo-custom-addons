# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_is_paid = fields.Boolean(
        string='Pagado',
        default=False,
        help='Indica si el pedido está marcado como pagado'
    )

    def action_toggle_paid(self):
        """Alterna el estado de pagado y registra mensaje en chatter"""
        for order in self:
            old_state = order.x_is_paid
            order.x_is_paid = not old_state
            
            if order.x_is_paid:
                message = _('Pedido marcado como PAGADO por %s') % self.env.user.name
            else:
                message = _('Pedido marcado como NO PAGADO por %s') % self.env.user.name
            
            order.message_post(body=message)
        
        return True
