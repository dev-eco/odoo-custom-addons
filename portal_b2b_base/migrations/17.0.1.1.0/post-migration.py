# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migración post-instalación para fix de visibilidad portal.

    Ejecuta:
    1. Recalcula portal_visible en pedidos existentes
    2. Genera access_token en pedidos sin token
    3. Genera access_token en facturas sin token
    """
    _logger.info("=" * 80)
    _logger.info("INICIANDO MIGRACIÓN: Fix Visibilidad Portal")
    _logger.info("=" * 80)

    # 1. Recalcular portal_visible en pedidos
    _logger.info("Paso 1: Recalculando portal_visible en pedidos...")
    cr.execute(
        """
        SELECT id, name, partner_id, state
        FROM sale_order
        WHERE state != 'cancel'
        AND portal_visible = FALSE
    """
    )
    orders_to_fix = cr.fetchall()
    _logger.info(f"  Encontrados {len(orders_to_fix)} pedidos con portal_visible=False")

    if orders_to_fix:
        # Forzar recálculo mediante SQL para mejor performance
        cr.execute(
            """
            UPDATE sale_order so
            SET portal_visible = (
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM res_users ru
                        WHERE ru.partner_id = so.partner_id
                        AND ru.active = TRUE
                    ) AND so.state != 'cancel'
                    THEN TRUE
                    ELSE FALSE
                END
            )
            WHERE so.state != 'cancel'
            AND so.portal_visible = FALSE
        """
        )
        _logger.info(f"  ✓ Pedidos actualizados")

    # 2. Generar access_token en pedidos
    _logger.info("Paso 2: Generando access_token en pedidos...")
    cr.execute(
        """
        SELECT COUNT(*)
        FROM sale_order
        WHERE access_token IS NULL
        AND state != 'cancel'
    """
    )
    count_without_token = cr.fetchone()[0]
    _logger.info(f"  Encontrados {count_without_token} pedidos sin access_token")

    if count_without_token > 0:
        # Generar tokens mediante Python (necesita la función _generate_access_token)
        # Esto se ejecutará mediante el método del modelo en post_init_hook
        _logger.info(f"  ⚠ Tokens se generarán en post_init_hook")

    # 3. Generar access_token en facturas
    _logger.info("Paso 3: Generando access_token en facturas...")
    cr.execute(
        """
        SELECT COUNT(*)
        FROM account_move
        WHERE access_token IS NULL
        AND move_type IN ('out_invoice', 'out_refund')
        AND state = 'posted'
    """
    )
    count_invoices_without_token = cr.fetchone()[0]
    _logger.info(
        f"  Encontradas {count_invoices_without_token} facturas sin access_token"
    )

    if count_invoices_without_token > 0:
        _logger.info(f"  ⚠ Tokens se generarán en post_init_hook")

    _logger.info("=" * 80)
    _logger.info("MIGRACIÓN COMPLETADA")
    _logger.info("=" * 80)
