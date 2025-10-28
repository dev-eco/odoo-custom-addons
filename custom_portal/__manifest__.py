# -*- coding: utf-8 -*-
{
    'name': 'Portal de Distribuidores Ecocaucho',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Portal personalizado para distribuidores de Ecocaucho',
    'description': """
Portal de Distribuidores Ecocaucho
==================================
Este módulo implementa un portal web personalizado para los distribuidores de Ecocaucho,
permitiéndoles gestionar albaranes y pedidos desde portal.ecocaucho.org.
    """,
    'author': 'Ecocaucho',
    'website': 'https://www.ecocaucho.org',
    'depends': [
        'base',
        'website',
        'portal',
        'sale',
        'stock',
    ],
    'data': [
        'security/distributor_security.xml',
        'security/ir.model.access.csv',
        'views/distributor_portal_templates.xml',
        'views/distributor_views.xml',
        'views/distributor_delivery_views.xml',
        'views/menu_views.xml',
        'data/website_data.xml',
    ],
    'demo': [
        'data/distributor_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
