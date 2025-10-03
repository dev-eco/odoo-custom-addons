# -*- coding: utf-8 -*-
# © 2025 ECOCAUCHO - https://ecocaucho.org
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    # Campos personalizados para la factura
    referencia_cliente = fields.Char(
        string="Referencia Cliente", 
        index=True,
        help="Referencia o número proporcionado por el cliente para esta factura"
    )
    
    instrucciones_especiales = fields.Text(
        string="Instrucciones Especiales",
        help="Notas o instrucciones especiales para esta factura que aparecerán en la versión impresa"
    )
    
    contacto_facturacion = fields.Many2one(
        'res.partner',
        string="Contacto de Facturación",
        domain="[('parent_id', '=', partner_id), ('type', '=', 'invoice')]",
        help="Contacto específico para facturación dentro de la empresa cliente"
    )
    
    # Campo calculado para mostrar pedidos relacionados
    pedidos_relacionados = fields.Char(
        string="Pedidos Relacionados",
        compute='_compute_pedidos_relacionados',
        store=True,
        help="Muestra los números de pedido relacionados con esta factura"
    )
    
    def action_invoice_print(self):
        """Reemplaza la acción de imprimir factura para usar nuestra plantilla personalizada"""
        self.ensure_one()
        self.filtered(lambda inv: not inv.is_move_sent).write({'is_move_sent': True})
        return self.env.ref('plantilla_factura.action_report_factura_personalizada').report_action(self)
    
    def _get_invoice_lines_by_order(self):
        """Agrupa las líneas de factura por pedido de venta"""
        self.ensure_one()
        result = {}
        
        # Primero, obtener todos los pedidos únicos relacionados con esta factura
        orders = self.env['sale.order']
        for line in self.invoice_line_ids:
            for sale_line in line.sale_line_ids:
                if sale_line.order_id not in orders:
                    orders |= sale_line.order_id
        
        # Crear diccionario agrupando líneas por pedido
        for order in orders:
            result[order] = self.invoice_line_ids.filtered(
                lambda l: any(sl.order_id == order for sl in l.sale_line_ids)
            )
        
        # Líneas sin pedido relacionado
        no_order_lines = self.invoice_line_ids.filtered(
            lambda l: not l.sale_line_ids and l.display_type not in ('line_section', 'line_note')
        )
        if no_order_lines:
            result['no_order'] = no_order_lines
        
        return result

    @api.depends('invoice_origin', 'invoice_line_ids.sale_line_ids.order_id')
    def _compute_pedidos_relacionados(self):
        """Calcula y formatea los pedidos relacionados con esta factura"""
        for move in self:
            order_ids = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            
            if order_ids:
                # Crear una lista formateada de referencias de pedidos
                order_refs = order_ids.mapped('name')
                # Eliminamos duplicados
                unique_refs = list(set(order_refs))
                move.pedidos_relacionados = ', '.join(unique_refs)
            else:
                # Usar el campo original si no hay pedidos identificados
                move.pedidos_relacionados = move.invoice_origin or ''
    
    def _get_report_base_filename(self):
        """Define el nombre base del archivo del informe"""
        self.ensure_one()
        if self.is_sale_document():
            return 'Factura - %s' % (self.name)
        elif self.is_purchase_document():
            return 'Factura Proveedor - %s' % (self.name)
        else:
            return 'Asiento - %s' % (self.name)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    # Campo calculado para mostrar el pedido relacionado
    sale_order_reference = fields.Char(
        string="Pedido",
        compute='_compute_sale_order_reference',
        help="Número de pedido relacionado con esta línea"
    )
    
    @api.depends('sale_line_ids')
    def _compute_sale_order_reference(self):
        """Obtiene la referencia del pedido asociado a esta línea de factura"""
        for line in self:
            if line.sale_line_ids:
                orders = line.sale_line_ids.mapped('order_id')
                line.sale_order_reference = ', '.join(orders.mapped('name'))
            else:
                line.sale_order_reference = ''
