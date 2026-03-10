# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    """Extensión de plantilla de producto para portal B2B."""

    _inherit = "product.template"

    # ========== CAMPOS PARA DISPONIBILIDAD ==========

    available_qty_for_portal = fields.Float(
        string="Cantidad Disponible Portal",
        compute="_compute_available_qty_for_portal",
        store=False,
        help="Cantidad disponible para mostrar en el portal",
    )

    stock_status = fields.Selection(
        [
            ("in_stock", "En Stock"),
            ("low_stock", "Stock Bajo"),
            ("out_of_stock", "Sin Stock"),
            ("on_order", "Bajo Pedido"),
        ],
        string="Estado de Stock",
        compute="_compute_stock_status",
        store=False,
        help="Estado del stock para el portal",
    )

    estimated_restock_date = fields.Date(
        string="Fecha Estimada Reposición",
        compute="_compute_estimated_restock_date",
        store=False,
        help="Fecha estimada de llegada de stock",
    )

    alternative_product_ids = fields.Many2many(
        "product.template",
        "product_alternative_rel",
        "product_id",
        "alternative_id",
        string="Productos Alternativos",
        help="Productos alternativos sugeridos",
    )

    low_stock_threshold = fields.Float(
        string="Umbral Stock Bajo",
        default=10.0,
        help="Cantidad mínima para considerar stock bajo",
    )

    @api.depends("qty_available", "virtual_available")
    def _compute_available_qty_for_portal(self) -> None:
        """
        Calcula la cantidad disponible para mostrar en el portal.

        Usa qty_available (stock físico) como referencia principal.
        """
        for product in self:
            if product.type == "product":
                # Stock físico disponible
                product.available_qty_for_portal = max(product.qty_available, 0.0)
            else:
                # Servicios o consumibles siempre disponibles
                product.available_qty_for_portal = 9999.0

    @api.depends("available_qty_for_portal", "low_stock_threshold", "type")
    def _compute_stock_status(self) -> None:
        """
        Determina el estado del stock para mostrar en el portal.

        Estados:
        - in_stock: Stock suficiente (> umbral)
        - low_stock: Stock bajo (> 0 pero <= umbral)
        - out_of_stock: Sin stock (= 0)
        - on_order: Producto bajo pedido (route específica)
        """
        for product in self:
            if product.type != "product":
                product.stock_status = "in_stock"
                continue

            # Verificar si es bajo pedido
            if product._is_make_to_order():
                product.stock_status = "on_order"
                continue

            qty = product.available_qty_for_portal
            threshold = product.low_stock_threshold

            if qty <= 0:
                product.stock_status = "out_of_stock"
            elif qty <= threshold:
                product.stock_status = "low_stock"
            else:
                product.stock_status = "in_stock"

    def _is_make_to_order(self) -> bool:
        """
        Verifica si el producto es bajo pedido (Make To Order).

        Returns:
            bool: True si tiene ruta MTO configurada
        """
        self.ensure_one()

        try:
            # Buscar ruta MTO
            mto_route = self.env.ref(
                "stock.route_warehouse0_mto", raise_if_not_found=False
            )
            if mto_route and mto_route in self.route_ids:
                return True
        except Exception as e:
            _logger.debug(f"Error verificando ruta MTO: {str(e)}")

        return False

    @api.depends("qty_available")
    def _compute_estimated_restock_date(self) -> None:
        """
        Calcula la fecha estimada de reposición basada en órdenes de compra.

        Busca la fecha más próxima de llegada en purchase.order.line
        para productos sin stock.
        """
        for product in self:
            if product.available_qty_for_portal > 0:
                product.estimated_restock_date = False
                continue

            # Buscar órdenes de compra pendientes
            purchase_lines = self.env["purchase.order.line"].search(
                [
                    ("product_id.product_tmpl_id", "=", product.id),
                    (
                        "order_id.state",
                        "in",
                        ["draft", "sent", "to approve", "purchase"],
                    ),
                    ("date_planned", "!=", False),
                ],
                order="date_planned asc",
                limit=1,
            )

            if purchase_lines:
                product.estimated_restock_date = purchase_lines[0].date_planned.date()
            else:
                # Si no hay órdenes, estimar 7 días
                product.estimated_restock_date = fields.Date.today() + timedelta(days=7)

    def get_stock_info_for_portal(self) -> dict:
        """
        Obtiene información completa de stock para el portal.

        Returns:
            dict: Información de stock formateada
        """
        self.ensure_one()

        return {
            "product_id": self.id,
            "product_name": self.name,
            "available_qty": float(self.available_qty_for_portal),
            "stock_status": self.stock_status,
            "stock_status_label": dict(self._fields["stock_status"].selection).get(
                self.stock_status
            ),
            "estimated_restock_date": (
                self.estimated_restock_date.strftime("%d/%m/%Y")
                if self.estimated_restock_date
                else None
            ),
            "low_stock_threshold": float(self.low_stock_threshold),
            "is_make_to_order": self._is_make_to_order(),
            "alternative_products": (
                [
                    {
                        "id": alt.id,
                        "name": alt.name,
                        "default_code": alt.default_code,
                        "list_price": float(alt.list_price),
                        "available_qty": float(alt.available_qty_for_portal),
                    }
                    for alt in self.alternative_product_ids
                ]
                if self.alternative_product_ids
                else []
            ),
        }
