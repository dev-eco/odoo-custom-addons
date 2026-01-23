# -*- coding: utf-8 -*-

from odoo import fields, models

class SaleReport(models.Model):
    _inherit = 'sale.report'

    order_status = fields.Selection([
        ('new', 'Nuevo'),
        ('warehouse', 'Almacén'),
        ('manufacturing', 'Fabricación'),
        ('prepared', 'Preparado'),
        ('shipped', 'Salida')
    ], string='Estado de Pedido', readonly=True)
    
    is_urgent = fields.Boolean(string='Urgente', readonly=True)
    
    picking_status = fields.Selection([
        ('not_created', 'No Creado'),
        ('waiting', 'Esperando'),
        ('partially_available', 'Parcialmente Disponible'),
        ('assigned', 'Reservado'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado Albarán', readonly=True)

    def _select_sale(self):
        select_str = super()._select_sale()
        select_str += """
            , s.order_status as order_status
            , s.is_urgent as is_urgent
            , CASE
                WHEN NOT EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = s.id) THEN 'not_created'
                WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = s.id AND sp.state = 'done') THEN 'done'
                WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = s.id AND sp.state = 'cancel')
                     AND NOT EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = s.id AND sp.state NOT IN ('cancel', 'done')) THEN 'cancelled'
                WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = s.id AND sp.state = 'assigned') THEN 'assigned'
                WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = s.id AND sp.state = 'partially_available') THEN 'partially_available'
                ELSE 'waiting'
            END as picking_status
        """
        return select_str

    def _group_by_sale(self):
        group_by_str = super()._group_by_sale()
        group_by_str += """
            , s.order_status
            , s.is_urgent
        """
        return group_by_str
