# -*- coding: utf-8 -*-
# from odoo import http


# class SaleMaterialPlanning(http.Controller):
#     @http.route('/sale_material_planning/sale_material_planning', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_material_planning/sale_material_planning/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_material_planning.listing', {
#             'root': '/sale_material_planning/sale_material_planning',
#             'objects': http.request.env['sale_material_planning.sale_material_planning'].search([]),
#         })

#     @http.route('/sale_material_planning/sale_material_planning/objects/<model("sale_material_planning.sale_material_planning"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_material_planning.object', {
#             'object': obj
#         })

