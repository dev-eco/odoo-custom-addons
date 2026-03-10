# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PortalNotification(models.Model):
    """Notificaciones para usuarios del portal B2B."""

    _name = "portal.notification"
    _description = "Notificación Portal B2B"
    _order = "create_date desc"
    _rec_name = "title"

    partner_id = fields.Many2one(
        "res.partner",
        string="Destinatario",
        required=True,
        ondelete="cascade",
        index=True,
    )

    title = fields.Char(string="Título", required=True)

    message = fields.Text(string="Mensaje", required=True)

    notification_type = fields.Selection(
        [
            ("info", "Información"),
            ("success", "Éxito"),
            ("warning", "Advertencia"),
            ("danger", "Error/Urgente"),
        ],
        string="Tipo",
        default="info",
        required=True,
    )

    is_read = fields.Boolean(string="Leída", default=False, index=True)

    read_date = fields.Datetime(string="Fecha Lectura", readonly=True)

    action_url = fields.Char(
        string="URL Acción", help="URL a la que redirigir al hacer clic"
    )

    related_model = fields.Char(string="Modelo Relacionado")

    related_id = fields.Integer(string="ID Relacionado")

    expires_at = fields.Datetime(
        string="Expira", help="Fecha de expiración de la notificación"
    )

    def action_mark_read(self):
        """Marca la notificación como leída."""
        self.ensure_one()
        self.write(
            {
                "is_read": True,
                "read_date": fields.Datetime.now(),
            }
        )

    @api.model
    def create_notification(
        self,
        partner_id,
        title,
        message,
        notification_type="info",
        action_url=None,
        related_model=None,
        related_id=None,
    ):
        """
        Crea una notificación para un distribuidor.

        Args:
            partner_id: ID del partner destinatario
            title: Título de la notificación
            message: Mensaje de la notificación
            notification_type: Tipo de notificación
            action_url: URL de acción (opcional)
            related_model: Modelo relacionado (opcional)
            related_id: ID del registro relacionado (opcional)

        Returns:
            portal.notification: Notificación creada
        """
        notification = self.create(
            {
                "partner_id": partner_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "action_url": action_url,
                "related_model": related_model,
                "related_id": related_id,
            }
        )

        _logger.info(f"Notificación creada para {partner_id}: {title}")

        return notification

    @api.model
    def get_unread_count(self, partner_id):
        """
        Obtiene el número de notificaciones no leídas.

        Args:
            partner_id: ID del partner

        Returns:
            int: Número de notificaciones no leídas
        """
        return self.search_count(
            [
                ("partner_id", "=", partner_id),
                ("is_read", "=", False),
            ]
        )

    @api.model
    def get_recent_notifications(self, partner_id, limit=10):
        """
        Obtiene las notificaciones recientes.

        Args:
            partner_id: ID del partner
            limit: Número máximo de notificaciones

        Returns:
            list: Lista de notificaciones formateadas
        """
        notifications = self.search(
            [
                ("partner_id", "=", partner_id),
            ],
            limit=limit,
            order="create_date desc",
        )

        return [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": n.is_read,
                "create_date": n.create_date.strftime("%d/%m/%Y %H:%M"),
                "action_url": n.action_url or "#",
            }
            for n in notifications
        ]
