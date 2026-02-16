# -*- coding: utf-8 -*-
{
    'name': 'Portal B2B Base',
    'version': '17.0.1.0.1',
    'category': 'Sales/Sales',
    'summary': 'Portal B2B para distribuidores - Módulo base con gestión de pedidos y control de crédito',
    'description': """
Portal B2B Base
===============

Módulo núcleo del portal B2B genérico para distribuidores.

Funcionalidades principales:
-----------------------------
* Gestión completa de pedidos desde portal
* Control de límite de crédito en tiempo real
* Catálogo de productos con búsqueda avanzada
* Creación y repetición de pedidos
* Consulta de facturas
* Gestión de cuenta de usuario
* Notificaciones de disponibilidad de stock
* Validación de crédito disponible antes de confirmar pedidos
* Asignación automática de estado distribuidor basada en grupos
* Menú de navegación mejorado
* Dashboard con información de crédito
* Exportación de pedidos a Excel
* Historial de precios de productos

Características técnicas:
-------------------------
* Compatible con Odoo 17 Community Edition
* Responsive Bootstrap 5
* API JSON para autocompletado
* Paginación y filtros avanzados
* Seguridad por record rules
* Multi-empresa compatible
* Campos computed para sincronización automática

Rutas del portal:
-----------------
* /mi-portal - Dashboard principal del portal
* /mis-pedidos - Lista de pedidos
* /mis-pedidos/<id> - Detalle de pedido
* /crear-pedido - Formulario nuevo pedido
* /mis-pedidos/exportar - Exportar pedidos a Excel
* /mis-facturas - Lista de facturas
* /mi-cuenta - Gestión de cuenta
* /api/productos/buscar - API búsqueda productos
* /api/productos/<id>/stock - API información stock
* /api/productos/<id>/historial-precios - API historial precios

Flujo de configuración:
-----------------------
1. Crear contacto en Contactos
2. Ir a Ventas > Distribuidores B2B
3. Abrir el distribuidor
4. Hacer clic en "Crear Usuario Portal"
5. Configurar límite de crédito y tarifa
6. El usuario recibe credenciales por email

Autor: Generic
Licencia: LGPL-3
    """,
    'author': 'Generic',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'portal',
        'sale',
        'stock',
        'account',
        'website',
        'mail',
    ],
    'data': [
        # Seguridad (PRIMERO)
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Reglas de productos (SIN referencias a campos nuevos)
        'security/product_security.xml',

        # Configuración del sitio web
        'data/website_config.xml',
        'data/email_templates.xml',
        'data/mail_template_data.xml',
        'data/sequences.xml',
        'data/cron.xml',

        # Wizards (ANTES de las vistas que los usan)
        'wizard/sale_order_template_wizard_views.xml',
        'wizard/sale_return_reject_wizard_views.xml',

        # Vistas backend
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_template_views.xml',
        'views/portal_message_views.xml',
        'views/sale_return_views.xml',
        'views/res_config_settings_views.xml',

        # Templates portal
        'views/portal_templates.xml',
        'views/portal_menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Estilos
            'portal_b2b_base/static/src/scss/portal.scss',

            # Scripts del portal
            'portal_b2b_base/static/src/js/portal.js',
            'portal_b2b_base/static/src/js/product_grid.js',
            'portal_b2b_base/static/src/js/returns.js',
        ],
    },
    'external_dependencies': {
        'python': ['xlsxwriter'],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
