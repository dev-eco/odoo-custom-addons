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
        'queue_job',
    ],
    # Añadir definición de assets aquí
    'assets': {
        'web.assets_backend': [
#            '/document_automation/static/src/js/document_preview.js',
            '/document_automation/static/src/scss/document_automation.scss',
            '/document_automation/static/src/components/document_preview/document_preview.js',
            '/document_automation/static/src/components/document_preview/document_preview.xml',
#            '/document_automation/static/src/xml/document_preview.xml',
        ],
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
        # Eliminar 'views/assets.xml' de esta lista
        'views/document_automation_views.xml',
        'views/document_type_views.xml',
        'views/document_template_views.xml',
        'views/document_rule_views.xml',
        'views/res_config_settings_views.xml',
        'views/document_templates.xml',
        
        # Wizards
        'wizard/document_import_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
