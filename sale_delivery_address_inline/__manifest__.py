# -*- coding: utf-8 -*-
{
    'name': 'Direcciones de Entrega Inline - Versión Básica',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Edición inline de direcciones de entrega en presupuestos',
    'description': """
Direcciones de Entrega Inline - Versión Básica
==============================================

Permite editar direcciones de entrega directamente desde el presupuesto.

Funcionalidades:
- Campo "Es Distribuidor" en partners
- Edición inline de direcciones en presupuestos
- Detección automática de distribuidores
- Campos adaptados a España
- Registro de cambios en el historial
- Gestión de permisos por grupos de usuario

Versión minimalista sin errores de compatibilidad.
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
    ],
    'assets': {
        'web.assets_backend': [
            'sale_delivery_address_inline/static/src/js/delivery_address_inline.js',
            'sale_delivery_address_inline/static/src/scss/delivery_address_inline.scss',
        ],
    },
    'demo': [
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
