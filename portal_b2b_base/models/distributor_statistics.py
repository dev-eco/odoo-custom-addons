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
    
    # Métricas de pedidos (sin store para evitar recalculos costosos)
    total_orders = fields.Integer(
        string='Total Pedidos',
        compute='_compute_order_metrics',
        store=False
    )
    
    confirmed_orders = fields.Integer(
        string='Pedidos Confirmados',
        compute='_compute_order_metrics',
        store=False
    )
    
    cancelled_orders = fields.Integer(
        string='Pedidos Cancelados',
        compute='_compute_order_metrics',
        store=False
    )
    
    total_amount = fields.Monetary(
        string='Importe Total',
        currency_field='currency_id',
        compute='_compute_order_metrics',
        store=False
    )
    
    average_order_value = fields.Monetary(
        string='Valor Medio Pedido',
        currency_field='currency_id',
        compute='_compute_order_metrics',
        store=False
    )
    
    # Métricas de productos (sin store para evitar recalculos costosos)
    total_products_ordered = fields.Integer(
        string='Productos Pedidos',
        compute='_compute_product_metrics',
        store=False
    )
    
    top_product_ids = fields.Many2many(
        'product.product',
        string='Productos Más Vendidos',
        compute='_compute_product_metrics',
        store=False
    )
    
    # Métricas de facturación (sin store para evitar recalculos costosos)
    total_invoiced = fields.Monetary(
        string='Total Facturado',
        currency_field='currency_id',
        compute='_compute_invoice_metrics',
        store=False
    )
    
    total_paid = fields.Monetary(
        string='Total Pagado',
        currency_field='currency_id',
        compute='_compute_invoice_metrics',
        store=False
    )
    
    pending_payment = fields.Monetary(
        string='Pendiente de Pago',
        currency_field='currency_id',
        compute='_compute_invoice_metrics',
        store=False
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

    def get_chart_data_orders_by_month(self):
        """
        Obtiene datos para gráfico de pedidos por mes.
        
        Returns:
            dict: Datos formateados para Chart.js
        """
        self.ensure_one()
        
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        # Últimos 12 meses
        end_date = fields.Date.today()
        start_date = end_date - timedelta(days=365)
        
        orders = self.env['sale.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
            ('state', 'in', ['sale', 'done']),
        ])
        
        # Agrupar por mes
        monthly_data = defaultdict(lambda: {'count': 0, 'amount': 0.0})
        
        for order in orders:
            month_key = order.date_order.strftime('%Y-%m')
            monthly_data[month_key]['count'] += 1
            monthly_data[month_key]['amount'] += float(order.amount_total)
        
        # Ordenar por fecha
        sorted_months = sorted(monthly_data.keys())
        
        return {
            'labels': [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months],
            'datasets': [
                {
                    'label': 'Número de Pedidos',
                    'data': [monthly_data[m]['count'] for m in sorted_months],
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 2,
                },
                {
                    'label': 'Importe Total (€)',
                    'data': [monthly_data[m]['amount'] for m in sorted_months],
                    'backgroundColor': 'rgba(75, 192, 192, 0.5)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 2,
                }
            ]
        }
    
    def get_chart_data_top_products(self, limit=10):
        """
        Obtiene datos para gráfico de productos más vendidos.
        
        Args:
            limit: Número de productos a mostrar
        
        Returns:
            dict: Datos formateados para Chart.js
        """
        self.ensure_one()
        
        order_lines = self.env['sale.order.line'].search([
            ('order_id.partner_id', '=', self.partner_id.id),
            ('order_id.date_order', '>=', self.period_start),
            ('order_id.date_order', '<=', self.period_end),
            ('order_id.state', 'in', ['sale', 'done']),
        ])
        
        # Agrupar por producto
        product_data = {}
        for line in order_lines:
            if line.product_id:
                if line.product_id.id not in product_data:
                    product_data[line.product_id.id] = {
                        'name': line.product_id.name,
                        'qty': 0,
                        'amount': 0,
                    }
                product_data[line.product_id.id]['qty'] += line.product_uom_qty
                product_data[line.product_id.id]['amount'] += float(line.price_subtotal)
        
        # Ordenar por cantidad
        sorted_products = sorted(
            product_data.values(),
            key=lambda x: x['qty'],
            reverse=True
        )[:limit]
        
        return {
            'labels': [p['name'] for p in sorted_products],
            'datasets': [{
                'label': 'Cantidad Vendida',
                'data': [p['qty'] for p in sorted_products],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(75, 192, 192, 0.5)',
                    'rgba(153, 102, 255, 0.5)',
                    'rgba(255, 159, 64, 0.5)',
                    'rgba(199, 199, 199, 0.5)',
                    'rgba(83, 102, 255, 0.5)',
                    'rgba(255, 99, 255, 0.5)',
                    'rgba(99, 255, 132, 0.5)',
                ],
            }]
        }
    
    def get_kpi_summary(self):
        """
        Obtiene resumen de KPIs principales.
        
        Returns:
            dict: KPIs formateados
        """
        self.ensure_one()
        
        from datetime import timedelta
        
        # Calcular variación respecto al período anterior
        previous_period_days = (self.period_end - self.period_start).days
        previous_start = self.period_start - timedelta(days=previous_period_days)
        previous_end = self.period_start - timedelta(days=1)
        
        previous_orders = self.env['sale.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('date_order', '>=', previous_start),
            ('date_order', '<=', previous_end),
            ('state', 'in', ['sale', 'done']),
        ])
        
        previous_amount = sum(previous_orders.mapped('amount_total'))
        previous_count = len(previous_orders)
        
        # Calcular variaciones
        amount_variation = 0
        if previous_amount > 0:
            amount_variation = ((self.total_amount - previous_amount) / previous_amount) * 100
        
        count_variation = 0
        if previous_count > 0:
            count_variation = ((self.confirmed_orders - previous_count) / previous_count) * 100
        
        return {
            'total_orders': {
                'value': self.total_orders,
                'variation': count_variation,
                'label': 'Total Pedidos',
                'icon': 'fa-shopping-cart',
            },
            'total_amount': {
                'value': float(self.total_amount),
                'variation': amount_variation,
                'label': 'Facturación Total',
                'icon': 'fa-euro-sign',
            },
            'average_order': {
                'value': float(self.average_order_value),
                'variation': 0,
                'label': 'Ticket Medio',
                'icon': 'fa-chart-line',
            },
            'pending_payment': {
                'value': float(self.pending_payment),
                'variation': 0,
                'label': 'Pendiente de Pago',
                'icon': 'fa-clock',
            },
        }
