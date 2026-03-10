# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class SaleReturnRejectWizard(models.TransientModel):
    _name = "sale.return.reject.wizard"
    _description = "Asistente para Rechazar Devolución"

    return_id = fields.Many2one(
        "sale.return",
        string="Devolución",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get("active_id"),
    )

    rejection_reason = fields.Text(
        string="Motivo del Rechazo",
        required=True,
        help="Explique por qué se rechaza esta devolución",
    )

    def action_confirm_reject(self):
        """Confirma el rechazo de la devolución."""
        self.ensure_one()
        self.return_id.action_reject(self.rejection_reason)
        return {"type": "ir.actions.act_window_close"}
