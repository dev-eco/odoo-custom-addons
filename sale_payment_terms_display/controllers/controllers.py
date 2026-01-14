# -*- coding: utf-8 -*-
# from odoo import http


# class SalePaymentTermsDisplay(http.Controller):
#     @http.route('/sale_payment_terms_display/sale_payment_terms_display', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_payment_terms_display/sale_payment_terms_display/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_payment_terms_display.listing', {
#             'root': '/sale_payment_terms_display/sale_payment_terms_display',
#             'objects': http.request.env['sale_payment_terms_display.sale_payment_terms_display'].search([]),
#         })

#     @http.route('/sale_payment_terms_display/sale_payment_terms_display/objects/<model("sale_payment_terms_display.sale_payment_terms_display"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_payment_terms_display.object', {
#             'object': obj
#         })

