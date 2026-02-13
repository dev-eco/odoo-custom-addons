# -*- coding: utf-8 -*-
# from odoo import http


# class PortalB2bDeliveryAddresses(http.Controller):
#     @http.route('/portal_b2b_delivery_addresses/portal_b2b_delivery_addresses', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/portal_b2b_delivery_addresses/portal_b2b_delivery_addresses/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('portal_b2b_delivery_addresses.listing', {
#             'root': '/portal_b2b_delivery_addresses/portal_b2b_delivery_addresses',
#             'objects': http.request.env['portal_b2b_delivery_addresses.portal_b2b_delivery_addresses'].search([]),
#         })

#     @http.route('/portal_b2b_delivery_addresses/portal_b2b_delivery_addresses/objects/<model("portal_b2b_delivery_addresses.portal_b2b_delivery_addresses"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('portal_b2b_delivery_addresses.object', {
#             'object': obj
#         })

