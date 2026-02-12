# -*- coding: utf-8 -*-
{
    # Theme information
    'name': "Portal B2B Theme",
    'summary': "Tema personalizado para Portal B2B de distribuidores",
    'description': """
Portal B2B Theme
================

Tema visual optimizado para el portal B2B de distribuidores.

Características:
----------------
* Diseño moderno y profesional
* Responsive (móvil, tablet, desktop)
* Colores corporativos personalizables
* Componentes reutilizables
* Optimizado para rendimiento
* Compatible con Odoo 17
* Integración con Bootstrap 5
* Animaciones suaves
* Accesibilidad mejorada (WCAG 2.1)

Paleta de colores:
------------------
* Primary: #0066CC (Azul corporativo)
* Success: #28a745 (Verde)
* Danger: #dc3545 (Rojo)
* Warning: #ffc107 (Amarillo)
* Info: #17a2b8 (Cian)
* Secondary: #6c757d (Gris)

Tipografía:
-----------
* Fuente principal: 'Inter', sans-serif
* Fuente secundaria: 'Roboto', sans-serif
* Tamaños responsivos

Componentes incluidos:
----------------------
* Cards con sombras y hover effects
* Botones con animaciones
* Formularios estilizados
* Tablas responsive
* Alertas personalizadas
* Badges y etiquetas
* Breadcrumbs
* Paginación
* Modales
* Tooltips

Snippets disponibles:
---------------------
* Hero section
* Feature cards
* Testimonials
* Call to action
* Statistics
* Contact forms
    """,
    'category': 'Theme/Creative',
    'version': '17.0.1.0.0',
    'depends': [
        'website',
        'portal',
        'portal_b2b_base',
    ],

    # Data files
    'data': [
        'views/layout.xml',
        'views/portal_menu.xml',
        'views/options.xml',
        'views/snippets.xml',
    ],

    # Assets - ORDEN CRÍTICO
    'assets': {
        'web.assets_frontend': [
            # ========== FIX MÍNIMO ==========
            'portal_theme/static/src/js/portal_fix.js',
            
            # ========== SCSS ==========
            'portal_theme/static/src/scss/primary_variables.scss',
            'portal_theme/static/src/scss/bootstrap_overrides.scss',
            'portal_theme/static/src/scss/portal_layout.scss',
            'portal_theme/static/src/scss/portal_components.scss',
            'portal_theme/static/src/scss/custom.scss',
            
            # ========== JAVASCRIPT ==========
            'portal_theme/static/src/js/portal_theme.js',
            'portal_theme/static/src/js/animations.js',
        ],
    },

    # Author information
    'author': "Tu Empresa",
    'website': "https://www.tuempresa.com",
    'license': 'LGPL-3',
    
    # Technical
    'installable': True,
    'application': False,
    'auto_install': False,
}
