# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo para activar direcciones alternativas (distribuidores)
    use_alternative_delivery = fields.Boolean(
        string='Use Alternative Delivery Address',
        default=False,
        help='Enable to select from alternative delivery addresses',
        compute='_compute_use_alternative_delivery',
        store=True,
        readonly=False
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
        inverse='_inverse_delivery_name',
        store=False
    )
    
    delivery_street = fields.Char(
        string='Delivery Street',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street',
        store=False
    )
    
    delivery_street2 = fields.Char(
        string='Delivery Street 2',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street2',
        store=False
    )
    
    delivery_city = fields.Char(
        string='Delivery City',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_city',
        store=False
    )
    
    delivery_state_id = fields.Many2one(
        'res.country.state',
        string='Delivery State',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_state_id',
        store=False
    )
    
    delivery_zip = fields.Char(
        string='Delivery ZIP',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_zip',
        store=False
    )
    
    delivery_country_id = fields.Many2one(
        'res.country',
        string='Delivery Country',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_country_id',
        store=False
    )
    
    delivery_phone = fields.Char(
        string='Delivery Phone',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_phone',
        store=False
    )
    
    delivery_email = fields.Char(
        string='Delivery Email',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_email',
        store=False
    )
    
    # Información de estado para controles de seguridad
    can_edit_delivery = fields.Boolean(
        string='Can Edit Delivery',
        compute='_compute_can_edit_delivery',
        store=False
    )
    
    # Direcciones disponibles para distribuidores
    available_delivery_addresses = fields.Selection(
        selection='_get_available_delivery_addresses',
        string='Available Delivery Addresses',
        help='List of available delivery addresses for distributors'
    )

    @api.depends('partner_id', 'partner_id.is_distributor')
    def _compute_use_alternative_delivery(self):
        """Auto-enable alternative delivery for distributors"""
        for order in self:
            order.use_alternative_delivery = order.partner_id.is_distributor

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
                order.delivery_street2 = delivery_partner.street2 or ''
                order.delivery_city = delivery_partner.city or ''
                order.delivery_state_id = delivery_partner.state_id.id if delivery_partner.state_id else False
                order.delivery_zip = delivery_partner.zip or ''
                order.delivery_country_id = delivery_partner.country_id.id if delivery_partner.country_id else False
                order.delivery_phone = delivery_partner.phone or ''
                order.delivery_email = delivery_partner.email or ''
            else:
                # Limpiar campos si no hay partner de entrega
                order.delivery_name = ''
                order.delivery_street = ''
                order.delivery_street2 = ''
                order.delivery_city = ''
                order.delivery_state_id = False
                order.delivery_zip = ''
                order.delivery_country_id = False
                order.delivery_phone = ''
                order.delivery_email = ''

    @api.depends('state')
    def _compute_can_edit_delivery(self):
        """Compute if user can edit delivery address based on order state and user rights"""
        for order in self:
            if order.state in ['draft', 'sent']:
                # En borrador o enviado, cualquier usuario de ventas puede editar
                order.can_edit_delivery = self.env.user.has_group('sales_team.group_sale_salesman')
            else:
                # Después de confirmación, solo Sales Manager
                order.can_edit_delivery = self.env.user.has_group('sales_team.group_sale_manager')

    def _get_available_delivery_addresses(self):
        """Get available delivery addresses for selection"""
        if not self.partner_id:
            return []
        
        return self.partner_id.get_delivery_addresses_for_selection()

    # Métodos inverse para actualizar direcciones cuando se modifican campos inline
    def _inverse_delivery_name(self):
        for order in self:
            if order.delivery_name:
                order._update_delivery_address({'name': order.delivery_name})

    def _inverse_delivery_street(self):
        for order in self:
            order._update_delivery_address({'street': order.delivery_street})

    def _inverse_delivery_street2(self):
        for order in self:
            order._update_delivery_address({'street2': order.delivery_street2})

    def _inverse_delivery_city(self):
        for order in self:
            order._update_delivery_address({'city': order.delivery_city})

    def _inverse_delivery_state_id(self):
        for order in self:
            order._update_delivery_address({'state_id': order.delivery_state_id.id if order.delivery_state_id else False})

    def _inverse_delivery_zip(self):
        for order in self:
            order._update_delivery_address({'zip': order.delivery_zip})

    def _inverse_delivery_country_id(self):
        for order in self:
            order._update_delivery_address({'country_id': order.delivery_country_id.id if order.delivery_country_id else False})

    def _inverse_delivery_phone(self):
        for order in self:
            order._update_delivery_address({'phone': order.delivery_phone})

    def _inverse_delivery_email(self):
        for order in self:
            order._update_delivery_address({'email': order.delivery_email})

    def _update_delivery_address(self, update_vals):
        """
        Update delivery address with new values and log changes
        
        Args:
            update_vals (dict): Values to update
        """
        self.ensure_one()
        
        # Verificar permisos de edición
        if not self.can_edit_delivery:
            raise UserError(_('You do not have permission to edit delivery address for confirmed orders'))
        
        # Determinar qué partner actualizar
        if self.use_alternative_delivery and self.selected_delivery_partner_id:
            delivery_partner = self.selected_delivery_partner_id
        else:
            delivery_partner = self.partner_shipping_id
        
        if not delivery_partner:
            # Crear nueva dirección de entrega
            delivery_partner = self._create_new_delivery_address(update_vals)
        else:
            # Actualizar dirección existente
            old_vals = {field: delivery_partner[field] for field in update_vals.keys() if hasattr(delivery_partner, field)}
            delivery_partner.write(update_vals)
            
            # Log del cambio en chatter
            self._log_delivery_change(old_vals, update_vals, delivery_partner)

    def _create_new_delivery_address(self, address_data):
        """
        Create new delivery address and assign to order
        
        Args:
            address_data (dict): Address data for creation
            
        Returns:
            res.partner: Created delivery partner
        """
        self.ensure_one()
        
        # Preparar datos completos para la dirección
        delivery_data = {
            'name': address_data.get('name', f"{self.partner_id.name} - Delivery"),
            'parent_id': self.partner_id.id,
            'type': 'delivery',
            'street': address_data.get('street', ''),
            'street2': address_data.get('street2', ''),
            'city': address_data.get('city', ''),
            'state_id': address_data.get('state_id', False),
            'zip': address_data.get('zip', ''),
            'country_id': address_data.get('country_id', self.partner_id.country_id.id),
            'phone': address_data.get('phone', ''),
            'email': address_data.get('email', ''),
            'company_id': self.company_id.id,
        }
        
        # Crear la dirección
        new_address = self.env['res.partner'].create(delivery_data)
        
        # Asignar al pedido
        if self.use_alternative_delivery:
            self.selected_delivery_partner_id = new_address
        else:
            self.partner_shipping_id = new_address
        
        # Log en chatter
        self.message_post(
            body=_('New delivery address created: %s') % new_address.contact_address,
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        return new_address

    def _log_delivery_change(self, old_vals, new_vals, delivery_partner):
        """
        Log delivery address changes in chatter
        
        Args:
            old_vals (dict): Previous values
            new_vals (dict): New values  
            delivery_partner (res.partner): Modified delivery partner
        """
        self.ensure_one()
        
        changes = []
        field_names = {
            'name': _('Contact Name'),
            'street': _('Street'),
            'street2': _('Street 2'),
            'city': _('City'),
            'state_id': _('State'),
            'zip': _('ZIP'),
            'country_id': _('Country'),
            'phone': _('Phone'),
            'email': _('Email'),
        }
        
        for field, new_value in new_vals.items():
            if field in old_vals and old_vals[field] != new_value:
                old_display = old_vals[field] or _('(empty)')
                new_display = new_value or _('(empty)')
                
                # Tratamiento especial para Many2one fields
                if field in ['state_id', 'country_id'] and new_value:
                    related_record = self.env['res.country.state' if field == 'state_id' else 'res.country'].browse(new_value)
                    new_display = related_record.name if related_record.exists() else new_display
                
                changes.append(f"• {field_names.get(field, field)}: {old_display} → {new_display}")
        
        if changes:
            body = _('Delivery address updated for %s:\n%s') % (
                delivery_partner.name,
                '\n'.join(changes)
            )
            self.message_post(
                body=body,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
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
            # Resetear campos de dirección alternativa
            self.selected_delivery_partner_id = False
            self.use_alternative_delivery = self.partner_id.is_distributor
        else:
            self.use_alternative_delivery = False
            self.selected_delivery_partner_id = False

    def action_create_delivery_address(self):
        """Action to create a new delivery address from current inline fields"""
        self.ensure_one()
        
        if not self.can_edit_delivery:
            raise UserError(_('You do not have permission to create delivery addresses for confirmed orders'))
        
        # Recopilar datos de los campos inline
        address_data = {
            'name': self.delivery_name or f"{self.partner_id.name} - New Delivery",
            'street': self.delivery_street,
            'street2': self.delivery_street2,
            'city': self.delivery_city,
            'state_id': self.delivery_state_id.id if self.delivery_state_id else False,
            'zip': self.delivery_zip,
            'country_id': self.delivery_country_id.id if self.delivery_country_id else False,
            'phone': self.delivery_phone,
            'email': self.delivery_email,
        }
        
        # Crear la dirección
        new_address = self._create_new_delivery_address(address_data)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Delivery address created successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def create(self, vals):
        """Override create to handle delivery address on creation"""
        order = super(SaleOrder, self).create(vals)
        
        # Si se proporciona información de entrega inline durante creación
        delivery_fields = [
            'delivery_name', 'delivery_street', 'delivery_street2', 
            'delivery_city', 'delivery_state_id', 'delivery_zip',
            'delivery_country_id', 'delivery_phone', 'delivery_email'
        ]
        
        delivery_data = {k: v for k, v in vals.items() if k in delivery_fields and v}
        
        if delivery_data and not order.partner_shipping_id:
            # Crear dirección de entrega automáticamente
            order._create_new_delivery_address(delivery_data)
        
        return order

    def write(self, vals):
        """Override write to ensure delivery fields consistency"""
        # Log changes before write for chatter
        for order in self:
            if any(field.startswith('delivery_') for field in vals.keys()):
                # Se están modificando campos de entrega
                if not order.can_edit_delivery:
                    raise UserError(_('You do not have permission to edit delivery address for confirmed orders'))
        
        return super(SaleOrder, self).write(vals)
