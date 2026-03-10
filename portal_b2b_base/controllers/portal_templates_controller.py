# -*- coding: utf-8 -*-

import logging

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalTemplates(http.Controller):
    """Controlador para gestión de plantillas en el portal."""

    def _prepare_portal_layout_values(self):
        """Preparar valores seguros para el layout del portal."""
        return {
            "website": False,
            "preview_object": False,
            "editable": False,
            "translatable": False,
        }

    @http.route(["/mis-plantillas"], type="http", auth="user", methods=["GET"])
    def portal_my_templates(self, **kw):
        """
        Página de lista de plantillas del distribuidor.

        Returns:
            str: HTML de la página de plantillas
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener plantillas del distribuidor
        templates = request.env["sale.order.template"].search(
            [
                ("partner_id", "=", partner.id),
                ("active", "=", True),
            ],
            order="name asc",
        )

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "templates": templates,
            }
        )

        return request.render("portal_b2b_base.portal_my_templates", values)

    @http.route(
        ["/mis-plantillas/<int:template_id>"], type="http", auth="user", methods=["GET"]
    )
    def portal_template_detail(self, template_id, **kw):
        """
        Página de detalle de una plantilla.

        Args:
            template_id: ID de la plantilla

        Returns:
            str: HTML de la página de detalle
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener plantilla
        template = request.env["sale.order.template"].search(
            [
                ("id", "=", template_id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )

        if not template:
            return request.not_found()

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "template": template,
            }
        )

        return request.render("portal_b2b_base.portal_template_detail", values)

    @http.route(
        ["/mis-plantillas/<int:template_id>/usar"],
        type="http",
        auth="user",
        methods=["POST"],
    )
    def portal_use_template(self, template_id, **kw):
        """
        Usa una plantilla para crear un nuevo pedido.

        Args:
            template_id: ID de la plantilla

        Returns:
            redirect: Redirección al nuevo pedido
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener plantilla
        template = request.env["sale.order.template"].search(
            [
                ("id", "=", template_id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )

        if not template:
            return request.not_found()

        try:
            # Crear líneas del pedido
            order_lines = []
            for line in template.line_ids:
                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.quantity,
                            "product_uom": line.product_id.uom_id.id,
                        },
                    )
                )

            # Crear pedido
            order = request.env["sale.order"].create(
                {
                    "partner_id": partner.id,
                    "order_line": order_lines,
                    "note": template.notes or "",
                    "template_id": template.id,
                }
            )

            # Agregar dirección y etiqueta si están configuradas
            if template.delivery_address_id:
                order.delivery_address_id = template.delivery_address_id.id

            if template.distributor_label_id:
                order.distributor_label_id = template.distributor_label_id.id

            # Actualizar uso de la plantilla
            template.write(
                {
                    "use_count": template.use_count + 1,
                    "last_used_date": request.env["fields.Date"].today(),
                }
            )

            _logger.info(
                f"Pedido {order.name} creado desde plantilla {template.name} "
                f"por usuario {request.env.user.login}"
            )

            # ✅ LOGGING
            try:
                request.env["portal.audit.log"].log_action(
                    action="use_template",
                    model_name="sale.order.template",
                    record_id=template.id,
                    description=f"Plantilla {template.name} usada para crear pedido {order.name}",
                )
            except Exception as log_error:
                _logger.warning(f"Error logging action: {str(log_error)}")

            return request.redirect(f"/mis-pedidos/{order.id}")

        except Exception as e:
            _logger.error(f"Error al usar plantilla: {str(e)}")
            return request.redirect(f"/mis-plantillas/{template_id}")

    @http.route(
        ["/mis-plantillas/<int:template_id>/eliminar"],
        type="http",
        auth="user",
        methods=["POST"],
    )
    def portal_delete_template(self, template_id, **kw):
        """
        Elimina (archiva) una plantilla.

        Args:
            template_id: ID de la plantilla

        Returns:
            redirect: Redirección a lista de plantillas
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener plantilla
        template = request.env["sale.order.template"].search(
            [
                ("id", "=", template_id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )

        if not template:
            return request.not_found()

        try:
            template.write({"active": False})
            _logger.info(
                f"Plantilla {template.name} archivada por usuario {request.env.user.login}"
            )
        except Exception as e:
            _logger.error(f"Error al eliminar plantilla: {str(e)}")

        return request.redirect("/mis-plantillas")

    @http.route(
        ["/mis-pedidos/<int:order_id>/crear-plantilla"],
        type="http",
        auth="user",
        methods=["GET"],
    )
    def portal_create_template_from_order(self, order_id, **kw):
        """
        Página para crear una plantilla desde un pedido existente.

        Args:
            order_id: ID del pedido

        Returns:
            str: HTML del formulario
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener pedido
        order = request.env["sale.order"].search(
            [
                ("id", "=", order_id),
                ("partner_id", "=", partner.id),
            ],
            limit=1,
        )

        if not order:
            return request.not_found()

        values = self._prepare_portal_layout_values()
        values.update(
            {
                "order": order,
            }
        )

        return request.render(
            "portal_b2b_base.portal_create_template_from_order", values
        )

    @http.route(
        ["/mis-pedidos/<int:order_id>/crear-plantilla/submit"],
        type="json",
        auth="user",
        methods=["POST"],
    )
    def portal_create_template_from_order_submit(self, order_id, **kw):
        """
        API para crear plantilla desde pedido.

        Args:
            order_id: ID del pedido
            template_name: Nombre de la plantilla
            include_notes: Incluir notas
            include_delivery_address: Incluir dirección
            include_distributor_label: Incluir etiqueta

        Returns:
            dict: Resultado de la operación
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {"error": _("No autorizado")}

        try:
            # Obtener pedido
            order = request.env["sale.order"].search(
                [
                    ("id", "=", order_id),
                    ("partner_id", "=", partner.id),
                ],
                limit=1,
            )

            if not order:
                return {"error": _("Pedido no encontrado")}

            if not order.order_line:
                return {"error": _("El pedido no tiene líneas de productos")}

            # Obtener parámetros
            template_name = kw.get("template_name", "").strip()
            include_notes = kw.get("include_notes", False)
            include_delivery_address = kw.get("include_delivery_address", False)
            include_distributor_label = kw.get("include_distributor_label", False)

            if not template_name:
                return {"error": _("El nombre de la plantilla es obligatorio")}

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
            template = request.env["sale.order.template"].create(
                {
                    "name": template_name,
                    "partner_id": partner.id,
                    "line_ids": template_lines,
                    "notes": order.note if include_notes else "",
                    "delivery_address_id": (
                        order.delivery_address_id.id
                        if include_delivery_address
                        and hasattr(order, "delivery_address_id")
                        and order.delivery_address_id
                        else None
                    ),
                    "distributor_label_id": (
                        order.distributor_label_id.id
                        if include_distributor_label
                        and hasattr(order, "distributor_label_id")
                        and order.distributor_label_id
                        else None
                    ),
                }
            )

            _logger.info(
                f"Plantilla {template.name} creada desde pedido {order.name} "
                f"por usuario {request.env.user.login}"
            )

            return {
                "success": True,
                "redirect_url": f"/mis-plantillas/{template.id}",
            }

        except Exception as e:
            _logger.error(f"Error al crear plantilla: {str(e)}")
            return {"error": str(e)}
