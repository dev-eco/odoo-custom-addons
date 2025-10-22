# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campos básicos para direcciones inline
    delivery_name = fields.Char(
        string='Nombre de Contacto de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_name'
    )
    
    delivery_street = fields.Char(
        string='Dirección de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street'
    )
    
    delivery_city = fields.Char(
        string='Ciudad de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_city'
    )
    
    delivery_zip = fields.Char(
        string='Código Postal',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_zip'
    )
    
    delivery_phone = fields.Char(
        string='Teléfono de Contacto',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_phone'
    )

    @api.depends('partner_shipping_id')
    def _compute_delivery_fields(self):
        for order in self:
            if order.partner_shipping_id:
                order.delivery_name = order.partner_shipping_id.name or ''
                order.delivery_street = order.partner_shipping_id.street or ''
                order.delivery_city = order.partner_shipping_id.city or ''
                order.delivery_zip = order.partner_shipping_id.zip or ''
                order.delivery_phone = order.partner_shipping_id.phone or ''
            else:
                order.delivery_name = ''
                order.delivery_street = ''
                order.delivery_city = ''
                order.delivery_zip = ''
                order.delivery_phone = ''

    def _inverse_delivery_name(self):
        for order in self:
            if order.partner_shipping_id and order.delivery_name:
                order.partner_shipping_id.name = order.delivery_name

    def _inverse_delivery_street(self):
        for order in self:
            if order.partner_shipping_id:
                order.partner_shipping_id.street = order.delivery_street

    def _inverse_delivery_city(self):
        for order in self:
            if order.partner_shipping_id:
                order.partner_shipping_id.city = order.delivery_city

    def _inverse_delivery_zip(self):
        for order in self:
            if order.partner_shipping_id:
                order.partner_shipping_id.zip = order.delivery_zip

    def _inverse_delivery_phone(self):
        for order in self:
            if order.partner_shipping_id:
                order.partner_shipping_id.phone = order.delivery_phone
