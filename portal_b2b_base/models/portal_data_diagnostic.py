# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_diagnose_portal_orders(self):
        """
        Acción para diagnosticar pedidos no visibles en el portal.
        Ejecutar desde el partner del distribuidor.
        """
        self.ensure_one()

        if not self.user_ids:
            raise UserError(_("Este partner no tiene usuarios de portal asignados."))

        # Obtener todos los pedidos del partner (sin filtros)
        all_orders = self.env['sale.order'].search([
            ('partner_id', 'child_of', [self.commercial_partner_id.id]),
        ])

        # Pedidos que no son cancel
        active_orders = all_orders.filtered(lambda o: o.state != 'cancel')

        # Pedidos con portal_visible = False
        invisible_orders = active_orders.filtered(lambda o: not o.portal_visible)

        # Pedidos sin access_token
        orders_without_token = active_orders.filtered(lambda o: not o.access_token)

        # Facturas
        all_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('partner_id', 'child_of', [self.commercial_partner_id.id]),
        ])

        posted_invoices = all_invoices.filtered(lambda i: i.state == 'posted')
        invoices_without_token = posted_invoices.filtered(lambda i: not i.access_token)

        # Log detallado
        _logger.info("="*80)
        _logger.info(f"DIAGNÓSTICO PORTAL - Partner: {self.name} (ID: {self.id})")
        _logger.info(f"Commercial Partner ID: {self.commercial_partner_id.id}")
        _logger.info(f"Usuarios: {len(self.user_ids)}")
        _logger.info("-"*80)
        _logger.info(f"Total pedidos (incluye cancel): {len(all_orders)}")
        _logger.info(f"Pedidos activos (sin cancel): {len(active_orders)}")
        _logger.info(f"Pedidos con portal_visible=False: {len(invisible_orders)}")
        _logger.info(f"Pedidos sin access_token: {len(orders_without_token)}")
        _logger.info("-"*80)
        _logger.info(f"Total facturas: {len(all_invoices)}")
        _logger.info(f"Facturas posted: {len(posted_invoices)}")
        _logger.info(f"Facturas sin access_token: {len(invoices_without_token)}")
        _logger.info("="*80)

        if invisible_orders:
            _logger.info("PEDIDOS INVISIBLES:")
            for order in invisible_orders[:10]:  # Primeros 10
                _logger.info(f"  - {order.name} | Partner: {order.partner_id.name} (ID: {order.partner_id.id}) | "
                           f"State: {order.state} | User IDs: {len(order.partner_id.user_ids)}")

        # Crear mensaje para el usuario
        message = f"""
        <h3>Diagnóstico de Pedidos y Facturas - Portal B2B</h3>
        <p><strong>Partner:</strong> {self.name}</p>
        <p><strong>Commercial Partner ID:</strong> {self.commercial_partner_id.id}</p>

        <h4>Pedidos de Venta:</h4>
        <ul>
            <li>Total pedidos: {len(all_orders)}</li>
            <li>Pedidos activos (sin cancelados): {len(active_orders)}</li>
            <li><strong style="color: red;">Pedidos invisibles (portal_visible=False): {len(invisible_orders)}</strong></li>
            <li>Pedidos sin access_token: {len(orders_without_token)}</li>
        </ul>

        <h4>Facturas:</h4>
        <ul>
            <li>Total facturas: {len(all_invoices)}</li>
            <li>Facturas publicadas: {len(posted_invoices)}</li>
            <li>Facturas sin access_token: {len(invoices_without_token)}</li>
        </ul>

        <p><em>Revisa los logs del servidor para más detalles.</em></p>
        """

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Diagnóstico Completado'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
