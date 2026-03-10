# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderTemplateWizard(models.TransientModel):
    """Wizard para crear plantillas desde pedidos existentes."""

    _name = "sale.order.template.wizard"
    _description = "Crear Plantilla desde Pedido"

    order_id = fields.Many2one(
        "sale.order",
        string="Pedido",
        required=True,
        ondelete="cascade",
        help="Pedido del que se creará la plantilla",
    )

    template_name = fields.Char(
        string="Nombre de la Plantilla",
        required=True,
        help="Nombre descriptivo para la plantilla",
    )

    include_notes = fields.Boolean(
        string="Incluir Notas del Pedido",
        default=True,
        help="Copiar las notas del pedido a la plantilla",
    )

    include_delivery_address = fields.Boolean(
        string="Incluir Dirección de Entrega",
        default=True,
        help="Usar la dirección de entrega del pedido",
    )

    include_distributor_label = fields.Boolean(
        string="Incluir Cliente Final",
        default=True,
        help="Usar el cliente final del pedido",
    )

    @api.constrains("template_name")
    def _check_template_name(self) -> None:
        """Valida que el nombre no esté vacío."""
        for wizard in self:
            if not wizard.template_name or not wizard.template_name.strip():
                raise ValidationError(
                    _("El nombre de la plantilla no puede estar vacío.")
                )

    def action_create_template(self):
        """
        Crea la plantilla basada en el pedido.

        Returns:
            dict: Acción de redirección a la plantilla creada
        """
        self.ensure_one()

        order = self.order_id

        # Validar que el pedido tenga líneas
        if not order.order_line:
            raise ValidationError(_("El pedido no tiene líneas de productos."))

        # Crear líneas de plantilla
        template_lines = []
        for line in order.order_line:
            if line.product_id:
                template_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "quantity": line.product_uom_qty,
                            "sequence": line.sequence or 10,
                        },
                    )
                )

        # Crear plantilla
        template = self.env["sale.order.template"].create(
            {
                "name": self.template_name.strip(),
                "partner_id": order.partner_id.id,
                "line_ids": template_lines,
                "notes": order.note if self.include_notes else "",
                "delivery_address_id": (
                    order.delivery_address_id.id
                    if self.include_delivery_address
                    and hasattr(order, "delivery_address_id")
                    else None
                ),
                "distributor_label_id": (
                    order.distributor_label_id.id
                    if self.include_distributor_label
                    and hasattr(order, "distributor_label_id")
                    else None
                ),
            }
        )

        _logger.info(
            f"Plantilla {template.name} creada desde pedido {order.name} "
            f"por usuario {self.env.user.login}"
        )

        return {
            "type": "ir.actions.act_window",
            "name": template.name,
            "res_model": "sale.order.template",
            "res_id": template.id,
            "view_mode": "form",
            "target": "current",
        }
