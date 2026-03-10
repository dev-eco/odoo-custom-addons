# -*- coding: utf-8 -*-

import secrets

from odoo import models


class PortalAccessMixin(models.AbstractModel):
    """Mixin para gestión de access_token en modelos del portal."""

    _name = "portal.access.mixin"
    _description = "Portal Access Token Mixin"

    @staticmethod
    def _generate_access_token():
        """Genera un token de acceso único y seguro."""
        return secrets.token_urlsafe(32)
