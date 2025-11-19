# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    use_alternative_delivery = fields.Boolean(
        string="Usar dirección alternativa",
        help="Permite seleccionar una dirección de entrega no vinculada al cliente facturado"
    )
    alternative_delivery_partner_id = fields.Many2one(
        'res.partner',
        string="Dirección de entrega alternativa",
        domain="['|', '|', '|', ('id', 'child_of', partner_id), ('is_public_delivery_address', '=', True), ('alternative_delivery_for_partner_ids', 'in', partner_id), ('type', '=', 'delivery')]",
        help="Dirección donde se entregará el pedido (puede no pertenecer al cliente)"
    )
    effective_delivery_partner_id = fields.Many2one(
        'res.partner',
        string="Dirección de entrega efectiva",
        compute='_compute_effective_delivery_partner',
        store=True,
        help="Dirección que se usará para la entrega (alternativa o estándar)"
    )

    @api.depends('partner_shipping_id', 'use_alternative_delivery', 'alternative_delivery_partner_id')
    def _compute_effective_delivery_partner(self):
        for order in self:
            if order.use_alternative_delivery and order.alternative_delivery_partner_id:
                order.effective_delivery_partner_id = order.alternative_delivery_partner_id
            else:
                order.effective_delivery_partner_id = order.partner_shipping_id
                
    @api.onchange('partner_id', 'use_alternative_delivery')
    def _onchange_use_alternative_delivery(self):
        """Depurar y mostrar direcciones disponibles"""
        if self.use_alternative_delivery and self.partner_id:
            # Buscar direcciones públicas para verificar que existen
            public_addresses = self.env['res.partner'].search([
                ('is_public_delivery_address', '=', True)
            ])
            if not public_addresses:
                # Mostrar advertencia si no hay direcciones públicas
                return {
                    'warning': {
                        'title': _('Sin direcciones públicas'),
                        'message': _('No se encontraron direcciones públicas configuradas en el sistema.')
                    }
                }

    def _prepare_picking_values(self, **kwargs):
        """Sobrescribe el método para usar la dirección alternativa en el albarán"""
        values = super()._prepare_picking_values(**kwargs)

        # Usar dirección alternativa si está configurada
        if self.use_alternative_delivery and self.alternative_delivery_partner_id:
            values['partner_id'] = self.alternative_delivery_partner_id.id
            # Guardar también el partner original para referencia
            values['original_partner_id'] = self.partner_id.id
            values['is_alternative_delivery'] = True

        return values

    def action_save_as_usual_address(self):
        """Guardar dirección alternativa como habitual para este cliente"""
        self.ensure_one()
        if not self.use_alternative_delivery or not self.alternative_delivery_partner_id:
            raise UserError(_("No hay dirección alternativa configurada"))

        self.partner_id.write({
            'alternative_delivery_for_partner_ids': [
                (4, self.alternative_delivery_partner_id.id)
            ]
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Dirección guardada"),
                'message': _("La dirección ha sido guardada como alternativa habitual"),
                'sticky': False,
            }
        }

    def action_create_alternative_address(self):
        """Abrir wizard para crear una nueva dirección alternativa"""
        self.ensure_one()
        return {
            'name': _('Crear Dirección de Entrega Alternativa'),
            'type': 'ir.actions.act_window',
            'res_model': 'create.alternative.delivery.address.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
            }
        }
