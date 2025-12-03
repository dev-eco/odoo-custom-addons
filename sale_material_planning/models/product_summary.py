# -*- coding: utf-8 -*-

from odoo import api, fields, models
from collections import defaultdict

class ProductSummary(models.Model):
    _name = 'sale.product.summary'
    _description = 'Resumen de Productos en Pedidos de Venta'
    _auto = False
    _order = 'product_id, qty desc'

    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_code = fields.Char(string='Referencia', readonly=True)
    product_name = fields.Char(string='Nombre del Producto', readonly=True)
    qty = fields.Float(string='Cantidad', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unidad de Medida', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    order_id = fields.Many2one('sale.order', string='Pedido', readonly=True)
    order_date = fields.Date(string='Fecha del Pedido', readonly=True)
    delivery_date = fields.Date(string='Fecha de Entrega', readonly=True)
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True)
    state = fields.Selection([
        ('draft', 'Presupuesto'),
        ('sent', 'Presupuesto Enviado'),
        ('sale', 'Pedido de Venta'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', readonly=True)
    picking_status = fields.Selection([
        ('not_created', 'No Creado'),
        ('waiting', 'Esperando'),
        ('partially_available', 'Parcialmente Disponible'),
        ('assigned', 'Reservado'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado Albarán', readonly=True)
    is_urgent = fields.Boolean(string='Urgente', readonly=True)
    order_status = fields.Selection([
        ('warehouse', 'Almacén'),
        ('manufacturing', 'Fabricación'),
        ('shipped', 'Salida')
    ], string='Estado de Pedido', readonly=True)
    days_to_delivery = fields.Integer(string='Días para Entrega', readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW sale_product_summary AS (
                SELECT
                    row_number() OVER () as id,
                    sol.product_id,
                    pp.default_code as product_code,
                    pt.name as product_name,
                    sol.product_uom_qty as qty,
                    sol.product_uom as uom_id,
                    so.partner_id,
                    so.id as order_id,
                    so.date_order::date as order_date,
                    so.commitment_date::date as delivery_date,
                    so.company_id,
                    so.state,
                    CASE
                        WHEN NOT EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id) THEN 'not_created'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'done') THEN 'done'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'cancel')
                             AND NOT EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state NOT IN ('cancel', 'done'))
THEN 'cancelled'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'assigned') THEN 'assigned'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'partially_available') THEN
'partially_available'
                        ELSE 'waiting'
                    END as picking_status,
                    so.is_urgent,
                    so.order_status,
                    CASE
                        WHEN so.commitment_date IS NULL THEN 999
                        ELSE (so.commitment_date::date - CURRENT_DATE)::integer
                    END as days_to_delivery
                FROM
                    sale_order_line sol
                JOIN
                    sale_order so ON sol.order_id = so.id
                JOIN
                    product_product pp ON sol.product_id = pp.id
                JOIN
                    product_template pt ON pp.product_tmpl_id = pt.id
                WHERE
                    pt.type = 'product'
                    AND so.state != 'cancel'
            )
        """)
# -*- coding: utf-8 -*-

from odoo import api, fields, models
from collections import defaultdict

class ProductSummary(models.Model):
    _name = 'sale.product.summary'
    _description = 'Resumen de Productos en Pedidos de Venta'
    _auto = False
    _order = 'product_id, qty desc'

    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_code = fields.Char(string='Referencia', readonly=True)
    product_name = fields.Char(string='Nombre del Producto', readonly=True)
    qty = fields.Float(string='Cantidad', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unidad de Medida', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    order_id = fields.Many2one('sale.order', string='Pedido', readonly=True)
    order_date = fields.Date(string='Fecha del Pedido', readonly=True)
    delivery_date = fields.Date(string='Fecha de Entrega', readonly=True)
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True)
    state = fields.Selection([
        ('draft', 'Presupuesto'),
        ('sent', 'Presupuesto Enviado'),
        ('sale', 'Pedido de Venta'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', readonly=True)
    picking_status = fields.Selection([
        ('not_created', 'No Creado'),
        ('waiting', 'Esperando'),
        ('partially_available', 'Parcialmente Disponible'),
        ('assigned', 'Reservado'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado Albarán', readonly=True)
    is_urgent = fields.Boolean(string='Urgente', readonly=True)
    order_status = fields.Selection([
        ('new', 'Nuevo'),
        ('warehouse', 'Almacén'),
        ('manufacturing', 'Fabricación'),
        ('prepared', 'Preparado'),
        ('shipped', 'Salida')
    ], string='Estado de Pedido', readonly=True)
    days_to_delivery = fields.Integer(string='Días para Entrega', readonly=True)

    def init(self):
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW sale_product_summary AS (
                SELECT
                    row_number() OVER () as id,
                    sol.product_id,
                    pp.default_code as product_code,
                    pt.name as product_name,
                    sol.product_uom_qty as qty,
                    sol.product_uom as uom_id,
                    so.partner_id,
                    so.id as order_id,
                    so.date_order::date as order_date,
                    so.commitment_date::date as delivery_date,
                    so.company_id,
                    so.state,
                    CASE
                        WHEN NOT EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id) THEN 'not_created'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'done') THEN 'done'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'cancel')
                             AND NOT EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state NOT IN ('cancel', 'done'))
THEN 'cancelled'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'assigned') THEN 'assigned'
                        WHEN EXISTS (SELECT 1 FROM stock_picking sp WHERE sp.sale_id = so.id AND sp.state = 'partially_available') THEN
'partially_available'
                        ELSE 'waiting'
                    END as picking_status,
                    so.is_urgent,
                    so.order_status,
                    CASE
                        WHEN so.commitment_date IS NULL THEN 999
                        ELSE (so.commitment_date::date - CURRENT_DATE)::integer
                    END as days_to_delivery
                FROM
                    sale_order_line sol
                JOIN
                    sale_order so ON sol.order_id = so.id
                JOIN
                    product_product pp ON sol.product_id = pp.id
                JOIN
                    product_template pt ON pp.product_tmpl_id = pt.id
                WHERE
                    pt.type = 'product'
                    AND so.state != 'cancel'
            )
        """)
