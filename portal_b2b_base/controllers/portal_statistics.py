# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from odoo import _, fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalStatistics(http.Controller):
    """Controlador de estadísticas para portal B2B."""

    @http.route(["/mis-estadisticas"], type="http", auth="user", website=True)
    def portal_statistics(self, period="month", **kw):
        """Dashboard de estadísticas del distribuidor."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Calcular período
        today = fields.Date.today()

        if period == "week":
            period_start = today - timedelta(days=7)
            period_name = "Última Semana"
        elif period == "month":
            period_start = today.replace(day=1)
            period_name = "Este Mes"
        elif period == "quarter":
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            period_start = today.replace(month=quarter_month, day=1)
            period_name = "Este Trimestre"
        elif period == "year":
            period_start = today.replace(month=1, day=1)
            period_name = "Este Año"
        else:
            period_start = today - timedelta(days=30)
            period_name = "Últimos 30 Días"

        period_end = today

        # Buscar o crear estadísticas
        stats = (
            request.env["distributor.statistics"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", partner.id),
                    ("period_start", "=", period_start),
                    ("period_end", "=", period_end),
                ],
                limit=1,
            )
        )

        if not stats:
            stats = (
                request.env["distributor.statistics"]
                .sudo()
                .create(
                    {
                        "partner_id": partner.id,
                        "period_start": period_start,
                        "period_end": period_end,
                    }
                )
            )

        # Obtener datos adicionales
        orders_by_state = request.env["sale.order"].read_group(
            domain=[
                ("partner_id", "=", partner.id),
                ("date_order", ">=", period_start),
                ("date_order", "<=", period_end),
            ],
            fields=["state"],
            groupby=["state"],
        )

        values = {
            "stats": stats,
            "period": period,
            "period_name": period_name,
            "period_start": period_start,
            "period_end": period_end,
            "orders_by_state": orders_by_state,
            "page_name": "estadisticas",
        }

        return request.render("portal_b2b_base.portal_statistics", values)

    @http.route(
        ["/api/estadisticas/grafico"], type="json", auth="user", methods=["POST"]
    )
    def api_statistics_chart(self, chart_type="orders", period="month", **kw):
        """API para obtener datos de gráficos."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {"error": _("No autorizado")}

        try:
            # Calcular período
            today = fields.Date.today()

            if period == "week":
                period_start = today - timedelta(days=7)
                days = 7
            elif period == "month":
                period_start = today.replace(day=1)
                days = (today - period_start).days + 1
            elif period == "year":
                period_start = today.replace(month=1, day=1)
                days = (today - period_start).days + 1
            else:
                period_start = today - timedelta(days=30)
                days = 30

            # Generar datos según tipo de gráfico
            if chart_type == "orders":
                data = self._get_orders_by_day(partner.id, period_start, today, days)
            elif chart_type == "revenue":
                data = self._get_revenue_by_day(partner.id, period_start, today, days)
            elif chart_type == "products":
                data = self._get_top_products(partner.id, period_start, today)
            else:
                return {"error": _("Tipo de gráfico no válido")}

            return {"success": True, "data": data}

        except Exception as e:
            _logger.error(f"Error obteniendo datos de gráfico: {str(e)}")
            return {"error": str(e)}

    def _get_orders_by_day(self, partner_id, start_date, end_date, days):
        """Obtiene número de pedidos por día."""
        labels = []
        data = []

        current_date = start_date
        while current_date <= end_date:
            count = request.env["sale.order"].search_count(
                [
                    ("partner_id", "=", partner_id),
                    ("date_order", ">=", current_date),
                    ("date_order", "<", current_date + timedelta(days=1)),
                ]
            )

            labels.append(current_date.strftime("%d/%m"))
            data.append(count)
            current_date += timedelta(days=1)

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Pedidos",
                    "data": data,
                    "backgroundColor": "rgba(0, 102, 204, 0.2)",
                    "borderColor": "rgba(0, 102, 204, 1)",
                    "borderWidth": 2,
                }
            ],
        }

    def _get_revenue_by_day(self, partner_id, start_date, end_date, days):
        """Obtiene ingresos por día."""
        labels = []
        data = []

        current_date = start_date
        while current_date <= end_date:
            orders = request.env["sale.order"].search(
                [
                    ("partner_id", "=", partner_id),
                    ("date_order", ">=", current_date),
                    ("date_order", "<", current_date + timedelta(days=1)),
                    ("state", "in", ["sale", "done"]),
                ]
            )

            total = sum(orders.mapped("amount_total"))

            labels.append(current_date.strftime("%d/%m"))
            data.append(float(total))
            current_date += timedelta(days=1)

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Ingresos (€)",
                    "data": data,
                    "backgroundColor": "rgba(40, 167, 69, 0.2)",
                    "borderColor": "rgba(40, 167, 69, 1)",
                    "borderWidth": 2,
                }
            ],
        }

    def _get_top_products(self, partner_id, start_date, end_date):
        """Obtiene productos más vendidos."""
        order_lines = request.env["sale.order.line"].search(
            [
                ("order_id.partner_id", "=", partner_id),
                ("order_id.date_order", ">=", start_date),
                ("order_id.date_order", "<=", end_date),
                ("order_id.state", "in", ["sale", "done"]),
            ]
        )

        product_qty = {}
        for line in order_lines:
            if line.product_id:
                product_qty[line.product_id.name] = (
                    product_qty.get(line.product_id.name, 0) + line.product_uom_qty
                )

        # Top 10
        top_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]

        return {
            "labels": [p[0] for p in top_products],
            "datasets": [
                {
                    "label": "Cantidad",
                    "data": [float(p[1]) for p in top_products],
                    "backgroundColor": [
                        "rgba(0, 102, 204, 0.7)",
                        "rgba(40, 167, 69, 0.7)",
                        "rgba(255, 193, 7, 0.7)",
                        "rgba(220, 53, 69, 0.7)",
                        "rgba(23, 162, 184, 0.7)",
                        "rgba(108, 117, 125, 0.7)",
                        "rgba(111, 66, 193, 0.7)",
                        "rgba(253, 126, 20, 0.7)",
                        "rgba(32, 201, 151, 0.7)",
                        "rgba(13, 110, 253, 0.7)",
                    ],
                }
            ],
        }
