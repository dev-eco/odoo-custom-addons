# -*- coding: utf-8 -*-
{
    'name': 'Exportación Masiva de Facturas',
    'version': '17.0.1.2.0',
    'category': 'Contabilidad/Localización',
    'summary': 'Exportación masiva de facturas a archivos comprimidos con funcionalidades avanzadas',
    'description': """
Exportación Masiva de Facturas - Versión Completa
================================================

Módulo completo para exportar múltiples facturas a archivos comprimidos con funcionalidades avanzadas.

Características Principales:
---------------------------
• Exportación masiva de facturas de clientes y proveedores
• Múltiples formatos de compresión (ZIP, TAR.GZ, TAR.BZ2)
• Protección con contraseña para archivos ZIP
• Patrones personalizables de nombres de archivo
• Organización automática por tipo de documento y partner
• Inclusión de archivos adjuntos (XML, otros PDFs)
• Historial completo de exportaciones para auditoría
• Procesamiento por lotes para mejor rendimiento
• Interfaz de usuario intuitiva y completamente en español
• Compatible con módulos OCA y terceros
• Validaciones de seguridad y permisos robustas

Funcionalidades Técnicas:
------------------------
• Generación PDF usando reportes estándar de Odoo
• Manejo seguro de errores y logging detallado
• Compatibilidad total con Odoo 17 Community Edition
• Soporte multi-empresa
• Filtros avanzados por fecha, partner, estado
• Descarga segura con tokens de autenticación
• Configuración global personalizable

Casos de Uso:
------------
• Envío masivo de facturas a clientes
• Respaldo periódico de documentos contables
• Auditorías y revisiones contables
• Integración con sistemas externos
• Cumplimiento normativo y archivo digital
    """,
    'author': 'Desarrollo Interno',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base_setup',
    ],
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        'security/export_security.xml',
        
        # Datos base
        'data/export_data.xml',
        
        # Vistas principales (orden importante para referencias)
        'views/export_history_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/bulk_export_wizard_views.xml',
        'views/menu_items.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_invoice_bulk_export/static/src/js/bulk_export.js',
            'account_invoice_bulk_export/static/src/scss/bulk_export.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'external_dependencies': {
        'python': [],
    },
}
