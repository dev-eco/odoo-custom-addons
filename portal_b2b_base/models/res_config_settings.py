# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    return_notification_email = fields.Char(
        string="Email Notificaciones Devolución",
        config_parameter="portal_b2b_base.return_notification_email",
        default="pedidos@ecocaucho.info",
        help="Email donde se enviarán las notificaciones de nuevas devoluciones",
    )
