# -*- coding: utf-8 -*-
{
    'name': 'Mass Invoice Export to ZIP',
    'version': '17.0.1.0.0',
    'summary': 'Export multiple invoices to compressed archives with smart naming',
    'description': """
Mass Invoice Export to ZIP
=========================

Export multiple customer and vendor invoices to compressed archives with
intelligent file naming and multiple compression format support.

Key Features:
- Batch export of customer/vendor invoices and credit notes
- Smart filename patterns with variables (type, number, partner, date)
- Multiple compression formats (ZIP, 7-Zip, TAR.GZ) 
- Password protection for sensitive documents
- Multi-company support with per-company templates
- Advanced filters (date range, document type, status)
- Optimized batch processing for large volumes
- Comprehensive error handling and progress tracking
    """,
    'category': 'Accounting/Accounting',
    'author': '[TU_NOMBRE]',
    'maintainer': '[TU_NOMBRE]', 
    'website': 'https://tu-sitio-web.com',
    'email': 'tu.email@dominio.com',
    'license': 'LGPL-3',
    'sequence': 100,
    
    # Dependencies
    'depends': [
        'account',      # Core accounting functionality
        'base',         # Base Odoo framework
        'web',          # Web interface components
    ],
    
    # External Python dependencies  
    'external_dependencies': {
        'python': [
            'py7zr',        # 7-Zip compression support
        ],
    },
    
    # Data files (ORDEN CRÍTICO - modelos antes que vistas)
    'data': [
        # Security files (loaded first)
        'security/ir.model.access.csv',
        
        # Master data (after security, before views)
        'data/export_templates_data.xml',
        
        # Views (after models are loaded)
        'views/export_template_views.xml',
        'wizard/batch_export_wizard_views.xml',
        'views/res_company_views.xml',
        
        # Menu items (last)
        'views/menu_items.xml',
    ],
    
    # Module metadata
    'images': ['static/description/icon.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    
    # Hooks
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    
    # Version info
    'python_requires': '>=3.8',
}
