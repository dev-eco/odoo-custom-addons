# -*- coding: utf-8 -*-
# from odoo import http


# class InvoiceDownloadPdf(http.Controller):
#     @http.route('/invoice_download_pdf/invoice_download_pdf', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/invoice_download_pdf/invoice_download_pdf/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('invoice_download_pdf.listing', {
#             'root': '/invoice_download_pdf/invoice_download_pdf',
#             'objects': http.request.env['invoice_download_pdf.invoice_download_pdf'].search([]),
#         })

#     @http.route('/invoice_download_pdf/invoice_download_pdf/objects/<model("invoice_download_pdf.invoice_download_pdf"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('invoice_download_pdf.object', {
#             'object': obj
#         })

