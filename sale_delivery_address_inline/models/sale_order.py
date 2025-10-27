# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ==========================================
    # CAMPOS PRINCIPALES
    # ==========================================
    
    is_distributor_customer = fields.Boolean(
        string='Cliente Distribuidor',
        compute='_compute_is_distributor_customer',
        store=True,
        help="Indica si el cliente es un distribuidor"
    )
    
    use_alternative_delivery = fields.Boolean(
        string='Usar Dirección Alternativa',
        default=False,
        tracking=True,
        help="Activa para usar dirección distinta a la predeterminada"
    )
    
    selected_delivery_partner_id = fields.Many2one(
        'res.partner',
        string='Dirección de Entrega Seleccionada',
        domain="[('parent_id', '=', partner_id), ('type', '=', 'delivery'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True
    )
    
    # NUEVO - Indicador de dirección temporal
    is_temporary_delivery = fields.Boolean(
        string='Dirección Temporal',
        compute='_compute_is_temporary_delivery',
        store=True,
        help="Indica si la dirección de entrega es temporal (proyecto)"
    )
    
    delivery_project_reference = fields.Char(
        string='Ref. Proyecto',
        related='partner_shipping_id.project_reference',
        store=True
    )
    
    # Campos de dirección inline
    delivery_name = fields.Char(
        string='Nombre Contacto',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_name',
        tracking=True
    )
    
    delivery_street = fields.Char(
        string='Dirección',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street',
        tracking=True
    )
    
    delivery_street2 = fields.Char(
        string='Info Adicional',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street2',
        tracking=True
    )
    
    delivery_city = fields.Char(
        string='Ciudad',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_city',
        tracking=True
    )
    
    delivery_zip = fields.Char(
        string='C.P.',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_zip',
        tracking=True
    )
    
    delivery_state_id = fields.Many2one(
        'res.country.state',
        string='Provincia',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_state',
        tracking=True
    )
    
    delivery_country_id = fields.Many2one(
        'res.country',
        string='País',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_country',
        tracking=True
    )
    
    delivery_phone = fields.Char(
        string='Teléfono',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_phone',
        tracking=True
    )
    
    delivery_email = fields.Char(
        string='Email',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_email',
        tracking=True
    )
    
    delivery_address_modified = fields.Boolean(
        string='Dirección Modificada',
        default=False,
        copy=False,
        help="Indica modificación post-confirmación"
    )
    
    # ==========================================
    # CAMPOS COMPUTADOS
    # ==========================================
    
    @api.depends('partner_id', 'partner_id.is_distributor')
    def _compute_is_distributor_customer(self):
        """Determina si el cliente es distribuidor"""
        for order in self:
            order.is_distributor_customer = (
                order.partner_id.is_distributor if order.partner_id else False
            )
    
    @api.depends('partner_shipping_id', 'partner_shipping_id.is_temporary_address')
    def _compute_is_temporary_delivery(self):
        """Determina si la dirección es temporal"""
        for order in self:
            order.is_temporary_delivery = (
                order.partner_shipping_id.is_temporary_address 
                if order.partner_shipping_id else False
            )
    
    @api.depends('partner_shipping_id', 'selected_delivery_partner_id')
    def _compute_delivery_fields(self):
        """Calcula campos de dirección desde la dirección seleccionada"""
        for order in self:
            shipping = order.partner_shipping_id
            if shipping:
                order.delivery_name = shipping.name or ''
                order.delivery_street = shipping.street or ''
                order.delivery_street2 = shipping.street2 or ''
                order.delivery_city = shipping.city or ''
                order.delivery_zip = shipping.zip or ''
                order.delivery_state_id = shipping.state_id.id if shipping.state_id else False
                order.delivery_country_id = shipping.country_id.id if shipping.country_id else False
                order.delivery_phone = shipping.phone or ''
                order.delivery_email = shipping.email or ''
            else:
                order.delivery_name = ''
                order.delivery_street = ''
                order.delivery_street2 = ''
                order.delivery_city = ''
                order.delivery_zip = ''
                order.delivery_state_id = False
                order.delivery_country_id = False
                order.delivery_phone = ''
                order.delivery_email = ''
    
    # ==========================================
    # ONCHANGES
    # ==========================================
    
    @api.onchange('partner_id')
    def _onchange_partner_id_delivery(self):
        """Al cambiar cliente, resetea campos de entrega"""
        if self.partner_id:
            self.use_alternative_delivery = False
            self.selected_delivery_partner_id = False
            
            if self.is_distributor_customer:
                delivery_addrs = self.partner_id.child_ids.filtered(
                    lambda r: r.type == 'delivery'
                )
                if delivery_addrs:
                    self.partner_shipping_id = delivery_addrs[0]
            else:
                self.partner_shipping_id = self.partner_id
    
    @api.onchange('use_alternative_delivery')
    def _onchange_use_alternative_delivery(self):
        """Gestiona cambio de opción alternativa"""
        if not self.use_alternative_delivery:
            self.selected_delivery_partner_id = False
            self.partner_shipping_id = self.partner_id
        else:
            delivery_addrs = self.partner_id.child_ids.filtered(
                lambda r: r.type == 'delivery'
            )
            if delivery_addrs:
                self.selected_delivery_partner_id = delivery_addrs[0]
                self.partner_shipping_id = delivery_addrs[0]
    
    @api.onchange('selected_delivery_partner_id')
    def _onchange_selected_delivery_partner_id(self):
        """Al seleccionar dirección, actualiza partner_shipping_id"""
        if self.selected_delivery_partner_id:
            self.partner_shipping_id = self.selected_delivery_partner_id
        elif self.use_alternative_delivery:
            self.partner_shipping_id = self.partner_id
    
    # ==========================================
    # MÉTODOS INVERSOS
    # ==========================================
    
    def _check_modify_permission(self):
        """Verifica permisos para modificar direcciones en pedidos confirmados"""
        self.ensure_one()
        if self.state in ['sale', 'done']:
            if not self.env.user.has_group('sales_team.group_sale_manager'):
                raise AccessError(_(
                    "Solo gerentes de ventas pueden modificar direcciones "
                    "en pedidos confirmados"
                ))
    
    def _log_delivery_field_change(self, field_name, old_value, new_value):
        """Registra cambios en dirección de entrega"""
        self.ensure_one()
        message = _(
            "📍 Dirección de entrega actualizada:<br/>"
            "<strong>%s:</strong> %s → %s"
        ) % (field_name, old_value or '-', new_value or '-')
        self.message_post(body=message)
    
    def _inverse_delivery_name(self):
        for order in self:
            if order.partner_shipping_id and order.delivery_name:
                order._check_modify_permission()
                old = order.partner_shipping_id.name
                if old != order.delivery_name:
                    order.partner_shipping_id.name = order.delivery_name
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Nombre', old, order.delivery_name)
    
    def _inverse_delivery_street(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.street
                if old != order.delivery_street:
                    order.partner_shipping_id.street = order.delivery_street
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Dirección', old, order.delivery_street)
    
    def _inverse_delivery_street2(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.street2
                if old != order.delivery_street2:
                    order.partner_shipping_id.street2 = order.delivery_street2
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Info adicional', old, order.delivery_street2)
    
    def _inverse_delivery_city(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.city
                if old != order.delivery_city:
                    order.partner_shipping_id.city = order.delivery_city
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Ciudad', old, order.delivery_city)
    
    def _inverse_delivery_zip(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.zip
                if old != order.delivery_zip:
                    order.partner_shipping_id.zip = order.delivery_zip
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('C.P.', old, order.delivery_zip)
    
    def _inverse_delivery_state(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.state_id.name if order.partner_shipping_id.state_id else ''
                new = order.delivery_state_id.name if order.delivery_state_id else ''
                if old != new:
                    order.partner_shipping_id.state_id = order.delivery_state_id.id
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Provincia', old, new)
    
    def _inverse_delivery_country(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.country_id.name if order.partner_shipping_id.country_id else ''
                new = order.delivery_country_id.name if order.delivery_country_id else ''
                if old != new:
                    order.partner_shipping_id.country_id = order.delivery_country_id.id
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('País', old, new)
    
    def _inverse_delivery_phone(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.phone
                if old != order.delivery_phone:
                    order.partner_shipping_id.phone = order.delivery_phone
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Teléfono', old, order.delivery_phone)
    
    def _inverse_delivery_email(self):
        for order in self:
            if order.partner_shipping_id:
                order._check_modify_permission()
                old = order.partner_shipping_id.email
                if old != order.delivery_email:
                    order.partner_shipping_id.email = order.delivery_email
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        order._log_delivery_field_change('Email', old, order.delivery_email)
    
    # ==========================================
    # ACTIONS
    # ==========================================
    
    def action_create_delivery_address(self):
        """Abre wizard para crear nueva dirección"""
        self.ensure_one()
        
        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente primero"))
        
        return {
            'name': _('Nueva Dirección de Entrega'),
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.address.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_sale_order_id': self.id,
                'default_company_id': self.company_id.id,
            }
        }
