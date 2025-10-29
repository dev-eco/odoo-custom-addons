from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_ids = fields.Many2many(
        'sale.order',
        string='Pedidos de venta consolidados',
        compute='_compute_sale_order_ids',
        store=False,
        help='Pedidos de venta incluidos en esta factura'
    )
    
    invoice_group_ids = fields.One2many(
        'sale.order.invoice.group',
        'invoice_id',
        string='Grupos de facturación',
        help='Relación entre esta factura y los pedidos de venta'
    )
    
    is_consolidated_invoice = fields.Boolean(
        string='Es factura consolidada',
        compute='_compute_is_consolidated_invoice',
        store=True,
        help='Indica si esta factura fue creada mediante consolidación de pedidos'
    )
    
    @api.depends('invoice_group_ids')
    def _compute_is_consolidated_invoice(self):
        for record in self:
            record.is_consolidated_invoice = bool(record.invoice_group_ids)
    
    @api.depends('invoice_group_ids.sale_order_id')
    def _compute_sale_order_ids(self):
        for record in self:
            record.sale_order_ids = record.invoice_group_ids.mapped('sale_order_id')
    
    def action_view_source_orders(self):
        """Acción para ver los pedidos de venta origen de esta factura"""
        self.ensure_one()
        action = self.env.ref('sale.action_orders').read()[0]
        
        if len(self.sale_order_ids) > 1:
            action['domain'] = [('id', 'in', self.sale_order_ids.ids)]
        else:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = self.sale_order_ids.id
        
        return action
