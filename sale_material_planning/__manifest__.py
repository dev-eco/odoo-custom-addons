{
    'name': 'Planificación de Material para Ventas',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Filtros y vistas para planificar salida de material',
    'description': """
        Módulo para facilitar la toma de decisiones sobre qué material debe salir cada día,
        mostrando referencias de productos y unidades en pedidos de clientes específicos.
    """,
    'author': 'EcoCaucho',
    'depends': ['sale_management', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_material_planning_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_material_planning/static/src/scss/style.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
