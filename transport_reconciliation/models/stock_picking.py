# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transport_carrier_id = fields.Many2one(
        'res.partner',
        string='Transportista',
        domain=[('is_transport_carrier', '=', True)],
        tracking=True,
        help='Agencia de transporte responsable del envío'
    )
    transport_cost = fields.Monetary(
        string='Coste de Transporte',
        currency_field='company_currency_id',
        tracking=True,
        help='Coste previsto del transporte'
    )
    transport_packages = fields.Integer(
        string='Número de Bultos',
        default=1,
        tracking=True,
        help='Cantidad de bultos/paquetes en el envío'
    )
    transport_weight = fields.Float(
        string='Peso Facturable (kg)',
        tracking=True,
        help='Peso total facturable del envío'
    )
    reconciliation_status = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('reconciled', 'Conciliado'),
            ('discrepancy', 'Discrepancia'),
        ],
        string='Estado de Conciliación',
        default='pending',
        tracking=True,
        help='Estado de conciliación con factura del transportista'
    )
    reconciliation_notes = fields.Text(
        string='Notas de Conciliación',
        help='Observaciones sobre la conciliación'
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )
