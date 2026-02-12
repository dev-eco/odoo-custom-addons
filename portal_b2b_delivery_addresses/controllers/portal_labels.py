# -*- coding: utf-8 -*-

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalLabels(http.Controller):
    """Controlador de etiquetas cliente final para portal B2B."""
    
    @http.route(['/mis-etiquetas', '/mis-etiquetas/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_mis_etiquetas(self, page=1, search=None, **kw):
        """Lista de etiquetas de cliente final."""
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
                ('customer_name', 'ilike', search),
                ('customer_reference', 'ilike', search)
            ]
        
        DistributorLabel = request.env['distributor.label']
        label_count = DistributorLabel.search_count(domain)
        
        from odoo.addons.portal.controllers.portal import pager as portal_pager
        pager = portal_pager(
            url='/mis-etiquetas',
            url_args={'search': search},
            total=label_count,
            page=page,
            step=20,
        )
        
        labels = DistributorLabel.search(
            domain,
            limit=20,
            offset=pager['offset'],
            order='name asc'
        )
        
        values = {
            'labels': labels,
            'label_count': label_count,
            'page_name': 'mis_etiquetas',
            'pager': pager,
            'search': search,
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_mis_etiquetas', values)

    @http.route(['/mis-etiquetas/crear'], type='http', auth='user', website=True)
    def portal_crear_etiqueta(self, redirect=None, **kw):
        """Formulario para crear nueva etiqueta."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        values = {
            'label': None,
            'page_name': 'crear_etiqueta',
            'redirect_url': redirect or '/mis-etiquetas',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_etiqueta', values)

    @http.route(['/mis-etiquetas/<int:label_id>/editar'], 
                type='http', auth='user', website=True)
    def portal_editar_etiqueta(self, label_id, **kw):
        """Formulario para editar etiqueta."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        label = request.env['distributor.label'].browse(label_id)
        
        if not label.exists() or label.partner_id != partner:
            return request.redirect('/mis-etiquetas')
        
        values = {
            'label': label,
            'page_name': 'editar_etiqueta',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_etiqueta', values)
