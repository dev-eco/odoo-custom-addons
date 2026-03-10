# -*- coding: utf-8 -*-
# from odoo import http


# class PortalB2bBase(http.Controller):
#     @http.route('/portal_b2b_base/portal_b2b_base', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/portal_b2b_base/portal_b2b_base/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('portal_b2b_base.listing', {
#             'root': '/portal_b2b_base/portal_b2b_base',
#             'objects': http.request.env['portal_b2b_base.portal_b2b_base'].search([]),
#         })

#     @http.route('/portal_b2b_base/portal_b2b_base/objects/<model("portal_b2b_base.portal_b2b_base"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('portal_b2b_base.object', {
#             'object': obj
#         })
