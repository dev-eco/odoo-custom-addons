# -*- coding: utf-8 -*-
# from odoo import http


# class DocumentAutomation(http.Controller):
#     @http.route('/document_automation/document_automation', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/document_automation/document_automation/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('document_automation.listing', {
#             'root': '/document_automation/document_automation',
#             'objects': http.request.env['document_automation.document_automation'].search([]),
#         })

#     @http.route('/document_automation/document_automation/objects/<model("document_automation.document_automation"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('document_automation.object', {
#             'object': obj
#         })

