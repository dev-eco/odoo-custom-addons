# -*- coding: utf-8 -*-
"""
Manifest del Módulo Invoice Batch Export

El archivo __manifest__.py es el "certificado de nacimiento" de cualquier módulo
de Odoo. Contiene toda la metadata que Odoo necesita para:

1. Identificar el módulo (nombre, versión, autor)
2. Entender sus dependencias (qué otros módulos necesita)
3. Saber qué archivos cargar (datos, vistas, seguridad)
4. Configurar su comportamiento (aplicación, auto-instalable, etc.)

Este archivo se lee ANTES de cargar cualquier código Python o XML del módulo,
por lo que debe estar bien estructurado y contener información precisa.

Estructura del Manifest
=======================
Los campos más importantes son:

- name: El nombre visible en la lista de aplicaciones
- version: Debe seguir el patrón X.Y.Z.W.R donde X.Y es la versión de Odoo
- depends: Lista de módulos que DEBEN estar instalados antes que este
- data: Lista de archivos XML/CSV a cargar en orden específico
- installable: Si False, el módulo no aparecerá disponible para instalar
- application: Si True, aparece como aplicación principal en el App Store
- auto_install: Si True, se instala automáticamente cuando sus dependencias están presentes

Orden de Carga de Datos
=======================
El orden en la lista 'data' es CRÍTICO porque:
- Los modelos se deben cargar antes que las vistas que los usan
- Los datos base se deben cargar antes que los datos que los referencian
- Los permisos se deben cargar antes que las acciones que los requieren

Convención de Versionado
=======================
Usamos el patrón: 17.0.1.0.0 donde:
- 17.0: Versión de Odoo (siempre debe coincidir)
- 1: Versión mayor del módulo (cambios breaking/incompatibles)
- 0: Versión menor (nuevas características compatibles)
- 0: Versión de parche (correcciones de bugs)
"""

