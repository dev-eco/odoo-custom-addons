# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class TransportReconciliationWizard(models.TransientModel):
    _name = 'transport.reconciliation.wizard'
    _description = 'Asistente de Conciliación de Transportes'

    transport_carrier_id = fields.Many2one(
        'res.partner',
        string='Transportista',
        required=True,
        domain=[('is_transport_carrier', '=', True)],
        help='Selecciona el transportista a conciliar'
    )
    month = fields.Selection(
        [(str(i), f'{i:02d}') for i in range(1, 13)],
        string='Mes',
        required=True,
        default=lambda self: str(datetime.now().month)
    )
    year = fields.Integer(
        string='Año',
        required=True,
        default=lambda self: datetime.now().year
    )
    wizard_line_ids = fields.One2many(
        'transport.reconciliation.wizard.line',
        'wizard_id',
        string='Líneas de Conciliación'
    )
    discrepancy_count = fields.Integer(
        string='Discrepancias Encontradas',
        compute='_compute_discrepancy_count'
    )

    @api.depends('wizard_line_ids.has_discrepancy')
    def _compute_discrepancy_count(self):
        for wizard in self:
            wizard.discrepancy_count = len(
                wizard.wizard_line_ids.filtered('has_discrepancy')
            )

    def action_reconcile(self):
        """Ejecuta la conciliación y actualiza estados"""
        for line in self.wizard_line_ids:
            if line.picking_id:
                line.picking_id.reconciliation_status = (
                    'discrepancy' if line.has_discrepancy else 'reconciled'
                )
                line.picking_id.reconciliation_notes = line.notes

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'transport.reconciliation.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class TransportReconciliationWizardLine(models.TransientModel):
    _name = 'transport.reconciliation.wizard.line'
    _description = 'Línea de Conciliación de Transportes'

    wizard_id = fields.Many2one(
        'transport.reconciliation.wizard',
        string='Asistente',
        ondelete='cascade'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Albarán',
        readonly=True
    )
    picking_number = fields.Char(
        related='picking_id.name',
        string='Número de Albarán',
        readonly=True
    )
    expected_cost = fields.Monetary(
        related='picking_id.transport_cost',
        string='Coste Previsto',
        currency_field='currency_id',
        readonly=True
    )
    invoiced_cost = fields.Monetary(
        string='Coste Facturado',
        currency_field='currency_id',
        help='Coste según factura del transportista'
    )
    has_discrepancy = fields.Boolean(
        string='Hay Discrepancia',
        compute='_compute_has_discrepancy',
        store=True
    )
    discrepancy_amount = fields.Monetary(
        string='Importe Discrepancia',
        currency_field='currency_id',
        compute='_compute_discrepancy_amount',
        store=True
    )
    notes = fields.Text(
        string='Notas'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.transport_carrier_id.company_id.currency_id',
        readonly=True
    )

    @api.depends('expected_cost', 'invoiced_cost')
    def _compute_has_discrepancy(self):
        for line in self:
            line.has_discrepancy = (
                line.expected_cost != line.invoiced_cost
            )

    @api.depends('expected_cost', 'invoiced_cost')
    def _compute_discrepancy_amount(self):
        for line in self:
            line.discrepancy_amount = (
                line.invoiced_cost - line.expected_cost
            )
