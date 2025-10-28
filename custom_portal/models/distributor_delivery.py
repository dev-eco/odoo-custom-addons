# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DistributorDelivery(models.Model):
    _name = 'distributor.delivery'
    _description = 'Albarán de Distribuidor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nuevo'))
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    distributor_id = fields.Many2one('distributor.distributor', string='Distribuidor',
                                    required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, tracking=True)
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True, tracking=True)
    sale_order_reference = fields.Char(string='Referencia de pedido', tracking=True)
    notes = fields.Text(string='Notas', tracking=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmado'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)

    # Campos relacionados para facilitar búsquedas y agrupaciones
    distributor_partner_id = fields.Many2one('res.partner', related='distributor_id.partner_id',
                                           string='Empresa distribuidora', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('distributor.delivery') or _('Nuevo')
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'
            record.message_post(body=_("Albarán confirmado"))

    def action_done(self):
        for record in self:
            record.state = 'done'
            record.message_post(body=_("Albarán marcado como realizado"))

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'
            record.message_post(body=_("Albarán cancelado"))

    def action_draft(self):
        for record in self:
            record.state = 'draft'
            record.message_post(body=_("Albarán devuelto a borrador"))
