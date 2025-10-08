{
    # Asegúrate de que esta sección existe y contiene 'mail'
    'depends': [
        'base', 
        'account', 
        'mail',
        'iap',
    ],
    # Asegúrate de que estos archivos están incluidos
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/document_types.xml',
        'data/ir_cron.xml',
        'views/api_documentation.xml',
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
}
