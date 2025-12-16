# -*- coding: utf-8 -*-
{
    'name': 'Bulk Invoice Export - Simplified',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Simple bulk export of invoices to ZIP',
    'description': """
Simple Bulk Invoice Export
=========================

Export multiple invoices to a ZIP file using Odoo's standard PDF generation.

Features:
- Export posted invoices to ZIP
- Uses standard Odoo invoice reports
- Simple and reliable
    """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_export_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
