# -*- coding: utf-8 -*-
{
    'name': 'Direcciones de Entrega Multi-Empresa con Proyectos',
    'version': '17.0.2.0.1',
    'category': 'Sales',
    'summary': 'Gestión avanzada de direcciones de entrega para multi-empresa',
    'description': """
Direcciones de Entrega Multi-Empresa
=====================================

Sistema completo de gestión de direcciones de entrega para configuraciones multi-empresa.

Funcionalidades Principales:
----------------------------
✓ Edición inline de direcciones en presupuestos
✓ Soporte multi-empresa (aislamiento de datos)
✓ Direcciones temporales para proyectos únicos
✓ Direcciones permanentes para distribuidores
✓ Campos logísticos especializados
✓ Gestión de permisos por grupos
✓ Registro completo de cambios
✓ Validaciones avanzadas

Casos de Uso:
-------------
• Empresa A - Fabricación: Gestión de distribuidores y clientes directos
• Empresa B - Obra Civil: Direcciones temporales por proyecto
• Empresa C - Distribución: Mix de clientes recurrentes y ocasionales

Características Técnicas:
-------------------------
• Compatible con Odoo 17.0 Community Edition
• Sin modificaciones a core de Odoo
• Completamente desinstalable
• Localización España
• Multi-empresa nativo
    """,
    'author': 'EcoCaucho España',
    'website': 'https://www.ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'contacts',
        'web',
    ],
    'data': [
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'wizard/delivery_address_wizard_views.xml',
        'security/wizard_access.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_delivery_address_inline/static/src/js/delivery_address_inline.js',
            'sale_delivery_address_inline/static/src/scss/delivery_address_inline.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
