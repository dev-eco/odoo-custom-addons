# -*- coding: utf-8 -*-

import json
import logging

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestPreferences(TransactionCase):
    """Tests para gestión de preferencias de usuario"""

    def setUp(self):
        super().setUp()
        self.user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "testuser@portal.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )

    def test_01_save_preferences(self):
        """Test guardar preferencias de usuario"""
        preferences = {
            "theme_mode": "dark",
            "high_contrast": True,
            "dashboard_layout": "list",
        }

        IrConfig = self.env["ir.config_parameter"].sudo()
        key = f"portal_preferences.user_{self.user.id}.data"
        IrConfig.set_param(key, json.dumps(preferences))

        # Verificar que se guardó
        saved = IrConfig.get_param(key)
        self.assertEqual(json.loads(saved), preferences)

    def test_02_get_preferences(self):
        """Test obtener preferencias de usuario"""
        preferences = {"theme_mode": "light"}

        IrConfig = self.env["ir.config_parameter"].sudo()
        key = f"portal_preferences.user_{self.user.id}.data"
        IrConfig.set_param(key, json.dumps(preferences))

        # Recuperar
        saved_json = IrConfig.get_param(key, "{}")
        saved = json.loads(saved_json)

        self.assertEqual(saved["theme_mode"], "light")

    def test_03_default_preferences(self):
        """Test preferencias por defecto cuando no existen"""
        IrConfig = self.env["ir.config_parameter"].sudo()
        key = f"portal_preferences.user_{self.user.id}.data"

        # No debería existir
        saved_json = IrConfig.get_param(key, "{}")
        saved = json.loads(saved_json)

        self.assertEqual(saved, {})

    def test_04_update_preferences(self):
        """Test actualizar preferencias existentes"""
        # Guardar preferencias iniciales
        initial_prefs = {"theme_mode": "light", "large_text": False}
        IrConfig = self.env["ir.config_parameter"].sudo()
        key = f"portal_preferences.user_{self.user.id}.data"
        IrConfig.set_param(key, json.dumps(initial_prefs))

        # Actualizar
        updated_prefs = {"theme_mode": "dark", "large_text": True}
        IrConfig.set_param(key, json.dumps(updated_prefs))

        # Verificar
        saved_json = IrConfig.get_param(key)
        saved = json.loads(saved_json)

        self.assertEqual(saved["theme_mode"], "dark")
        self.assertTrue(saved["large_text"])
