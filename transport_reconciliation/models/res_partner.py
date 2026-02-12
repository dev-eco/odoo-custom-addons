# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_transport_carrier = fields.Boolean(
        string='Es Transportista',
        help='Marcar si este proveedor es una agencia de transporte'
    )
    transport_carrier_code = fields.Char(
        string='Código Transportista',
        help='Código identificativo del transportista'
    )
