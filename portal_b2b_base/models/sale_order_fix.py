# -*- coding: utf-8 -*-

import logging

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def action_fix_portal_visibility_all(self):
        """
        Acción de servidor para recalcular portal_visible en TODOS los pedidos.
        Ejecutar una sola vez después del despliegue.
        """
        orders = self.search(
            [
                ("state", "!=", "cancel"),
                ("portal_visible", "=", False),
            ]
        )

        _logger.info(
            f"Iniciando recálculo de portal_visible para {len(orders)} pedidos..."
        )

        count_fixed = 0
        for order in orders:
            old_value = order.portal_visible
            # Forzar recálculo
            order._compute_portal_visible()

            if order.portal_visible != old_value:
                count_fixed += 1
                _logger.debug(
                    f"Pedido {order.name}: portal_visible cambiado de {old_value} a {order.portal_visible}"
                )

        _logger.info(f"Recálculo completado. {count_fixed} pedidos actualizados.")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Recálculo Completado"),
                "message": _("%s pedidos fueron actualizados.") % count_fixed,
                "type": "success",
                "sticky": False,
            },
        }

    def action_fix_portal_visibility_partner(self):
        """
        Recalcula portal_visible solo para pedidos de este partner.
        Ejecutar desde el formulario del partner.
        """
        self.ensure_one()
        partner = self if self._name == "res.partner" else self.partner_id

        orders = self.search(
            [
                ("partner_id", "child_of", [partner.commercial_partner_id.id]),
                ("state", "!=", "cancel"),
            ]
        )

        _logger.info(
            f"Recalculando portal_visible para {len(orders)} pedidos del partner {partner.name}..."
        )

        count_fixed = 0
        for order in orders:
            old_value = order.portal_visible
            order._compute_portal_visible()

            if order.portal_visible != old_value:
                count_fixed += 1

        _logger.info(f"Recálculo completado. {count_fixed} pedidos actualizados.")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Recálculo Completado"),
                "message": _("%s pedidos fueron actualizados para %s.")
                % (count_fixed, partner.name),
                "type": "success",
            },
        }

    @api.model
    def action_ensure_access_tokens_all(self):
        """
        Asegura que todos los pedidos tengan access_token.
        """
        orders = self.search(
            [
                ("access_token", "=", False),
                ("state", "!=", "cancel"),
            ]
        )

        _logger.info(f"Generando access_token para {len(orders)} pedidos...")

        for order in orders:
            if not order.access_token:
                order.access_token = order._generate_access_token()

        _logger.info(f"Tokens generados para {len(orders)} pedidos.")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Tokens Generados"),
                "message": _("%s pedidos ahora tienen access_token.") % len(orders),
                "type": "success",
            },
        }


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def action_ensure_access_tokens_all(self):
        """
        Asegura que todas las facturas tengan access_token.
        """
        invoices = self.search(
            [
                ("access_token", "=", False),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted"),
            ]
        )

        _logger.info(f"Generando access_token para {len(invoices)} facturas...")

        for invoice in invoices:
            if not invoice.access_token:
                invoice.access_token = self._generate_access_token()

        _logger.info(f"Tokens generados para {len(invoices)} facturas.")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Tokens Generados"),
                "message": _("%s facturas ahora tienen access_token.") % len(invoices),
                "type": "success",
            },
        }
