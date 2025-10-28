# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.osv.expression import OR


class DistributorPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'delivery_count' in counters:
            delivery_count = request.env['distributor.delivery'].search_count(self._prepare_delivery_domain())
            values['delivery_count'] = delivery_count

        return values

    def _prepare_delivery_domain(self):
        partner = request.env.user.partner_id
        distributor_ids = request.env['distributor.distributor'].sudo().search([
            '|',
            ('partner_id', '=', partner.id),
            ('partner_id', 'in', partner.child_ids.ids)
        ])

        return [('distributor_id', 'in', distributor_ids.ids)]

    @http.route(['/my/deliveries', '/my/deliveries/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_deliveries(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        DeliveryOrder = request.env['distributor.delivery']

        domain = self._prepare_delivery_domain()

        searchbar_sortings = {
            'date': {'label': _('Fecha'), 'order': 'date desc'},
            'name': {'label': _('Referencia'), 'order': 'name'},
            'state': {'label': _('Estado'), 'order': 'state'},
        }

        searchbar_filters = {
            'all': {'label': _('Todos'), 'domain': []},
            'draft': {'label': _('Borrador'), 'domain': [('state', '=', 'draft')]},
            'confirmed': {'label': _('Confirmado'), 'domain': [('state', '=', 'confirmed')]},
            'done': {'label': _('Realizado'), 'domain': [('state', '=', 'done')]},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        delivery_count = DeliveryOrder.search_count(domain)

        # pager
        pager = portal_pager(
            url="/my/deliveries",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=delivery_count,
            page=page,
            step=self._items_per_page
        )

        # content according to pager and archive selected
        deliveries = DeliveryOrder.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'deliveries': deliveries,
            'page_name': 'delivery',
            'pager': pager,
            'default_url': '/my/deliveries',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })

        return request.render("custom_portal.portal_my_deliveries", values)

    @http.route(['/my/delivery/<int:delivery_id>'], type='http', auth="user", website=True)
    def portal_my_delivery(self, delivery_id=None, **kw):
        try:
            delivery_sudo = self._document_check_access('distributor.delivery', delivery_id)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'delivery': delivery_sudo,
            'page_name': 'delivery',
        }

        return request.render("custom_portal.portal_my_delivery", values)

    @http.route(['/my/delivery/create'], type='http', auth="user", website=True)
    def portal_create_delivery(self, **kw):
        partner = request.env.user.partner_id
        distributor_ids = request.env['distributor.distributor'].sudo().search([
            '|',
            ('partner_id', '=', partner.id),
            ('partner_id', 'in', partner.child_ids.ids)
        ])

        if not distributor_ids:
            return request.redirect('/my')

        values = {
            'distributors': distributor_ids,
            'page_name': 'create_delivery',
        }

        return request.render("custom_portal.portal_create_delivery", values)

    @http.route(['/my/delivery/submit'], type='http', auth="user", website=True)
    def portal_submit_delivery(self, **kw):
        distributor_id = int(kw.get('distributor_id', 0))
        partner_id = int(kw.get('partner_id', 0))
        date = kw.get('date')
        sale_order_reference = kw.get('sale_order_reference')
        notes = kw.get('notes')

        if not distributor_id or not partner_id or not date:
            return request.redirect('/my/delivery/create')

        # Verificar que el usuario tiene acceso a este distribuidor
        partner = request.env.user.partner_id
        distributor = request.env['distributor.distributor'].sudo().browse(distributor_id)

        if not distributor.exists() or distributor.partner_id.id not in [partner.id] + partner.child_ids.ids:
            return request.redirect('/my')

        # Crear el albarán
        vals = {
            'distributor_id': distributor_id,
            'partner_id': partner_id,
            'date': date,
            'sale_order_reference': sale_order_reference,
            'notes': notes,
        }

        delivery = request.env['distributor.delivery'].sudo().create(vals)

        return request.redirect('/my/delivery/%s' % delivery.id)
