# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class portal_b2b_delivery_addresses(models.Model):
#     _name = 'portal_b2b_delivery_addresses.portal_b2b_delivery_addresses'
#     _description = 'portal_b2b_delivery_addresses.portal_b2b_delivery_addresses'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

