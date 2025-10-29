from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Pedido de venta origen',
        help='Pedido de venta del que procede esta línea de factura'
    )
    
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Línea de pedido origen',
        help='Línea de pedido de venta original'
    )
