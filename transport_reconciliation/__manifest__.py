# -*- coding: utf-8 -*-
{
    'name': 'Transport Reconciliation',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Control y conciliación de transportes con agencias externas',
    'description': """
        Registra transportes realizados con transportistas externos y concilia
        contra facturas mensuales para detectar discrepancias.
        
        Funcionalidades:
        - Campos adicionales en albaranes: coste previsto, bultos, peso facturable
        - Estado de conciliación por envío
        - Wizard mensual de conciliación contra facturas proveedor
        - Reporte de diferencias para revisión
        - Castellanizado y adaptado a flujos españoles
    """,
    'author': 'EcoCaucho',
    'website': 'https://www.ecocaucho.org',
    'depends': [
        'stock',
        'purchase',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/transport_carrier_data.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_line_views.xml',
        'wizards/transport_reconciliation_wizard_views.xml',
        'views/menus.xml',
        'reports/transport_reconciliation_report.xml',
        'reports/transport_reconciliation_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

