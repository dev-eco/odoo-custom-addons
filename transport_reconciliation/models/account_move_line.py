# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    transport_carrier_id = fields.Many2one(
        'res.partner',
        string='Transportista',
        domain=[('is_transport_carrier', '=', True)],
        help='Transportista asociado a esta línea de factura'
    )
    transport_reference = fields.Char(
        string='Referencia de Transporte',
        help='Número de albarán o referencia de transporte'
    )
