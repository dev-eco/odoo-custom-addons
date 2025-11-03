from odoo import api, fields, models, _


class SaleOrderInvoiceGroup(models.Model):
    _name = 'sale.order.invoice.group'
    _description = 'Relación entre Pedidos de Venta y Facturas Consolidadas'
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Pedido de venta',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura',
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    consolidation_mode = fields.Selection([
        ('sum_by_product', 'Sumar cantidades por producto'),
        ('lines_separate', 'Mantener líneas separadas'),
    ], string='Modo de consolidación', required=True, default='sum_by_product')
    
    date_created = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        required=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        related='sale_order_id.company_id',
        store=True,
    )
    
    _sql_constraints = [
        ('unique_order_invoice', 
         'UNIQUE(sale_order_id, invoice_id)',
         'Un pedido no puede estar asociado más de una vez a la misma factura.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescrito para registrar en el chatter de los pedidos y facturas"""
        records = super().create(vals_list)
        
        # Agrupar por facturas para optimizar
        invoice_to_orders = {}
        for record in records:
            if record.invoice_id not in invoice_to_orders:
                invoice_to_orders[record.invoice_id] = self.env['sale.order']
            invoice_to_orders[record.invoice_id] |= record.sale_order_id

        # Registrar en el chatter de facturas
        for invoice, orders in invoice_to_orders.items():
            order_names = ', '.join(orders.mapped('name'))
            message = _("Esta factura consolida los siguientes pedidos: %s") % order_names
            invoice.message_post(body=message)
        
        # Registrar en el chatter de los pedidos
        for record in records:
            message = _("Este pedido ha sido incluido en la factura consolidada: %s") % record.invoice_id.name
            record.sale_order_id.message_post(body=message)
            
        return records
