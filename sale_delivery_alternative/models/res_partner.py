# -*- coding: utf-8 -*-

from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_public_delivery_address = fields.Boolean(
        string="Dirección de entrega pública",
        help="Si está marcado, esta dirección puede ser seleccionada por cualquier cliente como dirección de entrega"
    )
    alternative_delivery_for_partner_ids = fields.Many2many(
        'res.partner',
        'partner_alternative_delivery_rel',
        'address_id',
        'partner_id',
        string="Dirección alternativa para clientes",
        help="Clientes que usan esta dirección como alternativa habitual"
    )

    def name_get(self):
        """Sobrescribe name_get para mostrar si es dirección pública"""
        result = super(ResPartner, self).name_get()
        new_result = []

        for partner_id, name in result:
            partner = self.browse(partner_id)
            if partner.is_public_delivery_address:
                name = f"{name} (Pública)"
            new_result.append((partner_id, name))

        return new_result
