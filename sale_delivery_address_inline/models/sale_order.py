# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campos indicadores
    is_distributor_customer = fields.Boolean(
        string='Cliente Distribuidor',
        compute='_compute_is_distributor_customer',
        store=True
    )
    
    use_alternative_delivery = fields.Boolean(
        string='Usar Dirección Alternativa',
        default=False
    )
    
    selected_delivery_partner_id = fields.Many2one(
        'res.partner',
        string='Dirección Seleccionada',
        domain="[('parent_id', '=', partner_id), ('type', '=', 'delivery')]"
    )
    
    is_temporary_delivery = fields.Boolean(
        string='Dirección Temporal',
        related='partner_shipping_id.is_temporary_address',
        store=True
    )

    # Campos RELATED (simples y eficientes)
    delivery_name = fields.Char(
        related='partner_shipping_id.name',
        string='Contacto',
        readonly=False
    )
    
    delivery_street = fields.Char(
        related='partner_shipping_id.street',
        string='Calle',
        readonly=False
    )
    
    delivery_city = fields.Char(
        related='partner_shipping_id.city',
        string='Ciudad',
        readonly=False
    )
    
    delivery_zip = fields.Char(
        related='partner_shipping_id.zip',
        string='C.P.',
        readonly=False
    )
    
    delivery_state_id = fields.Many2one(
        'res.country.state',
        related='partner_shipping_id.state_id',
        string='Provincia',
        readonly=False
    )
    
    delivery_country_id = fields.Many2one(
        'res.country',
        related='partner_shipping_id.country_id',
        string='País',
        readonly=False
    )
    
    delivery_phone = fields.Char(
        related='partner_shipping_id.phone',
        string='Teléfono',
        readonly=False
    )
    
    delivery_email = fields.Char(
        related='partner_shipping_id.email',
        string='Email',
        readonly=False
    )

    @api.depends('partner_id', 'partner_id.is_distributor')
    def _compute_is_distributor_customer(self):
        for order in self:
            order.is_distributor_customer = order.partner_id.is_distributor if order.partner_id else False

    @api.onchange('partner_id')
    def _onchange_partner_id_delivery(self):
        if self.partner_id:
            self.use_alternative_delivery = False
            self.selected_delivery_partner_id = False

    @api.onchange('selected_delivery_partner_id')
    def _onchange_selected_delivery_partner_id(self):
        if self.selected_delivery_partner_id:
            self.partner_shipping_id = self.selected_delivery_partner_id

    def action_create_delivery_address(self):
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
            }
        }
