# -*- coding: utf-8 -*-
# from odoo import http


# class IndustryReportsBase(http.Controller):
#     @http.route('/industry_reports_base/industry_reports_base', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/industry_reports_base/industry_reports_base/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('industry_reports_base.listing', {
#             'root': '/industry_reports_base/industry_reports_base',
#             'objects': http.request.env['industry_reports_base.industry_reports_base'].search([]),
#         })

#     @http.route('/industry_reports_base/industry_reports_base/objects/<model("industry_reports_base.industry_reports_base"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('industry_reports_base.object', {
#             'object': obj
#         })
