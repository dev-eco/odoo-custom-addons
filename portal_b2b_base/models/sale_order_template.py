# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderTemplate(models.Model):
    """Plantillas de pedidos para distribuidores."""

    _name = 'sale.order.template'
    _description = 'Plantilla de Pedido'
    _order = 'name asc'

    name = fields.Char(
        string='Nombre de la Plantilla',
        required=True,
        help='Nombre descriptivo de la plantilla'
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        required=True,
        ondelete='cascade',
        help='Distribuidor propietario de la plantilla'
    )

    line_ids = fields.One2many(
        'sale.order.template.line',
        'template_id',
        string='Líneas de Productos',
        copy=True,
        help='Productos incluidos en la plantilla'
    )

    delivery_address_id = fields.Many2one(
        'delivery.address',
        string='Dirección de Entrega Predeterminada',
        help='Dirección de entrega que se usará por defecto'
    )

    distributor_label_id = fields.Many2one(
        'distributor.label',
        string='Cliente Final Predeterminado',
        help='Cliente final que se usará por defecto'
    )

    notes = fields.Text(
        string='Notas',
        help='Notas adicionales para la plantilla'
    )

    active = fields.Boolean(
        string='Activa',
        default=True,
        help='Marcar como inactiva para archivar la plantilla'
    )

    use_count = fields.Integer(
        string='Veces Usada',
        default=0,
        readonly=True,
        help='Número de veces que se ha usado esta plantilla'
    )

    last_used_date = fields.Date(
        string='Último Uso',
        readonly=True,
        help='Fecha del último uso de la plantilla'
    )

    estimated_total = fields.Monetary(
        string='Total Estimado',
        currency_field='currency_id',
        compute='_compute_estimated_total',
        store=False,
        help='Total estimado basado en precios actuales'
    )

    total_products = fields.Integer(
        string='Total de Productos',
        compute='_compute_total_products',
        store=False,
        help='Número de productos en la plantilla'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        help='Moneda de la plantilla'
    )

    @api.depends('line_ids', 'line_ids.quantity', 'line_ids.product_id')
    def _compute_estimated_total(self) -> None:
        """Calcula el total estimado de la plantilla."""
        for template in self:
            total = 0.0
            pricelist = template.partner_id.obtener_tarifa_aplicable()

            for line in template.line_ids:
                if line.product_id:
                    price = pricelist._get_product_price(
                        line.product_id.product_variant_id,
                        line.quantity,
                        partner=template.partner_id
                    ) if pricelist else line.product_id.list_price

                    total += price * line.quantity

            template.estimated_total = total

    @api.depends('line_ids')
    def _compute_total_products(self) -> None:
        """Cuenta el número de productos en la plantilla."""
        for template in self:
            template.total_products = len(template.line_ids)

    def action_use_template(self):
        """
        Acción para usar la plantilla y crear un nuevo pedido.

        Returns:
            dict: Acción de redirección al formulario de crear pedido
        """
        self.ensure_one()

        # Actualizar contador de uso
        self.write({
            'use_count': self.use_count + 1,
            'last_used_date': fields.Date.today(),
        })

        _logger.info(f"Plantilla {self.name} usada por {self.env.user.name}")

        # Redirigir a crear pedido con parámetros de la plantilla
        return {
            'type': 'ir.actions.act_window',
            'name': _('Crear Pedido desde Plantilla'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_template_id': self.id,
                'template_lines': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                }) for line in self.line_ids],
            },
        }

    def action_create_order_from_template(self):
        """
        Crea un pedido de venta basado en la plantilla.

        Returns:
            dict: Acción de redirección al nuevo pedido
        """
        self.ensure_one()

        # Crear líneas del pedido
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
            }))

        # Crear pedido
        order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': order_lines,
            'note': self.notes or '',
            'delivery_address_id': self.delivery_address_id.id if self.delivery_address_id else None,
            'distributor_label_id': self.distributor_label_id.id if self.distributor_label_id else None,
        })

        # Actualizar uso
        self.write({
            'use_count': self.use_count + 1,
            'last_used_date': fields.Date.today(),
        })

        _logger.info(f"Pedido {order.name} creado desde plantilla {self.name}")

        return {
            'type': 'ir.actions.act_window',
            'name': order.name,
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }


class SaleOrderTemplateLine(models.Model):
    """Líneas de productos en plantillas de pedidos."""

    _name = 'sale.order.template.line'
    _description = 'Línea de Plantilla de Pedido'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'sale.order.template',
        string='Plantilla',
        required=True,
        ondelete='cascade',
        help='Plantilla a la que pertenece esta línea'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='restrict',
        domain=[('sale_ok', '=', True)],
        help='Producto a incluir en la plantilla'
    )

    quantity = fields.Float(
        string='Cantidad',
        default=1.0,
        required=True,
        help='Cantidad del producto'
    )

    notes = fields.Char(
        string='Notas',
        help='Notas específicas para esta línea'
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de visualización'
    )

    @api.constrains('quantity')
    def _check_quantity(self) -> None:
        """Valida que la cantidad sea positiva."""
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    _('La cantidad debe ser mayor a 0.')
                )
