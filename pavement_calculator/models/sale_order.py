# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    pavement_calculator_ids = fields.One2many(
        'pavement.calculator', 
        'sale_order_id', 
        string='Cálculos de Pavimento',
        readonly=True,
    )
    
    pavement_calculator_count = fields.Integer(
        string='Número de Cálculos',
        compute='_compute_pavement_calculator_count',
    )
    
    @api.depends('pavement_calculator_ids')
    def _compute_pavement_calculator_count(self):
        for order in self:
            order.pavement_calculator_count = len(order.pavement_calculator_ids)
    
    def action_view_pavement_calculators(self):
        self.ensure_one()
        return {
            'name': _('Cálculos de Pavimento'),
            'type': 'ir.actions.act_window',
            'res_model': 'pavement.calculator',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.pavement_calculator_ids.ids)],
        }
    
    def action_create_pavement_calculator(self):
        self.ensure_one()
        return {
            'name': _('Nueva Calculadora de Pavimento'),
            'type': 'ir.actions.act_window',
            'res_model': 'pavement.calculator.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_sale_order_id': self.id,
            },
        }
