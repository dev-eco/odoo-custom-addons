# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Solo el campo más básico
    is_distributor = fields.Boolean(
        string='Es Distribuidor',
        default=False,
        help='Cliente con múltiples direcciones de entrega'
    )
    
    # Contador simple
    delivery_address_count = fields.Integer(
        string='Direcciones de Entrega',
        compute='_compute_delivery_address_count'
    )

    @api.depends('child_ids')
    def _compute_delivery_address_count(self):
        for partner in self:
            delivery_addresses = partner.child_ids.filtered(lambda c: c.type == 'delivery')
            partner.delivery_address_count = len(delivery_addresses)

    def action_view_delivery_addresses(self):
        """Ver direcciones de entrega"""
        self.ensure_one()
        return {
            'name': 'Direcciones de Entrega',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('parent_id', '=', self.id), ('type', '=', 'delivery')],
            'context': {
                'default_parent_id': self.id,
                'default_type': 'delivery',
                'default_is_company': False,
            }
        }
