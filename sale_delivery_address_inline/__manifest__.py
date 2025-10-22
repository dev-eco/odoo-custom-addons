# -*- coding: utf-8 -*-
{
    'name': 'Sale Delivery Address Inline',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Edit delivery addresses inline in sale orders without opening partner form',
    'description': """
Sale Delivery Address Inline
============================

This module allows editing delivery addresses directly from the sale order form 
without having to open the partner form. It includes special handling for distributors 
who may have multiple delivery addresses.

Features:
---------
* Edit delivery address inline from sale order
* Support for distributors with multiple delivery addresses  
* Delivery address selection dropdown for distributors
* Create new delivery addresses on the fly
* Activity logging in chatter when addresses are modified
* Security: only Sales Managers can edit after order confirmation
* Multi-company and multi-language support
* Non-invasive: uses model inheritance and view xpath

Compatibility:
--------------
* Odoo 17.0 Community Edition
* Compatible with OCA sale-workflow modules
* No core modifications required

Usage:
------
1. Open a sale order
2. Click on delivery address section
3. Edit fields inline or select from dropdown (distributors)
4. Changes are automatically saved and logged

For distributors:
-----------------
1. Mark partners as distributors via checkbox
2. Access dropdown of alternative delivery addresses
3. Create new addresses specific to orders
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
        'data/demo_data.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    },
}
