# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo para identificar distribuidores
    is_distributor = fields.Boolean(
        string='Is Distributor',
        default=False,
        help='Check this box if this partner is a distributor who may have multiple delivery addresses'
    )
    
    # Contactos de entrega relacionados (para distribuidores)
    delivery_address_ids = fields.One2many(
        'res.partner',
        'parent_id',
        domain=[('type', '=', 'delivery')],
        string='Delivery Addresses',
        help='Delivery addresses associated with this distributor'
    )
    
    # Contador de direcciones de entrega
    delivery_address_count = fields.Integer(
        string='Delivery Address Count',
        compute='_compute_delivery_address_count',
        store=False
    )

    @api.depends('delivery_address_ids')
    def _compute_delivery_address_count(self):
        """Compute the number of delivery addresses for each partner"""
        for partner in self:
            partner.delivery_address_count = len(partner.delivery_address_ids)

    @api.model
    def create_delivery_address(self, partner_id, address_data):
        """
        Create a new delivery address for a partner
        
        Args:
            partner_id (int): ID of the parent partner
            address_data (dict): Dictionary containing address information
            
        Returns:
            res.partner: Created delivery address partner
        """
        parent_partner = self.browse(partner_id)
        
        if not parent_partner.exists():
            raise ValidationError(_('Parent partner not found'))
            
        # Preparar datos para la nueva dirección
        delivery_data = {
            'name': address_data.get('name', f"{parent_partner.name} - Delivery"),
            'parent_id': partner_id,
            'type': 'delivery',
            'street': address_data.get('street', ''),
            'street2': address_data.get('street2', ''),
            'city': address_data.get('city', ''),
            'state_id': address_data.get('state_id', False),
            'zip': address_data.get('zip', ''),
            'country_id': address_data.get('country_id', parent_partner.country_id.id),
            'phone': address_data.get('phone', ''),
            'email': address_data.get('email', ''),
            'company_id': parent_partner.company_id.id,
            'is_company': False,
        }
        
        # Crear la nueva dirección
        new_address = self.create(delivery_data)
        
        return new_address

    def action_view_delivery_addresses(self):
        """Action to view all delivery addresses for this partner"""
        self.ensure_one()
        action = self.env.ref('contacts.action_contacts').read()[0]
        action['domain'] = [('parent_id', '=', self.id), ('type', '=', 'delivery')]
        action['context'] = {
            'default_parent_id': self.id,
            'default_type': 'delivery',
            'default_is_company': False,
        }
        action['name'] = _('Delivery Addresses for %s') % self.display_name
        return action

    @api.constrains('is_distributor', 'parent_id')
    def _check_distributor_consistency(self):
        """Ensure distributors are not child contacts themselves"""
        for partner in self:
            if partner.is_distributor and partner.parent_id:
                raise ValidationError(
                    _('A contact cannot be marked as distributor if it has a parent company')
                )

    def get_delivery_addresses_for_selection(self):
        """
        Get delivery addresses formatted for selection widget
        
        Returns:
            list: List of tuples (id, display_name) for selection
        """
        self.ensure_one()
        addresses = []
        
        if self.is_distributor:
            # Incluir la dirección principal si tiene dirección completa
            if self.street:
                addresses.append((self.id, f"[Principal] {self.contact_address}"))
            
            # Incluir todas las direcciones de entrega
            for delivery in self.delivery_address_ids:
                addresses.append((delivery.id, f"[Delivery] {delivery.contact_address}"))
        else:
            # Para clientes normales, solo la dirección principal
            if self.street:
                addresses.append((self.id, self.contact_address))
        
        return addresses

    @api.model
    def get_or_create_delivery_contact(self, partner_id, delivery_data):
        """
        Get existing or create new delivery contact based on address similarity
        
        Args:
            partner_id (int): Parent partner ID
            delivery_data (dict): Delivery address data
            
        Returns:
            res.partner: Existing or newly created delivery contact
        """
        parent = self.browse(partner_id)
        
        # Buscar direcciones existentes similares
        existing_addresses = self.search([
            ('parent_id', '=', partner_id),
            ('type', '=', 'delivery'),
            ('street', '=', delivery_data.get('street', '')),
            ('city', '=', delivery_data.get('city', '')),
        ])
        
        if existing_addresses:
            # Si ya existe una dirección similar, actualizarla
            existing_address = existing_addresses[0]
            existing_address.write(delivery_data)
            return existing_address
        else:
            # Crear nueva dirección
            return self.create_delivery_address(partner_id, delivery_data)
