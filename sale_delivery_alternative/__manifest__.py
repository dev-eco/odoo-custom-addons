# -*- coding: utf-8 -*-
{
    'name': 'Direcciones de Entrega Alternativas',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': 'Permite usar direcciones de entrega alternativas en pedidos',
    'description': """
        Gestión avanzada de direcciones de entrega para escenarios B2B:
        - Direcciones de entrega no vinculadas al cliente facturado
        - Soporte para distribuidores con entregas a clientes finales
        - Direcciones públicas compartidas entre clientes
    """,
    'author': 'Odoo Community',
    'website': 'https://www.odoo.com',
    'depends': ['sale_stock', 'delivery'],
    'data': [
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'wizard/create_alternative_address_views.xml',
        'report/stock_report_deliveryslip.xml',
        'data/migration_scripts.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
