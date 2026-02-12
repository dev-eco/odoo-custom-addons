# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class DistributorStatistics(models.Model):
    """Estadísticas y métricas para distribuidores."""
    
    _name = 'distributor.statistics'
    _description = 'Estadísticas Distribuidor'
    _rec_name = 'partner_id'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Período
    period_start = fields.Date(
        string='Inicio Período',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    
    period_end = fields.Date(
        string='Fin Período',
        required=True,
        default=fields.Date.today
    )
    
    # Métricas de pedidos
    total_orders = fields.Integer(
        string='Total Pedidos',
        compute='_compute_order_metrics',
        store=True
    )
    
    confirmed_orders = fields.Integer(
        string='Pedidos Confirmados',
        compute='_compute_order_metrics',
        store=True
    )
    
    cancelled_orders = fields.Integer(
        string='Pedidos Cancelados',
        compute='_compute_order_metrics',
        store=True
    )
    
    total_amount = fields.Monetary(
        string='Importe Total',
        currency_field='currency_id',
        compute='_compute_order_metrics',
        store=True
    )
    
    average_order_value = fields.Monetary(
        string='Valor Medio Pedido',
        currency_field='currency_id',
        compute='_compute_order_metrics',
        store=True
    )
    
    # Métricas de productos
    total_products_ordered = fields.Integer(
        string='Productos Pedidos',
        compute='_compute_product_metrics',
        store=True
    )
    
    top_product_ids = fields.Many2many(
        'product.product',
        string='Productos Más Vendidos',
        compute='_compute_product_metrics',
        store=True
    )
    
    # Métricas de facturación
    total_invoiced = fields.Monetary(
        string='Total Facturado',
        currency_field='currency_id',
        compute='_compute_invoice_metrics',
        store=True
    )
    
    total_paid = fields.Monetary(
        string='Total Pagado',
        currency_field='currency_id',
        compute='_compute_invoice_metrics',
        store=True
    )
    
    pending_payment = fields.Monetary(
        string='Pendiente de Pago',
        currency_field='currency_id',
        compute='_compute_invoice_metrics',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )
    
    @api.depends('partner_id', 'period_start', 'period_end')
    def _compute_order_metrics(self):
        """Calcula métricas de pedidos."""
        for stat in self:
            orders = self.env['sale.order'].search([
                ('partner_id', '=', stat.partner_id.id),
                ('date_order', '>=', stat.period_start),
                ('date_order', '<=', stat.period_end),
            ])
            
            stat.total_orders = len(orders)
            stat.confirmed_orders = len(orders.filtered(lambda o: o.state in ['sale', 'done']))
            stat.cancelled_orders = len(orders.filtered(lambda o: o.state == 'cancel'))
            stat.total_amount = sum(orders.mapped('amount_total'))
            stat.average_order_value = stat.total_amount / stat.total_orders if stat.total_orders > 0 else 0.0
    
    @api.depends('partner_id', 'period_start', 'period_end')
    def _compute_product_metrics(self):
        """Calcula métricas de productos."""
        for stat in self:
            order_lines = self.env['sale.order.line'].search([
                ('order_id.partner_id', '=', stat.partner_id.id),
                ('order_id.date_order', '>=', stat.period_start),
                ('order_id.date_order', '<=', stat.period_end),
                ('order_id.state', 'in', ['sale', 'done']),
            ])
            
            stat.total_products_ordered = int(sum(order_lines.mapped('product_uom_qty')))
            
            # Top 5 productos
            product_qty = {}
            for line in order_lines:
                if line.product_id:
                    product_qty[line.product_id.id] = product_qty.get(line.product_id.id, 0) + line.product_uom_qty
            
            top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[:5]
            stat.top_product_ids = [(6, 0, [p[0] for p in top_products])]
    
    @api.depends('partner_id', 'period_start', 'period_end')
    def _compute_invoice_metrics(self):
        """Calcula métricas de facturación."""
        for stat in self:
            invoices = self.env['account.move'].search([
                ('partner_id', '=', stat.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('invoice_date', '>=', stat.period_start),
                ('invoice_date', '<=', stat.period_end),
                ('state', '=', 'posted'),
            ])
            
            stat.total_invoiced = sum(invoices.mapped('amount_total'))
            stat.total_paid = sum(invoices.filtered(lambda i: i.payment_state == 'paid').mapped('amount_total'))
            stat.pending_payment = stat.total_invoiced - stat.total_paid
    
    def get_statistics_for_portal(self):
        """
        Obtiene estadísticas formateadas para el portal.
        
        Returns:
            dict: Estadísticas completas
        """
        self.ensure_one()
        
        return {
            'period': {
                'start': self.period_start.strftime('%d/%m/%Y'),
                'end': self.period_end.strftime('%d/%m/%Y'),
            },
            'orders': {
                'total': self.total_orders,
                'confirmed': self.confirmed_orders,
                'cancelled': self.cancelled_orders,
                'total_amount': float(self.total_amount),
                'average_value': float(self.average_order_value),
            },
            'products': {
                'total_ordered': self.total_products_ordered,
                'top_products': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'default_code': p.default_code,
                    }
                    for p in self.top_product_ids
                ],
            },
            'invoicing': {
                'total_invoiced': float(self.total_invoiced),
                'total_paid': float(self.total_paid),
                'pending_payment': float(self.pending_payment),
            },
        }
