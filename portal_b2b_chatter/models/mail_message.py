# -*- coding: utf-8 -*-
from odoo import models, api, SUPERUSER_ID


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        """
        Override _search para permitir que usuarios portal vean mensajes
        de sus propios pedidos de venta.
        """
        # Si el usuario es portal, añadir filtro para sus pedidos
        if self.env.user.has_group('base.group_portal') and not self.env.su:
            partner = self.env.user.partner_id
            # Buscar pedidos del partner (incluyendo partner comercial)
            sale_orders = self.env['sale.order'].search([
                ('partner_id', 'child_of', partner.commercial_partner_id.id)
            ])

            # Añadir condición al dominio: solo mensajes de sale.order que pertenecen al usuario
            portal_domain = [
                '|',
                    # Mantener el dominio original para otros modelos que ya tienen acceso
                    ('model', '!=', 'sale.order'),
                    # O mensajes de sale.order que son del usuario
                    '&',
                        ('model', '=', 'sale.order'),
                        ('res_id', 'in', sale_orders.ids)
            ]
            domain = ['&'] + portal_domain + domain

        return super()._search(
            domain, offset=offset, limit=limit, order=order,
            access_rights_uid=access_rights_uid
        )
