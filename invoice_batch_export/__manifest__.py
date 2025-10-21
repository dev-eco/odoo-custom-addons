# -*- coding: utf-8 -*-
{
    'name': 'Invoice Batch Export',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Exportación masiva de facturas a ZIP con nombres descriptivos',
    'description': """
Invoice Batch Export - Odoo 17.0
==================================

Este módulo permite exportar múltiples facturas (clientes y proveedores) 
en un archivo ZIP con nombres de archivo descriptivos.

Características principales:
---------------------------
* Exportación masiva de facturas seleccionadas
* Filtros avanzados (fecha, tipo, estado, contacto)
* Nombres descriptivos automáticos para PDFs
* Manejo robusto de errores
* Interfaz intuitiva desde lista de facturas
* Compatible con multi-empresa
* Optimizado para grandes volúmenes

Casos de uso:
------------
* Envío a asesorías fiscales
* Respaldo documental
* Archivos por períodos
* Exportación por cliente/proveedor

Seguridad:
---------
* Respeta permisos de usuario de Odoo
* Solo usuarios con acceso a facturas pueden exportar
* Logs detallados de todas las operaciones

Rendimiento:
-----------
* Procesamiento por lotes para grandes volúmenes
* Generación eficiente de PDFs
* Compresión optimizada de archivos ZIP
* Indicadores de progreso y tiempo de procesamiento

    """,
    'author': 'EcoCaucho Development Team',
    'website': 'https://www.ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'web',
    ],
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        
        # Vistas
        'wizard/batch_export_wizard_views.xml',
    ],
    'demo': [],
    'assets': {},
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 100,
    
    # Metadatos adicionales para Odoo 17
    'external_dependencies': {
        'python': [],
    },
    
    # Configuración específica del módulo
    'pre_init_hook': None,
    'post_init_hook': None,
    'uninstall_hook': None,
    
    # Información de soporte
    'support': 'dev@ecocaucho.org',
    'maintainer': 'EcoCaucho Development Team',
    
    # Imágenes del módulo
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],
    
    # Configuración de desarrollo
    'development_status': 'Production/Stable',
    'maintainers': ['ecocaucho-dev'],
}
