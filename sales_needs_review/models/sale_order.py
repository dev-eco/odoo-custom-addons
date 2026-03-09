# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    needs_review = fields.Boolean(
        string="Sin revisar",
        default=True,
        tracking=True,
        help="Indica si el presupuesto necesita revisión manual",
    )

    def action_confirm(self):
        """Al confirmar, marcar como revisado automáticamente."""
        res = super().action_confirm()
        self.write({"needs_review": False})
        return res
