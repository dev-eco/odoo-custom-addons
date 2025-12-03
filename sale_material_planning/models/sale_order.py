from odoo import api, fields, models
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo calculado para mostrar resumen de productos
    product_summary = fields.Text(
        string='Resumen de Productos',
        compute='_compute_product_summary',
        store=False,
        help='Resumen de referencias y cantidades de productos'
    )
    
    # Campo para facilitar la agrupación por fecha de entrega
    delivery_date = fields.Date(
        string='Fecha de Entrega',
        compute='_compute_delivery_date',
        store=True,
        help='Fecha estimada de entrega para agrupar'
    )
    
    # Campo para contar total de unidades
    total_product_qty = fields.Float(
        string='Total Unidades',
        compute='_compute_total_qty',
        store=True,
        help='Total de unidades en el pedido'
    )
    
    # Campo para mostrar el estado del albarán
    picking_status = fields.Selection([
        ('not_created', 'No Creado'),
        ('waiting', 'Esperando'),
        ('partially_available', 'Parcialmente Disponible'),
        ('assigned', 'Reservado'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado Albarán', compute='_compute_picking_status', store=True)
    
    # Campo para indicar si el pedido es urgente
    is_urgent = fields.Boolean(
        string='Urgente',
        help='Marcar si el pedido es urgente'
    )
    
    # Días restantes hasta la entrega
    days_to_delivery = fields.Integer(
        string='Días para Entrega',
        compute='_compute_days_to_delivery',
        store=True,
        help='Días restantes hasta la fecha de entrega'
    )
    
    # Color para la vista kanban
    color = fields.Integer(string='Color', compute='_compute_color', store=True)
    
    # Campo para marcar el estado del pedido
    order_status = fields.Selection([
<<<<<<< HEAD
        ('none', 'Sin estado'),
=======
        ('new', 'Nuevo'),  # Nuevo estado por defecto
>>>>>>> development
        ('warehouse', 'Almacén'),
        ('manufacturing', 'Fabricación'),
        ('prepared', 'Preparado'),
        ('shipped', 'Salida')
<<<<<<< HEAD
    ], string='Estado de Pedido', default='none', tracking=True,
       help='Estado actual del pedido: sin estado, en almacén, en fabricación, preparado o ya salido')
=======
    ], string='Estado de Pedido', default='new', tracking=True,
       help='Estado actual del pedido: nuevo, en almacén, en fabricación, preparado o ya salido')
>>>>>>> development
    
    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_product_summary(self):
        for order in self:
            # Líneas de detalle individuales
            detail_lines = []
            
            # Diccionario para acumular cantidades por producto
            product_totals = {}
            
            # Procesar cada línea de pedido
            for line in order.order_line:
                product = line.product_id
                
                # Excluir productos de tipo servicio
                if product.type == 'service':
                    continue
                
                # Añadir línea individual
                detail_lines.append(f"{product.default_code or ''} - {product.name}: {line.product_uom_qty} {product.uom_id.name}")
                
                # Acumular para el sumatorio
                if product in product_totals:
                    product_totals[product] += line.product_uom_qty
                else:
                    product_totals[product] = line.product_uom_qty
            
            # Añadir línea en blanco como separador si hay productos
            if detail_lines and product_totals:
                detail_lines.append("")
                detail_lines.append("RESUMEN TOTAL POR PRODUCTO:")
                
                # Añadir sumatorio por producto
                for product, qty in product_totals.items():
                    detail_lines.append(f"TOTAL {product.default_code or ''} - {product.name}: {qty} {product.uom_id.name}")
            
            # Asignar el resumen completo
            order.product_summary = "\n".join(detail_lines)
    
    @api.depends('commitment_date', 'expected_date')
    def _compute_delivery_date(self):
        for order in self:
            # Usamos la fecha de compromiso si está disponible, de lo contrario la fecha esperada
            order.delivery_date = order.commitment_date or order.expected_date or False
    
    @api.depends('order_line.product_uom_qty', 'order_line.product_id')
    def _compute_total_qty(self):
        for order in self:
            # Filtrar líneas excluyendo productos de tipo servicio
            product_lines = order.order_line.filtered(lambda l: l.product_id.type != 'service')
            order.total_product_qty = sum(product_lines.mapped('product_uom_qty'))
    
    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_picking_status(self):
        for order in self:
            if not order.picking_ids:
                order.picking_status = 'not_created'
            else:
                # Obtener el estado más avanzado de los albaranes
                states = order.picking_ids.mapped('state')
                if 'done' in states:
                    order.picking_status = 'done'
                elif 'cancel' in states and all(state in ['cancel', 'done'] for state in states):
                    order.picking_status = 'cancelled'
                elif 'assigned' in states:
                    order.picking_status = 'assigned'
                elif 'partially_available' in states:
                    order.picking_status = 'partially_available'
                else:
                    order.picking_status = 'waiting'
    
    @api.depends('delivery_date')
    def _compute_days_to_delivery(self):
        today = fields.Date.today()
        for order in self:
            if order.delivery_date:
                delta = order.delivery_date - today
                order.days_to_delivery = delta.days
            else:
                order.days_to_delivery = 999  # Valor alto para pedidos sin fecha
    
    @api.depends('is_urgent', 'days_to_delivery', 'picking_status', 'order_status')
    def _compute_color(self):
        for order in self:
            if order.order_status == 'shipped':
                order.color = 10  # Verde (prioridad máxima)
            elif order.order_status == 'manufacturing':
                order.color = 4  # Azul claro
            elif order.order_status == 'new':
                order.color = 6  # Gris claro para nuevos
            elif order.is_urgent:
                order.color = 1  # Rojo
            elif order.picking_status == 'done':
                order.color = 5  # Verde claro
            elif order.days_to_delivery <= 0 and order.picking_status != 'done':
                order.color = 2  # Naranja
            elif order.days_to_delivery <= 3 and order.picking_status != 'done':
                order.color = 3  # Amarillo
            else:
                order.color = 0  # Blanco/Sin color
                
    def action_mark_as_shipped(self):
        """Marcar el pedido como salida"""
        for order in self:
            order.write({'order_status': 'shipped'})
        return True
    
    def action_mark_as_warehouse(self):
        """Marcar el pedido como en almacén"""
        for order in self:
            order.write({'order_status': 'warehouse'})
        return True
    
    def action_mark_as_manufacturing(self):
        """Marcar el pedido como en fabricación"""
        for order in self:
            order.write({'order_status': 'manufacturing'})
        return True
        
    def action_mark_as_prepared(self):
        """Marcar el pedido como preparado para salida"""
        for order in self:
            order.write({'order_status': 'prepared'})
        return True
        
    def action_mark_as_new(self):
        """Marcar el pedido como nuevo"""
        for order in self:
            order.write({'order_status': 'new'})
        return True
