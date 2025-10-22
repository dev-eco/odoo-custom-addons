# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo principal para identificar distribuidores (SOLO LOS BÁSICOS)
    is_distributor = fields.Boolean(
        string='Es Distribuidor',
        default=False,
        help='Marque esta casilla si este cliente es un distribuidor con múltiples direcciones de entrega'
    )
    
    # Contador de direcciones de entrega
    delivery_address_count = fields.Integer(
        string='Número de Direcciones de Entrega',
        compute='_compute_delivery_address_count',
        help='Número total de direcciones de entrega asociadas'
    )
    
    # Direcciones de entrega relacionadas
    delivery_address_ids = fields.One2many(
        'res.partner',
        'parent_id',
        domain=[('type', '=', 'delivery')],
        string='Direcciones de Entrega',
        help='Direcciones de entrega asociadas a este distribuidor'
    )

    @api.depends('child_ids')
    def _compute_delivery_address_count(self):
        """Calcular el número de direcciones de entrega para cada partner"""
        for partner in self:
            delivery_addresses = partner.child_ids.filtered(lambda c: c.type == 'delivery')
            partner.delivery_address_count = len(delivery_addresses)

    @api.constrains('is_distributor', 'parent_id')
    def _check_distributor_consistency(self):
        """Asegurar que los distribuidores no sean contactos hijo"""
        for partner in self:
            if partner.is_distributor and partner.parent_id:
                raise ValidationError(
                    _('Un contacto no puede marcarse como distribuidor si tiene una empresa padre')
                )

    def get_delivery_addresses_for_selection(self):
        """Obtener direcciones de entrega formateadas para widget de selección"""
        self.ensure_one()
        addresses = []
        
        if self.is_distributor:
            # Incluir la dirección principal si tiene dirección completa
            if self.street:
                addresses.append((self.id, f"[Principal] {self.contact_address}"))
            
            # Incluir todas las direcciones de entrega
            for delivery in self.delivery_address_ids:
                province = f" ({delivery.state_id.name})" if delivery.state_id else ""
                addresses.append((delivery.id, f"[Entrega] {delivery.name} - {delivery.city}{province}"))
        else:
            # Para clientes normales, solo la dirección principal
            if self.street:
                addresses.append((self.id, self.contact_address))
        
        return addresses

    def action_view_delivery_addresses(self):
        """Acción para ver todas las direcciones de entrega de este partner"""
        self.ensure_one()
        action = self.env.ref('contacts.action_contacts').read()[0]
        action['domain'] = [('parent_id', '=', self.id), ('type', '=', 'delivery')]
        action['context'] = {
            'default_parent_id': self.id,
            'default_type': 'delivery',
            'default_is_company': False,
            'default_country_id': self.env.ref('base.es').id,  # España por defecto
        }
        action['name'] = _('Direcciones de Entrega para %s') % self.display_name
        return action

    @api.model
    def create_delivery_address_es(self, partner_id, address_data):
        """
        Crear una nueva dirección de entrega para un partner (versión española)
        
        Args:
            partner_id (int): ID del partner padre
            address_data (dict): Diccionario con información de la dirección
            
        Returns:
            res.partner: Dirección de entrega creada
        """
        parent_partner = self.browse(partner_id)
        
        if not parent_partner.exists():
            raise ValidationError(_('Partner padre no encontrado'))
        
        # Preparar datos para la nueva dirección con valores por defecto españoles
        delivery_data = {
            'name': address_data.get('name', f"{parent_partner.name} - Entrega"),
            'parent_id': partner_id,
            'type': 'delivery',
            'street': address_data.get('street', ''),
            'street2': address_data.get('street2', ''),
            'city': address_data.get('city', ''),
            'state_id': address_data.get('state_id', False),
            'zip': address_data.get('zip', ''),
            'country_id': address_data.get('country_id', self.env.ref('base.es').id),  # España por defecto
            'phone': address_data.get('phone', ''),
            'email': address_data.get('email', ''),
            'company_id': parent_partner.company_id.id,
            'is_company': False,
        }
        
        # Crear la nueva dirección
        new_address = self.create(delivery_data)
        
        return new_address

    def _get_contact_address_formatted(self):
        """Obtener dirección formateada para España"""
        self.ensure_one()
        
        address_parts = []
        
        if self.street:
            address_parts.append(self.street)
        
        if self.street2:
            address_parts.append(self.street2)
        
        # Formato español: CP Ciudad, Provincia
        city_line = []
        if self.zip:
            city_line.append(self.zip)
        if self.city:
            city_line.append(self.city)
        
        if city_line:
            address_parts.append(" ".join(city_line))
        
        if self.state_id:
            address_parts.append(self.state_id.name)
        
        if self.country_id and self.country_id.code != 'ES':
            address_parts.append(self.country_id.name)
        
        return "\n".join(address_parts)