{
    # METADATOS BÁSICOS
    # ================
    'name': 'Invoice Batch Export',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    
    # Resumen corto que aparece en la lista de aplicaciones
    # Debe ser descriptivo pero conciso (máximo ~80 caracteres)
    'summary': 'Exportación masiva de facturas en múltiples formatos comprimidos',
    
    # Descripción detallada en formato reStructuredText
    # Esta descripción aparece cuando el usuario abre el módulo para ver detalles
    'description': """
        Invoice Batch Export - Exportación Masiva Inteligente
        =====================================================
        
        Sistema avanzado de exportación de facturas diseñado para asesorías 
        contables y empresas que necesitan gestionar grandes volúmenes de 
        documentación fiscal.
        
        🚀 **Características Principales**
        
        * **Múltiples formatos de compresión**: ZIP, 7-Zip, TAR.GZ
        * **Nomenclatura inteligente**: Plantillas personalizables por empresa
        * **Procesamiento por lotes**: Optimizado para miles de facturas
        * **Filtrado avanzado**: Por fecha, estado, tipo de documento
        * **Seguridad empresarial**: Control de acceso granular
        * **Métricas de rendimiento**: Tiempo de procesamiento y ratios de compresión
        
        📊 **Optimizado para Alto Rendimiento**
        
        * Procesamiento en lotes configurable para uso eficiente de memoria
        * Algoritmos de compresión optimizados según preferencias velocidad/tamaño
        * Caché inteligente de PDFs para evitar regeneración innecesaria
        * Limpieza automática de archivos temporales
        
        🏢 **Perfecto para Asesorías Fiscales**
        
        * Plantillas de nomenclatura por empresa
        * Filtros específicos para períodos fiscales
        * Separación automática por tipo de documento
        * Integración transparente con el flujo de trabajo existente
        
        🔧 **Fácil Configuración e Integración**
        
        * No modifica modelos core de Odoo (instalación/desinstalación limpia)
        * Configuración automática según facturas preseleccionadas
        * Compatible con instalaciones multi-empresa
        * Traducciones completas al español
    """,
    
    # INFORMACIÓN DEL DESARROLLADOR
    # ============================
    'author': 'Tu Nombre',
    'website': 'https://tuwebsite.com',
    'license': 'LGPL-3',
    
    # DEPENDENCIAS DEL MÓDULO
    # ======================
    # Lista de módulos de Odoo que DEBEN estar instalados antes de este módulo
    'depends': [
        'account',      # Módulo de contabilidad (facturas, asientos contables)
        'base_setup',   # Configuraciones base (para configuraciones por empresa)
    ],
    
    # DEPENDENCIAS EXTERNAS
    # ====================
    # Bibliotecas Python que deben estar instaladas en el sistema
    # Odoo verificará estas dependencias durante la instalación
    'external_dependencies': {
        'python': ['py7zr'],  # Para soporte de compresión 7-Zip ultra eficiente
    },
    
    # ARCHIVOS DE DATOS A CARGAR
    # ==========================
    # ORDEN CRÍTICO: Los archivos se cargan en el orden especificado aquí
    'data': [
        # 1. SEGURIDAD (siempre primero)
        # Los permisos deben cargarse antes que cualquier otra cosa
        'security/ir.model.access.csv',      # Permisos básicos de acceso a modelos
        'security/batch_export_security.xml', # Reglas de seguridad avanzadas
        
        # 2. DATOS BASE
        # Datos que otros archivos pueden referenciar
        'data/export_templates.xml',         # Plantillas predefinidas de exportación
        
        # 3. VISTAS DE MODELOS
        # Vistas para los modelos persistentes que hemos creado
        'views/export_template_views.xml',   # Interfaz para gestionar plantillas
        'views/res_company_views.xml',       # Extensiones de vista de empresa
        
        # 4. WIZARDS
        # Los wizards van después porque pueden usar los modelos anteriores
        'wizard/batch_export_wizard_views.xml', # Interfaz del wizard principal
        
        # 5. HERENCIAS DE VISTAS (al final)
        # Las herencias van al final para asegurar que las vistas base existan
        'views/account_move_views.xml',      # Botones añadidos a facturas
    ],
    
    # DATOS DE DEMOSTRACIÓN
    # ====================
    # Se cargan solo si Odoo se instala con --demo o --init con datos demo
    'demo': [
        'demo/demo_export_templates.xml',    # Plantillas de ejemplo para testing
    ],
    
    # CONFIGURACIÓN DEL MÓDULO
    # ========================
    'installable': True,    # El módulo está listo para instalación
    'application': False,   # No es una aplicación principal (es una extensión)
    'auto_install': False,  # No se instala automáticamente
    
    # HOOKS DE CICLO DE VIDA
    # =====================
    # Funciones Python que se ejecutan en momentos específicos del ciclo de vida
    'post_init_hook': 'post_init_hook',      # Después de instalar el módulo
    'uninstall_hook': 'uninstall_hook',      # Antes de desinstalar el módulo
    
    # ASSETS WEB (FUTURO)
    # ==================
    # Archivos JavaScript/CSS para el frontend (preparado para futuras mejoras)
    'assets': {
        'web.assets_backend': [
            # 'invoice_batch_export/static/src/js/export_widget.js',
            # 'invoice_batch_export/static/src/css/export_styles.css',
        ],
    },
    
    # CONFIGURACIÓN DE TRADUCCIÓN
    # ===========================
    # Odoo buscará automáticamente archivos .po en el directorio i18n/
    # pero podemos especificar explícitamente cuáles cargar
    'translations': [
        'i18n/es.po',          # Español (España)
    ],
    
    # METADATOS ADICIONALES
    # ====================
    # Información que aparece en el App Store de Odoo
    'images': [
        'static/description/banner.png',      # Banner principal
        'static/description/screenshot1.png', # Capturas de pantalla
        'static/description/screenshot2.png',
    ],
    
    # Precio si planeas comercializar el módulo
    # 'price': 0.00,
    # 'currency': 'EUR',
    
    # Palabras clave para búsqueda en App Store
    'tags': ['accounting', 'export', 'batch', 'invoices', 'zip', 'compression'],
}

"""
NOTAS IMPORTANTES PARA EL DESARROLLADOR
=======================================

Orden de Carga de Datos
-----------------------
El orden en la lista 'data' es absolutamente crítico. Si cambias este orden,
puedes causar errores como:
- "El modelo 'x.y.z' no existe" (si cargas vistas antes que modelos)
- "El registro 'external_id' no existe" (si referencias datos no cargados aún)
- "Permisos insuficientes" (si cargas acciones antes que permisos)

Dependencias Externas
---------------------
La dependencia 'py7zr' es opcional en el código (usamos try/except para importarla).
Sin embargo, la listamos aquí para que Odoo pueda mostrar una advertencia clara
al usuario si no está instalada. Esto es mejor que fallar silenciosamente.

Para instalar py7zr en el servidor:
pip3 install --break-system-packages py7zr

Versionado Semántico
-------------------
La versión 17.0.1.0.0 significa:
- 17.0: Compatible con Odoo 17.0
- 1.0.0: Primera versión mayor del módulo

Cuando hagas cambios:
- Incrementa el último número (17.0.1.0.1) para bug fixes
- Incrementa el penúltimo (17.0.1.1.0) para nuevas características
- Incrementa el antepenúltimo (17.0.2.0.0) para cambios incompatibles

Hooks de Ciclo de Vida
---------------------
Los hooks nos permiten ejecutar código Python en momentos específicos:
- post_init_hook: Después de instalar (crear datos iniciales, configuraciones)
- uninstall_hook: Antes de desinstalar (limpiar datos, archivos temporales)

Estos hooks se definen como funciones en __init__.py y permiten una gestión
muy granular del ciclo de vida del módulo.
"""
