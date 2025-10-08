{
    'name': 'Document Automation',
    'version': '1.0.0',
    'summary': 'Automatización integral para documentos empresariales',
    'description': """
        Sistema completo para automatizar la captura y procesamiento de documentos en Odoo 17 CE:
        
        - Recepción de documentos por email
        - Procesamiento de documentos escaneados
        - OCR integrado con Tesseract
        - Validación automática configurable
        - Compatible con facturas, tickets, albaranes y más
        - Soporte para escáneres en red local
    """,
    'category': 'Documents/Automation',
    'author': 'Ecocaucho',
    'website': 'https://ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'base', 
        'account', 
        'mail',
        'web',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/document_types.xml',
        'data/ir_cron.xml',
        'views/document_automation_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'document_automation/static/src/scss/document_dashboard.scss',
            'document_automation/static/src/js/document_widget.js',
        ],
    },
    'external_dependencies': {
        'python': ['pytesseract', 'pdf2image', 'pillow'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
