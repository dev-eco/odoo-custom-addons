# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PortalUserPreferences(models.Model):
    """Preferencias de usuario del portal B2B."""
    
    _name = 'portal.user.preferences'
    _description = 'Preferencias Usuario Portal B2B'
    _rec_name = 'user_id'
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        related='user_id.partner_id',
        store=True,
        readonly=True
    )
    
    # Tema
    theme_mode = fields.Selection([
        ('light', 'Claro'),
        ('dark', 'Oscuro'),
        ('auto', 'Automático'),
    ], string='Modo de Tema', default='light')
    
    # Accesibilidad
    high_contrast = fields.Boolean(
        string='Alto Contraste',
        default=False,
        help='Activa modo de alto contraste para mejor visibilidad'
    )
    
    large_text = fields.Boolean(
        string='Texto Grande',
        default=False,
        help='Aumenta el tamaño del texto'
    )
    
    reduce_motion = fields.Boolean(
        string='Reducir Animaciones',
        default=False,
        help='Reduce las animaciones para usuarios sensibles al movimiento'
    )
    
    screen_reader_mode = fields.Boolean(
        string='Modo Lector de Pantalla',
        default=False,
        help='Optimiza la interfaz para lectores de pantalla'
    )
    
    # Idioma y localización
    language = fields.Selection(
        selection='_get_languages',
        string='Idioma',
        default='es_ES'
    )
    
    timezone = fields.Selection(
        selection='_get_timezones',
        string='Zona Horaria',
        default='Europe/Madrid'
    )
    
    # Notificaciones
    email_notifications = fields.Boolean(
        string='Notificaciones por Email',
        default=True
    )
    
    browser_notifications = fields.Boolean(
        string='Notificaciones del Navegador',
        default=False
    )
    
    # Dashboard
    dashboard_layout = fields.Selection([
        ('cards', 'Tarjetas'),
        ('list', 'Lista'),
        ('compact', 'Compacto'),
    ], string='Layout Dashboard', default='cards')
    
    show_credit_widget = fields.Boolean(
        string='Mostrar Widget de Crédito',
        default=True
    )
    
    # Configuración de tabla
    orders_per_page = fields.Integer(
        string='Pedidos por Página',
        default=20,
        help='Número de pedidos a mostrar por página'
    )
    
    default_order_sort = fields.Selection([
        ('date', 'Fecha'),
        ('name', 'Referencia'),
        ('amount', 'Importe'),
        ('state', 'Estado'),
    ], string='Ordenación por Defecto', default='date')
    
    @api.model
    def _get_languages(self):
        """Obtiene idiomas disponibles."""
        return [
            ('es_ES', 'Español'),
            ('en_US', 'English'),
            ('fr_FR', 'Français'),
            ('de_DE', 'Deutsch'),
        ]
    
    @api.model
    def _get_timezones(self):
        """Obtiene zonas horarias disponibles."""
        return [
            ('Europe/Madrid', 'Madrid (CET/CEST)'),
            ('Europe/London', 'London (GMT/BST)'),
            ('Europe/Paris', 'Paris (CET/CEST)'),
            ('Europe/Berlin', 'Berlin (CET/CEST)'),
            ('America/New_York', 'New York (EST/EDT)'),
            ('America/Los_Angeles', 'Los Angeles (PST/PDT)'),
        ]
    
    @api.model
    def get_user_preferences(self, user_id=None):
        """
        Obtiene las preferencias del usuario actual o especificado.
        
        Args:
            user_id: ID del usuario (opcional, usa usuario actual si no se especifica)
        
        Returns:
            dict: Preferencias del usuario
        """
        if not user_id:
            user_id = self.env.user.id
        
        preferences = self.search([('user_id', '=', user_id)], limit=1)
        
        if not preferences:
            # Crear preferencias por defecto
            preferences = self.create({'user_id': user_id})
        
        return {
            'theme_mode': preferences.theme_mode,
            'high_contrast': preferences.high_contrast,
            'large_text': preferences.large_text,
            'reduce_motion': preferences.reduce_motion,
            'screen_reader_mode': preferences.screen_reader_mode,
            'language': preferences.language,
            'timezone': preferences.timezone,
            'email_notifications': preferences.email_notifications,
            'browser_notifications': preferences.browser_notifications,
            'dashboard_layout': preferences.dashboard_layout,
            'show_credit_widget': preferences.show_credit_widget,
            'orders_per_page': preferences.orders_per_page,
            'default_order_sort': preferences.default_order_sort,
        }
    
    @api.model
    def update_user_preferences(self, preferences_data, user_id=None):
        """
        Actualiza las preferencias del usuario.
        
        Args:
            preferences_data: Diccionario con las preferencias a actualizar
            user_id: ID del usuario (opcional)
        
        Returns:
            bool: True si se actualizó correctamente
        """
        if not user_id:
            user_id = self.env.user.id
        
        preferences = self.search([('user_id', '=', user_id)], limit=1)
        
        if not preferences:
            preferences_data['user_id'] = user_id
            preferences = self.create(preferences_data)
        else:
            preferences.write(preferences_data)
        
        _logger.info(f"Preferencias actualizadas para usuario {user_id}")
        
        return True
    
    def get_css_classes(self):
        """
        Genera clases CSS basadas en las preferencias.
        
        Returns:
            str: Clases CSS separadas por espacios
        """
        self.ensure_one()
        
        classes = []
        
        # Tema
        if self.theme_mode == 'dark':
            classes.append('theme-dark')
        elif self.theme_mode == 'auto':
            classes.append('theme-auto')
        else:
            classes.append('theme-light')
        
        # Accesibilidad
        if self.high_contrast:
            classes.append('high-contrast')
        
        if self.large_text:
            classes.append('large-text')
        
        if self.reduce_motion:
            classes.append('reduce-motion')
        
        if self.screen_reader_mode:
            classes.append('screen-reader-mode')
        
        # Dashboard
        classes.append(f'dashboard-{self.dashboard_layout}')
        
        return ' '.join(classes)
