{
    'name': 'Descarga Individual de Facturas',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Permite descargar facturas individualmente, incluso cuando se seleccionan varias',
    'author': 'Tu Nombre/Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'wizards/download_wizard_views.xml',
    ],
    'images': [
        'static/description/icon.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
