# -*- coding: utf-8 -*-

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalAddresses(http.Controller):
    """Controlador de direcciones de entrega para portal B2B."""
    
    @http.route(['/mis-direcciones', '/mis-direcciones/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_mis_direcciones(self, page=1, search=None, **kw):
        """Lista de direcciones de entrega del distribuidor."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        domain = [
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ]
        
        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('city', 'ilike', search),
                ('street', 'ilike', search)
            ]
        
        DeliveryAddress = request.env['delivery.address']
        address_count = DeliveryAddress.search_count(domain)
        
        from odoo.addons.portal.controllers.portal import pager as portal_pager
        pager = portal_pager(
            url='/mis-direcciones',
            url_args={'search': search},
            total=address_count,
            page=page,
            step=20,
        )
        
        addresses = DeliveryAddress.search(
            domain,
            limit=20,
            offset=pager['offset'],
            order='is_default desc, name asc'
        )
        
        countries = request.env['res.country'].search([])
        default_country = request.env.ref('base.es', raise_if_not_found=False)
        
        values = {
            'addresses': addresses,
            'page_name': 'mis_direcciones',
            'pager': pager,
            'search': search,
            'countries': countries,
            'default_country': default_country,
            'states': [],
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_mis_direcciones', values)

    @http.route(['/mis-direcciones/crear'], type='http', auth='user', website=True)
    def portal_crear_direccion(self, redirect=None, **kw):
        """Formulario para crear nueva dirección."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        countries = request.env['res.country'].search([])
        default_country = request.env.ref('base.es', raise_if_not_found=False)
        
        states = []
        if default_country:
            states = request.env['res.country.state'].search([
                ('country_id', '=', default_country.id)
            ], order='name')
        
        values = {
            'page_name': 'crear_direccion',
            'countries': countries,
            'default_country': default_country,
            'states': states,
            'redirect_url': redirect or '/mis-direcciones',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_direccion', values)

    @http.route(['/mis-direcciones/<int:address_id>/editar'], 
                type='http', auth='user', website=True)
    def portal_editar_direccion(self, address_id, **kw):
        """Formulario para editar dirección."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        address = request.env['delivery.address'].browse(address_id)
        
        if not address.exists() or address.partner_id != partner:
            return request.redirect('/mis-direcciones')
        
        countries = request.env['res.country'].search([])
        
        states = []
        if address.country_id:
            states = request.env['res.country.state'].search([
                ('country_id', '=', address.country_id.id)
            ], order='name')
        
        values = {
            'address': address,
            'page_name': 'editar_direccion',
            'countries': countries,
            'states': states,
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_editar_direccion', values)
