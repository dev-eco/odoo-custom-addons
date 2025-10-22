# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo para activar direcciones alternativas (distribuidores)
    use_alternative_delivery = fields.Boolean(
        string='Use Alternative Delivery Address',
        default=False,
        help='Enable to select from alternative delivery addresses',
        compute='_compute_use_alternative_delivery',
        store=True
    )
    
    # Dirección de entrega seleccionada
    selected_delivery_partner_id = fields.Many2one(
        'res.partner',
        string='Selected Delivery Address',
        domain="[('parent_id', '=', partner_id), ('type', '=', 'delivery')]",
        help='Selected delivery address for this order'
    )
    
    # Campos inline para edición de dirección
    delivery_name = fields.Char(
        string='Delivery Contact Name',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_name'
    )
    
    delivery_street = fields.Char(
        string='Delivery Street',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street'
    )
    
    delivery_city = fields.Char(
        string='Delivery City',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_city'
    )
    
    delivery_zip = fields.Char(
        string='Delivery ZIP',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_zip'
    )
    
    delivery_phone = fields.Char(
        string='Delivery Phone',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_phone'
    )
    
    delivery_email = fields.Char(
        string='Delivery Email',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_email'
    )

    @api.depends('partner_id', 'partner_id.is_distributor')
    def _compute_use_alternative_delivery(self):
        """Auto-enable alternative delivery for distributors"""
        for order in self:
            if order.partner_id:
                order.use_alternative_delivery = order.partner_id.is_distributor
            else:
                order.use_alternative_delivery = False

    @api.depends('partner_shipping_id', 'selected_delivery_partner_id', 'use_alternative_delivery')
    def _compute_delivery_fields(self):
        """Compute delivery fields from the appropriate partner"""
        for order in self:
            # Determinar qué partner usar para la dirección
            if order.use_alternative_delivery and order.selected_delivery_partner_id:
                delivery_partner = order.selected_delivery_partner_id
            else:
                delivery_partner = order.partner_shipping_id
            
            if delivery_partner:
                order.delivery_name = delivery_partner.name or ''
                order.delivery_street = delivery_partner.street or ''
                order.delivery_city = delivery_partner.city or ''
                order.delivery_zip = delivery_partner.zip or ''
                order.delivery_phone = delivery_partner.phone or ''
                order.delivery_email = delivery_partner.email or ''
            else:
                # Limpiar campos si no hay partner de entrega
                order.delivery_name = ''
                order.delivery_street = ''
                order.delivery_city = ''
                order.delivery_zip = ''
                order.delivery_phone = ''
                order.delivery_email = ''

    def _inverse_delivery_name(self):
        for order in self:
            if order.delivery_name:
                order._update_delivery_field('name', order.delivery_name)

    def _inverse_delivery_street(self):
        for order in self:
            order._update_delivery_field('street', order.delivery_street)

    def _inverse_delivery_city(self):
        for order in self:
            order._update_delivery_field('city', order.delivery_city)

    def _inverse_delivery_zip(self):
        for order in self:
            order._update_delivery_field('zip', order.delivery_zip)

    def _inverse_delivery_phone(self):
        for order in self:
            order._update_delivery_field('phone', order.delivery_phone)

    def _inverse_delivery_email(self):
        for order in self:
            order._update_delivery_field('email', order.delivery_email)

    def _update_delivery_field(self, field_name, value):
        """Update a specific field in the delivery partner"""
        self.ensure_one()
        
        # Determinar qué partner actualizar
        if self.use_alternative_delivery and self.selected_delivery_partner_id:
            delivery_partner = self.selected_delivery_partner_id
        else:
            delivery_partner = self.partner_shipping_id
        
        if delivery_partner:
            delivery_partner.write({field_name: value})
            # Log simple en chatter
            self.message_post(
                body=_('Delivery address updated: %s = %s') % (field_name, value),
                message_type='notification'
            )

    @api.onchange('selected_delivery_partner_id')
    def _onchange_selected_delivery_partner(self):
        """Update partner_shipping_id when alternative address is selected"""
        if self.use_alternative_delivery and self.selected_delivery_partner_id:
            self.partner_shipping_id = self.selected_delivery_partner_id

    @api.onchange('partner_id')
    def _onchange_partner_id_delivery(self):
        """Reset delivery selections when main partner changes"""
        if self.partner_id:
            self.selected_delivery_partner_id = False
            self.use_alternative_delivery = self.partner_id.is_distributor
        else:
            self.use_alternative_delivery = False
            self.selected_delivery_partner_id = False
