# -*- coding: utf-8 -*-
{
    'name': 'Sale Delivery Address Inline',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Edit delivery addresses inline in sale orders',
    'description': """
Sale Delivery Address Inline
============================

This module allows editing delivery addresses directly from the sale order form 
without having to open the partner form. Compatible with Odoo 17.0 syntax.

Features:
---------
* Edit delivery address inline from sale order
* Support for distributors with multiple delivery addresses  
* Delivery address selection for distributors
* Activity logging when addresses are modified
* Odoo 17.0 compatible (no attrs, uses new syntax)

Compatibility:
--------------
* Odoo 17.0 Community Edition
* Uses new view syntax (no attrs/states)
* Non-invasive: uses model inheritance and view xpath
""",
    'author': 'EcoCaucho Development Team',
    'website': 'https://www.ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'contacts',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
