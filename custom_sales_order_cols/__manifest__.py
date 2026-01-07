# -*- coding: utf-8 -*-
{
    'name': "Sale Order Paid Column",

    'summary': "Añade columna de estado pagado en pedidos de venta",

    'description': """
Módulo que añade una columna para indicar si un pedido está pagado o no.
Incluye campo booleano editable y botón para marcar/desmarcar con registro en chatter.
    """,

    'author': "Tu Empresa",
    'website': "https://www.tuempresa.com",

    'category': 'Sales',
    'version': '17.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['sale', 'mail'],

    # always loaded
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}

