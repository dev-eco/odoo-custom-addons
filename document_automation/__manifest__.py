# __manifest__.py
{
    'name': 'Automatización Documental Avanzada',
    'version': '17.0.1.0.0',
    'category': 'Document Management',
    'summary': 'Sistema integral para procesamiento automático de documentos comerciales',
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'account',
        'purchase',
        'stock',
        'web',
        'queue_job',  # Para procesamiento asíncrono
    ],
    'external_dependencies': {
        'python': ['pytesseract', 'pdf2image', 'python-magic', 'invoice2data', 'pdfplumber', 'regex'],
        'bin': ['tesseract', 'pdftoppm'],
    },
    'data': [
        # Seguridad
        'security/document_automation_security.xml',
        'security/ir.model.access.csv',
        
        # Datos
        'data/ir_sequence_data.xml',
        'data/document_type_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        
        # Vistas
        'views/assets.xml',
        'views/document_automation_views.xml',
        'views/document_type_views.xml',
        'views/document_template_views.xml',
        'views/document_rule_views.xml',
        'views/res_config_settings_views.xml',
        
        # Wizards
        'wizard/document_import_views.xml',
    ],
    'demo': [
        # Datos de demo para pruebas
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
    'post_init_hook': 'post_init_hook',
    'assets': {
        'web.assets_backend': [
            'document_automation/static/src/js/document_preview.js',
            'document_automation/static/src/scss/document_automation.scss',
        ],
    },
    'sequence': 1,  # Prioridad de carga
}
