# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Distributor(models.Model):
    _name = 'distributor.distributor'
    _description = 'Distribuidor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Contacto relacionado', required=True, tracking=True,
                                 domain=[('is_company', '=', True)])
    active = fields.Boolean(default=True, tracking=True)
    code = fields.Char(string='Código', tracking=True)
    user_ids = fields.Many2many('res.users', string='Usuarios del portal', tracking=True,
                               help='Usuarios que pueden acceder al portal como este distribuidor')

    delivery_count = fields.Integer(compute='_compute_delivery_count', string='Número de albaranes')

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'El código del distribuidor debe ser único!')
    ]

    @api.constrains('partner_id')
    def _check_partner_id(self):
        for record in self:
            if self.search_count([('partner_id', '=', record.partner_id.id), ('id', '!=', record.id)]):
                raise ValidationError(_('Este contacto ya está asignado a otro distribuidor.'))

    def _compute_delivery_count(self):
        for distributor in self:
            distributor.delivery_count = self.env['distributor.delivery'].search_count([
                ('distributor_id', '=', distributor.id)
            ])

    def action_view_deliveries(self):
        self.ensure_one()
        return {
            'name': _('Albaranes'),
            'type': 'ir.actions.act_window',
            'res_model': 'distributor.delivery',
            'view_mode': 'tree,form',
            'domain': [('distributor_id', '=', self.id)],
            'context': {'default_distributor_id': self.id},
        }
