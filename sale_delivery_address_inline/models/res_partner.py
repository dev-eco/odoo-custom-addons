# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo principal para identificar distribuidores
    is_distributor = fields.Boolean(
        string='Is Distributor',
        default=False,
        help='Check this box if this partner is a distributor who may have multiple delivery addresses'
    )
    
    # Contador de direcciones de entrega
    delivery_address_count = fields.Integer(
        string='Delivery Address Count',
        compute='_compute_delivery_address_count'
    )

    @api.depends('child_ids')
    def _compute_delivery_address_count(self):
        """Compute the number of delivery addresses for each partner"""
        for partner in self:
            delivery_addresses = partner.child_ids.filtered(lambda c: c.type == 'delivery')
            partner.delivery_address_count = len(delivery_addresses)

    @api.constrains('is_distributor', 'parent_id')
    def _check_distributor_consistency(self):
        """Ensure distributors are not child contacts themselves"""
        for partner in self:
            if partner.is_distributor and partner.parent_id:
                raise ValidationError(
                    _('A contact cannot be marked as distributor if it has a parent company')
                )

    def get_delivery_addresses_for_selection(self):
        """Get delivery addresses formatted for selection widget"""
        self.ensure_one()
        addresses = []
        
        if self.is_distributor:
            # Incluir la dirección principal si tiene dirección completa
            if self.street:
                addresses.append((self.id, f"[Principal] {self.contact_address}"))
            
            # Incluir todas las direcciones de entrega
            for delivery in self.child_ids.filtered(lambda c: c.type == 'delivery'):
                addresses.append((delivery.id, f"[Delivery] {delivery.contact_address}"))
        else:
            # Para clientes normales, solo la dirección principal
            if self.street:
                addresses.append((self.id, self.contact_address))
        
        return addresses
