# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    needs_review = fields.Boolean(
        string="Sin revisar",
        default=True,
        tracking=True,
        help="Indica si el presupuesto necesita revisión manual",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Asegurar que nuevos presupuestos se marcan como sin revisar."""
        for vals in vals_list:
            if "needs_review" not in vals:
                vals["needs_review"] = True
        return super().create(vals_list)

    def action_confirm(self):
        """Al confirmar, marcar como revisado automáticamente."""
        res = super().action_confirm()
        self.write({"needs_review": False})
        return res
