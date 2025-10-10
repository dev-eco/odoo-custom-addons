# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class document_automation(models.Model):
#     _name = 'document_automation.document_automation'
#     _description = 'document_automation.document_automation'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

