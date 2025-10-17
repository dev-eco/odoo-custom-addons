# -*- coding: utf-8 -*-
# © 2025 Tu Empresa - https://www.tuempresa.com
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

{
    'name': 'Facturas Personalizadas',
    'version': '17.0.1.0.0',
    'summary': 'Plantillas personalizadas para facturas en Odoo',
    'description': """
        Este módulo proporciona plantillas personalizadas para facturas,
        añadiendo campos útiles como referencia del cliente, pedidos relacionados,
        e instrucciones especiales.
        
        Características:
        - Plantilla de factura completamente personalizada
        - Campos adicionales para más información relevante
        - Formato optimizado para mejor presentación
        - Diseño limpio y profesional
    """,
    'category': 'Accounting/Accounting',
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/report_facturas_templates.xml',
        'reports/invoice_reports.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'plantilla_factura/static/src/scss/invoice_report_style.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
}
