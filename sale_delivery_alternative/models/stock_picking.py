# -*- coding: utf-8 -*-

from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    original_partner_id = fields.Many2one(
        'res.partner',
        string="Cliente facturación",
        help="Cliente original del pedido (facturación)"
    )
    is_alternative_delivery = fields.Boolean(
        string="Entrega alternativa",
        help="Indica si este albarán usa una dirección de entrega alternativa"
    )

    def _get_report_delivery_data(self):
        """Método auxiliar para informes de entrega"""
        self.ensure_one()
        return {
            'partner_id': self.partner_id,
            'original_partner_id': self.original_partner_id,
            'is_alternative_delivery': self.is_alternative_delivery,
        }
