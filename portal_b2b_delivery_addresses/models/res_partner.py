# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    """Extensión de res.partner para direcciones de entrega y etiquetas."""

    _inherit = "res.partner"

    # CAMPOS AÑADIDOS - Relaciones One2many para dashboard
    delivery_address_ids = fields.One2many(
        "delivery.address",
        "partner_id",
        string="Direcciones de Entrega",
        help="Direcciones de entrega del distribuidor",
    )

    distributor_label_ids = fields.One2many(
        "distributor.label",
        "partner_id",
        string="Etiquetas Cliente Final",
        help="Etiquetas de clientes finales del distribuidor",
    )

    def name_get(self):
        """
        Override para controlar cómo se muestra el nombre en campos Many2one.

        Para contactos de entrega B2B creados automáticamente, mostrar solo
        el alias sin el nombre del distribuidor padre.
        """
        result = []
        for partner in self:
            # Si es un contacto de entrega hijo de un distribuidor
            if (
                partner.type == "delivery"
                and partner.parent_id
                and partner.parent_id.is_distributor
                and partner.comment
                and "Dirección de entrega B2B:" in partner.comment
            ):
                # Extraer solo el alias de la dirección B2B del comment
                try:
                    alias = partner.comment.split("Dirección de entrega B2B: ")[1]
                    result.append((partner.id, alias))
                except (IndexError, AttributeError):
                    # Fallback al nombre normal si no se puede extraer
                    result.append((partner.id, partner.name))
            else:
                # Comportamiento estándar para otros contactos
                name = partner.name or ""
                if partner.parent_id and not partner.is_company:
                    name = f"{partner.parent_id.name}, {name}"
                result.append((partner.id, name))

        return result
