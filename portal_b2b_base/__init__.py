# -*- coding: utf-8 -*-

from . import controllers, models, wizard


def post_init_hook(cr, registry):
    """
    Hook ejecutado después de instalar/actualizar el módulo.
    Genera access_tokens para pedidos y facturas existentes.
    """
    import logging

    from odoo import SUPERUSER_ID, api

    _logger = logging.getLogger(__name__)

    env = api.Environment(cr, SUPERUSER_ID, {})

    # Generar tokens en pedidos
    _logger.info("Post-init: Generando access_tokens en pedidos...")
    env["sale.order"]._ensure_access_tokens()

    # Generar tokens en facturas
    _logger.info("Post-init: Generando access_tokens en facturas...")
    env["account.move"]._ensure_access_tokens()

    _logger.info("Post-init hook completado.")
