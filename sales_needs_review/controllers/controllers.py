# -*- coding: utf-8 -*-
# from odoo import http


# class SalesNeedsReview(http.Controller):
#     @http.route('/sales_needs_review/sales_needs_review', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sales_needs_review/sales_needs_review/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sales_needs_review.listing', {
#             'root': '/sales_needs_review/sales_needs_review',
#             'objects': http.request.env['sales_needs_review.sales_needs_review'].search([]),
#         })

#     @http.route('/sales_needs_review/sales_needs_review/objects/<model("sales_needs_review.sales_needs_review"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sales_needs_review.object', {
#             'object': obj
#         })
