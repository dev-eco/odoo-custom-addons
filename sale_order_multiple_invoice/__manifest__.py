{
    'name': 'Facturación Consolidada de Pedidos de Venta',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Crear facturas consolidadas a partir de múltiples pedidos de venta',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'AGPL-3',
    'depends': [
        'sale',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}
