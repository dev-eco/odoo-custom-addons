# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class CreateAlternativeDeliveryAddress(models.TransientModel):
    _name = 'create.alternative.delivery.address.wizard'
    _description = 'Crear dirección de entrega alternativa'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    name = fields.Char('Nombre/Referencia', required=True)
    street = fields.Char('Calle')
    street2 = fields.Char('Calle 2')
    zip = fields.Char('C.P.')
    city = fields.Char('Ciudad')
    state_id = fields.Many2one('res.country.state', 'Provincia')
    country_id = fields.Many2one('res.country', 'País')
    contact_name = fields.Char('Persona de contacto')
    phone = fields.Char('Teléfono')
    email = fields.Char('Email')
    is_public = fields.Boolean('Dirección pública', default=False)
    notes = fields.Text('Notas para entrega')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.country_id = self.partner_id.country_id

    def action_create_address(self):
        """Crear nueva dirección y asignarla al pedido"""
        self.ensure_one()

        # Crear la dirección como contacto hijo del partner
        partner_vals = {
            'name': self.name,
            'type': 'delivery',
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'state_id': self.state_id.id if self.state_id else False,
            'country_id': self.country_id.id if self.country_id else False,
            'phone': self.phone,
            'email': self.email,
            'comment': self.notes,
            'is_public_delivery_address': self.is_public,
        }

        # Si es dirección pública, no la vinculamos a ningún partner específico
        if not self.is_public:
            partner_vals['parent_id'] = self.partner_id.id
        
        # Asegurarse de que el tipo sea 'delivery' para direcciones de entrega
        partner_vals['type'] = 'delivery'

        new_partner = self.env['res.partner'].create(partner_vals)

        # Si viene de un pedido, asignar automáticamente
        active_model = self._context.get('active_model')
        active_id = self._context.get('active_id')

        if active_model == 'sale.order' and active_id:
            order = self.env['sale.order'].browse(active_id)
            order.write({
                'use_alternative_delivery': True,
                'alternative_delivery_partner_id': new_partner.id
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Dirección creada"),
                'message': _("La dirección alternativa ha sido creada y asignada al pedido"),
                'sticky': False,
            }
        }
