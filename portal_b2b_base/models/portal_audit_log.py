# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PortalAuditLog(models.Model):
    """Registro de auditoría de acciones en el portal B2B."""

    _name = "portal.audit.log"
    _description = "Registro de Auditoría Portal B2B"
    _order = "create_date desc"
    _rec_name = "action"

    partner_id = fields.Many2one(
        "res.partner", string="Usuario", required=True, ondelete="cascade", index=True
    )

    user_id = fields.Many2one(
        "res.users",
        string="Usuario Sistema",
        required=True,
        default=lambda self: self.env.user,
    )

    action = fields.Char(string="Acción", required=True, index=True)

    description = fields.Text(string="Descripción")

    model_name = fields.Char(string="Modelo", index=True)

    record_id = fields.Integer(string="ID Registro")

    old_values = fields.Text(
        string="Valores Anteriores", help="JSON con valores antes del cambio"
    )

    new_values = fields.Text(
        string="Valores Nuevos", help="JSON con valores después del cambio"
    )

    ip_address = fields.Char(string="Dirección IP")

    user_agent = fields.Char(string="User Agent")

    @api.model
    def log_action(
        self,
        action,
        description=None,
        model_name=None,
        record_id=None,
        old_values=None,
        new_values=None,
    ):
        """
        Registra una acción en el log de auditoría.

        Args:
            action: Nombre de la acción
            description: Descripción detallada
            model_name: Nombre del modelo afectado
            record_id: ID del registro afectado
            old_values: Valores anteriores (dict)
            new_values: Valores nuevos (dict)

        Returns:
            portal.audit.log: Registro creado
        """
        import json

        from odoo.http import request as http_request

        partner = self.env.user.partner_id

        # Obtener IP y User Agent si está disponible
        ip_address = None
        user_agent = None

        try:
            if http_request:
                ip_address = http_request.httprequest.remote_addr
                user_agent = http_request.httprequest.headers.get("User-Agent", "")
        except Exception:
            pass

        log = self.create(
            {
                "partner_id": partner.id,
                "user_id": self.env.user.id,
                "action": action,
                "description": description,
                "model_name": model_name,
                "record_id": record_id,
                "old_values": json.dumps(old_values) if old_values else None,
                "new_values": json.dumps(new_values) if new_values else None,
                "ip_address": ip_address,
                "user_agent": user_agent[:255] if user_agent else None,
            }
        )

        _logger.info(f"Auditoría: {action} por {partner.name} (IP: {ip_address})")

        return log

    @api.model
    def get_recent_activity(self, partner_id, limit=20):
        """
        Obtiene actividad reciente de un distribuidor.

        Args:
            partner_id: ID del partner
            limit: Número máximo de registros

        Returns:
            list: Lista de actividades formateadas
        """
        import json

        logs = self.search(
            [
                ("partner_id", "=", partner_id),
            ],
            limit=limit,
            order="create_date desc",
        )

        return [
            {
                "id": log.id,
                "action": log.action,
                "description": log.description,
                "model_name": log.model_name,
                "record_id": log.record_id,
                "create_date": log.create_date.strftime("%d/%m/%Y %H:%M:%S"),
                "ip_address": log.ip_address,
            }
            for log in logs
        ]
