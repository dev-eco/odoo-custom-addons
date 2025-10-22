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

Versión minimalista sin errores de compatibilidad.
""",
    'author': 'EcoCaucho España',
    'website': 'https://www.ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
