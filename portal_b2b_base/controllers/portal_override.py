# -*- coding: utf-8 -*-

import logging

from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalB2BOverride(CustomerPortal):
    """
    Override completo de las rutas estándar del portal de Odoo.

    Desactiva completamente las rutas /my para evitar conflictos
    y redirige a las rutas en español del Portal B2B.

    PRIORIDAD: 100 (máxima) para asegurar que se ejecute antes que
    las rutas estándar de CustomerPortal.
    """

    # ========== DESACTIVAR RUTAS ESTÁNDAR ==========

    @http.route(
        ["/my", "/my/home"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        priority=100,
    )
    def my_home_redirect(self, **kw):
        """
        Redirige /my y /my/home a /mi-portal.

        Redirección 301 (permanente) para que los navegadores
        cacheen la redirección.
        """
        _logger.info(
            f"Redirigiendo /my a /mi-portal para usuario {request.env.user.login}"
        )
        return request.redirect("/mi-portal", code=301)

    @http.route(
        ["/my/account"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        priority=100,
    )
    def my_account_redirect(self, **kw):
        """Redirige /my/account a /mi-cuenta."""
        _logger.info(
            f"Redirigiendo /my/account a /mi-cuenta para usuario {request.env.user.login}"
        )
        return request.redirect("/mi-cuenta", code=301)

    @http.route(
        ["/my/orders", "/my/orders/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        priority=100,
    )
    def my_orders_redirect(self, page=1, **kw):
        """Redirige /my/orders a /mis-pedidos."""
        query_string = request.httprequest.query_string.decode("utf-8")
        redirect_url = f"/mis-pedidos/page/{page}" if page > 1 else "/mis-pedidos"
        if query_string:
            redirect_url += f"?{query_string}"
        _logger.info(f"Redirigiendo /my/orders a {redirect_url}")
        return request.redirect(redirect_url, code=301)

    @http.route(
        ["/my/orders/<int:order_id>"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        priority=100,
    )
    def my_order_redirect(self, order_id, **kw):
        """Redirige /my/orders/<id> a /mis-pedidos/<id>."""
        query_string = request.httprequest.query_string.decode("utf-8")
        redirect_url = f"/mis-pedidos/{order_id}"
        if query_string:
            redirect_url += f"?{query_string}"
        return request.redirect(redirect_url, code=301)

    @http.route(
        ["/my/invoices", "/my/invoices/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        priority=100,
    )
    def my_invoices_redirect(self, page=1, **kw):
        """Redirige /my/invoices a /mis-facturas."""
        query_string = request.httprequest.query_string.decode("utf-8")
        redirect_url = f"/mis-facturas/page/{page}" if page > 1 else "/mis-facturas"
        if query_string:
            redirect_url += f"?{query_string}"
        return request.redirect(redirect_url, code=301)

    @http.route(
        ["/my/invoices/<int:invoice_id>"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        priority=100,
    )
    def my_invoice_redirect(self, invoice_id, **kw):
        """Redirige /my/invoices/<id> a /mis-facturas/<id>."""
        query_string = request.httprequest.query_string.decode("utf-8")
        redirect_url = f"/mis-facturas/{invoice_id}"
        if query_string:
            redirect_url += f"?{query_string}"
        return request.redirect(redirect_url, code=301)

    # ========== NO OVERRIDE _prepare_home_portal_values ==========
    # Dejar que CustomerPortal maneje esto normalmente
    # Las redirecciones se hacen en las rutas @http.route arriba
