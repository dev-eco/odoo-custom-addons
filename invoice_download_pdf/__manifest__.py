{
    'name': 'Descarga Individual de Facturas',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Permite descargar facturas individualmente, incluso cuando se seleccionan varias',
    'author': 'Ecocaucho SL',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'wizards/download_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
