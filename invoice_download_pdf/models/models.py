# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class invoice_download_pdf(models.Model):
#     _name = 'invoice_download_pdf.invoice_download_pdf'
#     _description = 'invoice_download_pdf.invoice_download_pdf'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

