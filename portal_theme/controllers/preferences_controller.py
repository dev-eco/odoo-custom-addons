# -*- coding: utf-8 -*-

import logging
import json
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PreferencesController(http.Controller):
    """Controlador para gestionar preferencias de usuario."""

    @http.route('/api/preferencias/actualizar', type='json', auth='user', methods=['POST'])
    def update_preferences(self, **preferences):
        """
        Guarda preferencias del usuario en base de datos.

        Args:
            preferences (dict): Diccionario con preferencias

        Returns:
            dict: {'success': True} o {'error': 'mensaje'}
        """
        try:
            user = request.env.user

            # Validar preferencias permitidas
            allowed_keys = {
                'theme_mode', 'high_contrast', 'large_text',
                'reduce_motion', 'screen_reader_mode',
                'dashboard_layout', 'orders_per_page'
            }

            # Filtrar solo keys permitidas
            filtered_prefs = {
                k: v for k, v in preferences.items()
                if k in allowed_keys
            }

            if not filtered_prefs:
                return {'error': 'No hay preferencias válidas para guardar'}

            # Guardar en ir.config_parameter por usuario
            IrConfig = request.env['ir.config_parameter'].sudo()
            key_prefix = f'portal_preferences.user_{user.id}'

            IrConfig.set_param(
                f'{key_prefix}.data',
                json.dumps(filtered_prefs)
            )

            _logger.info(f"Preferencias guardadas para usuario {user.login}")

            return {'success': True}

        except Exception as e:
            _logger.error(f"Error guardando preferencias: {str(e)}", exc_info=True)
            return {'error': 'Error guardando preferencias'}

    @http.route('/api/preferencias/obtener', type='json', auth='user', methods=['GET'])
    def get_preferences(self):
        """
        Obtiene preferencias del usuario desde base de datos.

        Returns:
            dict: Diccionario con preferencias o {}
        """
        try:
            user = request.env.user
            IrConfig = request.env['ir.config_parameter'].sudo()
            key_prefix = f'portal_preferences.user_{user.id}'

            prefs_json = IrConfig.get_param(f'{key_prefix}.data', '{}')
            preferences = json.loads(prefs_json)

            return preferences

        except Exception as e:
            _logger.error(f"Error obteniendo preferencias: {str(e)}", exc_info=True)
            return {}
