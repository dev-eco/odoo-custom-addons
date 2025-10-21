# -*- coding: utf-8 -*-
{
    'name': 'Bulk Invoice Export',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Export multiple invoices to compressed archives',
    'description': """
Bulk Invoice Export
==================

Export customer and vendor invoices to compressed archives with smart
filename generation and multiple compression formats.

Features:
* Export from invoice list view or with custom filters
* Multiple compression formats: ZIP, TAR.GZ, TAR.BZ2
* Password protection for ZIP files
* Smart filename patterns
* Batch processing for performance
* Multi-company support
    """,
    'author': 'Your Name',
    'website': 'https://your-website.com',
    'email': 'your.email@domain.com',
    'license': 'LGPL-3',
    'depends': ['account', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_export_wizard.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
