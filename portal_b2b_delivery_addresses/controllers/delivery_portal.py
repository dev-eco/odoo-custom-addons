# -*- coding: utf-8 -*-

import logging

from odoo import _, http
from odoo.http import request
from werkzeug.utils import redirect as werkzeug_redirect

_logger = logging.getLogger(__name__)


class DeliveryPortalController(http.Controller):
    """Controlador específico para direcciones y etiquetas."""

    # ========== RUTAS DE DIRECCIONES ==========

    @http.route(
        ["/mis-direcciones", "/mis-direcciones/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_mis_direcciones(self, page=1, search=None, **kw):
        """Lista de direcciones de entrega del distribuidor."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Domain base
        domain = [("partner_id", "=", partner.id), ("active", "=", True)]

        # Búsqueda
        if search:
            domain += [
                "|",
                "|",
                ("name", "ilike", search),
                ("city", "ilike", search),
                ("street", "ilike", search),
            ]

        # Contar direcciones
        DeliveryAddress = request.env["delivery.address"]
        address_count = DeliveryAddress.search_count(domain)

        # Paginación
        from odoo.addons.portal.controllers.portal import pager as portal_pager

        pager = portal_pager(
            url="/mis-direcciones",
            url_args={"search": search},
            total=address_count,
            page=page,
            step=20,
        )

        # Obtener direcciones
        addresses = DeliveryAddress.search(
            domain, limit=20, offset=pager["offset"], order="is_default desc, name asc"
        )

        # Obtener países para el formulario
        countries = request.env["res.country"].search([])
        default_country = request.env.ref("base.es", raise_if_not_found=False)

        values = {
            "addresses": addresses,
            "page_name": "mis_direcciones",
            "pager": pager,
            "search": search,
            "countries": countries,
            "default_country": default_country,
            "states": [],
        }

        return request.render(
            "portal_b2b_delivery_addresses.portal_mis_direcciones", values
        )

    @http.route(["/mis-direcciones/crear"], type="http", auth="user", website=True)
    def portal_crear_direccion(self, redirect=None, **kw):
        """Formulario para crear nueva dirección."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener países
        countries = request.env["res.country"].search([])
        default_country = request.env.ref("base.es", raise_if_not_found=False)

        # Obtener provincias de España por defecto
        states = []
        if default_country:
            states = request.env["res.country.state"].search(
                [("country_id", "=", default_country.id)], order="name"
            )

        values = {
            "page_name": "crear_direccion",
            "countries": countries,
            "default_country": default_country,
            "states": states,
            "redirect_url": redirect or "/mis-direcciones",
        }

        return request.render(
            "portal_b2b_delivery_addresses.portal_crear_direccion", values
        )

    @http.route(
        ["/mis-direcciones/<int:address_id>/editar"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_editar_direccion(self, address_id, **kw):
        """Formulario para editar dirección."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener dirección
        address = request.env["delivery.address"].browse(address_id)

        if not address.exists() or address.partner_id != partner:
            return request.redirect("/mis-direcciones")

        # Obtener países
        countries = request.env["res.country"].search([])

        # Obtener provincias del país de la dirección
        states = []
        if address.country_id:
            states = request.env["res.country.state"].search(
                [("country_id", "=", address.country_id.id)], order="name"
            )

        values = {
            "address": address,
            "page_name": "editar_direccion",
            "countries": countries,
            "states": states,
        }

        return request.render(
            "portal_b2b_delivery_addresses.portal_editar_direccion", values
        )

    @http.route(
        ["/mis-direcciones/submit"],
        type="json",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def portal_direccion_submit(self, **post):
        """Procesa creación/edición de dirección."""
        try:
            partner = request.env.user.partner_id

            if not partner.is_distributor:
                return {"error": _("No autorizado")}

            # Validar campos requeridos
            required_fields = ["name", "street", "city", "zip", "country_id"]
            for field in required_fields:
                if not post.get(field):
                    return {"error": _("Faltan campos requeridos")}

            # Preparar valores
            vals = {
                "partner_id": partner.id,
                "name": post["name"],
                "street": post["street"],
                "street2": post.get("street2", ""),
                "city": post["city"],
                "zip": post["zip"],
                "country_id": int(post["country_id"]),
                "state_id": int(post["state_id"]) if post.get("state_id") else False,
                "contact_name": post.get("contact_name", ""),
                "contact_phone": post.get("contact_phone", ""),
                "require_appointment": post.get("require_appointment", False),
                "tail_lift_required": post.get("tail_lift_required", False),
                "delivery_notes": post.get("delivery_notes", ""),
            }

            # Crear o actualizar
            if post.get("address_id"):
                # Editar
                address = request.env["delivery.address"].browse(
                    int(post["address_id"])
                )
                if address.exists() and address.partner_id == partner:
                    address.sudo().write(vals)
                    message = _("Dirección actualizada correctamente")
                else:
                    return {"error": _("Dirección no encontrada")}
            else:
                # Crear
                address = request.env["delivery.address"].sudo().create(vals)
                message = _("Dirección creada correctamente")

            return {
                "success": True,
                "message": message,
                "redirect_url": "/mis-direcciones",
            }

        except Exception as e:
            _logger.error(f"Error al guardar dirección: {str(e)}", exc_info=True)
            return {"error": _("Error al guardar la dirección")}

    @http.route(
        ["/mis-direcciones/<int:address_id>/eliminar"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_direccion_eliminar(self, address_id, **kw):
        """Desactiva una dirección."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        address = request.env["delivery.address"].browse(address_id)

        if not address.exists() or address.partner_id != partner:
            return request.redirect("/mis-direcciones")

        try:
            address.sudo().write({"active": False})
            return werkzeug_redirect("/mis-direcciones?deleted=success", code=303)
        except Exception as e:
            _logger.error(f"Error al eliminar dirección: {str(e)}")
            return werkzeug_redirect("/mis-direcciones?error=delete_failed", code=303)

    @http.route(
        ["/mis-direcciones/<int:address_id>/por-defecto"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_direccion_por_defecto(self, address_id, **kw):
        """Marca una dirección como predeterminada."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        address = request.env["delivery.address"].browse(address_id)

        if not address.exists() or address.partner_id != partner:
            return request.redirect("/mis-direcciones")

        try:
            address.sudo().write({"is_default": True})
            return werkzeug_redirect("/mis-direcciones?default=success", code=303)
        except Exception as e:
            _logger.error(f"Error al marcar como predeterminada: {str(e)}")
            return werkzeug_redirect("/mis-direcciones?error=default_failed", code=303)

    # ========== RUTAS DE ETIQUETAS CLIENTE FINAL ==========

    @http.route(
        ["/mis-etiquetas", "/mis-etiquetas/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_mis_etiquetas(self, page=1, search=None, **kw):
        """Lista de etiquetas de cliente final."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Domain base
        domain = [("partner_id", "=", partner.id), ("active", "=", True)]

        # Búsqueda
        if search:
            domain += [
                "|",
                "|",
                ("name", "ilike", search),
                ("customer_name", "ilike", search),
                ("customer_reference", "ilike", search),
            ]

        # Contar etiquetas
        DistributorLabel = request.env["distributor.label"]
        label_count = DistributorLabel.search_count(domain)

        # Paginación
        from odoo.addons.portal.controllers.portal import pager as portal_pager

        pager = portal_pager(
            url="/mis-etiquetas",
            url_args={"search": search},
            total=label_count,
            page=page,
            step=20,
        )

        # Obtener etiquetas
        labels = DistributorLabel.search(
            domain, limit=20, offset=pager["offset"], order="name asc"
        )

        values = {
            "labels": labels,
            "label_count": label_count,
            "page_name": "mis_etiquetas",
            "pager": pager,
            "search": search,
        }

        return request.render(
            "portal_b2b_delivery_addresses.portal_mis_etiquetas", values
        )

    @http.route(["/mis-etiquetas/crear"], type="http", auth="user", website=True)
    def portal_crear_etiqueta(self, redirect=None, **kw):
        """Formulario para crear nueva etiqueta."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        values = {
            "label": None,
            "page_name": "crear_etiqueta",
            "redirect_url": redirect or "/mis-etiquetas",
        }

        return request.render(
            "portal_b2b_delivery_addresses.portal_crear_etiqueta", values
        )

    @http.route(
        ["/mis-etiquetas/<int:label_id>/editar"], type="http", auth="user", website=True
    )
    def portal_editar_etiqueta(self, label_id, **kw):
        """Formulario para editar etiqueta."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        # Obtener etiqueta
        label = request.env["distributor.label"].browse(label_id)

        if not label.exists() or label.partner_id != partner:
            return request.redirect("/mis-etiquetas")

        values = {
            "label": label,
            "page_name": "editar_etiqueta",
        }

        return request.render(
            "portal_b2b_delivery_addresses.portal_crear_etiqueta", values
        )

    @http.route(
        ["/mis-etiquetas/submit"], type="json", auth="user", methods=["POST"], csrf=True
    )
    def portal_etiqueta_submit(self, **post):
        """Procesa creación/edición de etiqueta."""
        try:
            partner = request.env.user.partner_id

            if not partner.is_distributor:
                return {"error": _("No autorizado")}

            # Validar campos requeridos
            if not post.get("name") or not post.get("customer_name"):
                return {"error": _("Faltan campos requeridos")}

            # Preparar valores
            vals = {
                "partner_id": partner.id,
                "name": post["name"],
                "customer_name": post["customer_name"],
                "customer_reference": post.get("customer_reference", ""),
                "tax_id": post.get("tax_id", ""),
                "contact_person": post.get("contact_person", ""),
                "customer_phone": post.get("customer_phone", ""),
                "customer_email": post.get("customer_email", ""),
                "customer_address": post.get("customer_address", ""),
                "payment_terms": post.get("payment_terms", ""),
                "delivery_instructions": post.get("delivery_instructions", ""),
                "print_on_delivery_note": post.get("print_on_delivery_note", False),
                "hide_company_info": post.get("hide_company_info", False),
                "notes": post.get("notes", ""),
            }

            # Crear o actualizar
            if post.get("label_id"):
                # Editar
                label = request.env["distributor.label"].browse(int(post["label_id"]))
                if label.exists() and label.partner_id == partner:
                    label.sudo().write(vals)
                    message = _("Etiqueta actualizada correctamente")
                else:
                    return {"error": _("Etiqueta no encontrada")}
            else:
                # Crear
                label = request.env["distributor.label"].sudo().create(vals)
                message = _("Etiqueta creada correctamente")

            return {
                "success": True,
                "message": message,
                "redirect_url": "/mis-etiquetas",
            }

        except Exception as e:
            _logger.error(f"Error al guardar etiqueta: {str(e)}", exc_info=True)
            return {"error": _("Error al guardar la etiqueta")}

    @http.route(
        ["/mis-etiquetas/<int:label_id>/eliminar"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        csrf=True,
    )
    def portal_etiqueta_eliminar(self, label_id, **kw):
        """Desactiva una etiqueta."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect("/mi-portal")

        label = request.env["distributor.label"].browse(label_id)

        if not label.exists() or label.partner_id != partner:
            return request.redirect("/mis-etiquetas")

        try:
            label.sudo().write({"active": False})
            return werkzeug_redirect("/mis-etiquetas?deleted=success", code=303)
        except Exception as e:
            _logger.error(f"Error al eliminar etiqueta: {str(e)}")
            return werkzeug_redirect("/mis-etiquetas?error=delete_failed", code=303)

    @http.route(
        ["/api/direcciones/<int:address_id>/editar"],
        type="json",
        auth="user",
        methods=["POST"],
    )
    def api_editar_direccion(self, address_id, **kw):
        """
        API JSON para editar dirección desde modal.

        Returns:
            dict: {success: bool, message: str, address: dict}
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {"success": False, "error": _("No autorizado")}

        try:
            # Obtener dirección
            address = request.env["delivery.address"].search(
                [
                    ("id", "=", address_id),
                    ("partner_id", "=", partner.id),
                ],
                limit=1,
            )

            if not address:
                return {"success": False, "error": _("Dirección no encontrada")}

            # Validar campos requeridos
            required_fields = ["name", "street", "city", "zip", "country_id"]
            for field in required_fields:
                if not kw.get(field):
                    return {
                        "success": False,
                        "error": _("Campo requerido faltante: %s") % field,
                    }

            # Actualizar dirección
            address.sudo().write(
                {
                    "name": kw.get("name"),
                    "street": kw.get("street"),
                    "street2": kw.get("street2", False),
                    "city": kw.get("city"),
                    "zip": kw.get("zip"),
                    "state_id": int(kw.get("state_id"))
                    if kw.get("state_id")
                    else False,
                    "country_id": int(kw.get("country_id")),
                    "contact_name": kw.get("contact_name", False),
                    "contact_phone": kw.get("contact_phone", False),
                    "require_appointment": kw.get("require_appointment", False),
                    "tail_lift_required": kw.get("tail_lift_required", False),
                    "delivery_notes": kw.get("delivery_notes", False),
                }
            )

            _logger.info(
                f"Dirección {address.name} editada inline por {request.env.user.login}"
            )

            # Retornar datos actualizados
            return {
                "success": True,
                "message": _("Dirección actualizada correctamente"),
                "address": {
                    "id": address.id,
                    "name": address.name,
                    "full_address": address.full_address,
                },
            }

        except Exception as e:
            _logger.error(f"Error al editar dirección inline: {str(e)}")
            return {"success": False, "error": str(e)}
