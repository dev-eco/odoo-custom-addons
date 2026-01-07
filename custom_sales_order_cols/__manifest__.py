# -*- coding: utf-8 -*-
{
    'name': "Sale Order Paid Column",

    'summary': "Añade columna de estado pagado en pedidos de venta basada en facturas",

    'description': """
Módulo que añade una columna para indicar si un pedido está pagado o no.
El estado se calcula automáticamente basándose en el estado de pago de las facturas relacionadas.
    """,

    'author': "Tu Empresa",
    'website': "https://www.tuempresa.com",

    'category': 'Sales',
    'version': '17.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['sale', 'mail', 'account'],

    # always loaded
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}

