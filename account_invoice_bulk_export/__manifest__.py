# -*- coding: utf-8 -*-
{
    'name': 'Exportación Masiva de Facturas',
    'version': '17.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Exporta múltiples facturas a archivos comprimidos con PDFs reales',
    'description': """
Exportación Masiva de Facturas Mejorada
========================================

Exporta facturas de clientes y proveedores a archivos comprimidos con 
generación real de PDFs, nombres inteligentes y múltiples formatos.

Características Principales:
----------------------------
* Exportación masiva desde lista de facturas o con filtros personalizados
* **Generación real de PDFs** usando el motor de reportes de Odoo
* Múltiples formatos de compresión: ZIP, TAR.GZ, TAR.BZ2
* Protección con contraseña para archivos ZIP
* Patrones inteligentes de nombres de archivo
* **Organización en carpetas por tipo de documento**
* **Inclusión opcional de archivos adjuntos**
* Procesamiento por lotes para mejor rendimiento
* Soporte multi-empresa completo
* **Barra de progreso durante la exportación**
* **Vista previa de facturas a exportar**
* **Estadísticas detalladas del proceso**
* **Registro de auditoría de exportaciones**
* **Interfaz completamente en castellano**
* Validaciones de seguridad mejoradas
* Manejo robusto de errores con logs detallados

Casos de Uso:
-------------
* Envío de facturas a asesorías fiscales
* Backup periódico de documentación
* Archivos para auditorías
* Entrega de documentación a clientes
* Gestión documental empresarial

Seguridad:
----------
* Validación de permisos por factura
* Sanitización de nombres de archivo
* Límites de procesamiento por lotes
* Control de acceso basado en grupos
* Registro de auditoría de exportaciones

Requisitos:
-----------
* Odoo 17.0
* Módulo 'account' instalado
* Permisos de usuario de contabilidad

    """,
    'author': 'EcoCaucho Development Team',
    'website': 'https://www.ecocaucho.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'base',
        'mail',  # Para attachments
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/export_security.xml',
        'views/export_history_views.xml',
        'wizard/bulk_export_wizard_views.xml',
        'views/menu_items.xml',
        'data/export_data.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 0.00,
    'currency': 'EUR',
}
