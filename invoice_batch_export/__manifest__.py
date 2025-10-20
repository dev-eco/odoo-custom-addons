# -*- coding: utf-8 -*-
"""
Manifest del Módulo Invoice Download PDF (Mejorado)

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
Usamos el patrón: 17.0.2.0.0 donde:
- 17.0: Versión de Odoo (siempre debe coincidir)
- 2: Versión mayor del módulo (esta es la versión mejorada)
- 0: Versión menor (nuevas características compatibles)
- 0: Versión de parche (correcciones de bugs)
"""

{
    # METADATOS BÁSICOS
    # ================
    'name': 'Mass Invoice Export to ZIP',
    'version': '17.0.2.0.0', 
    'category': 'Accounting/Accounting',
    
    # Resumen corto que aparece en la lista de aplicaciones
    # Debe ser descriptivo pero conciso (máximo ~80 caracteres)
    'summary': 'Exportación masiva de facturas en múltiples formatos comprimidos optimizados',
    
    # Descripción detallada que explica el valor del módulo
    # Esta descripción aparece cuando el usuario abre el módulo para ver detalles
    'description': """
        Mass Invoice Export to ZIP - Sistema de Exportación Inteligente
        ===============================================================
        
        Herramienta profesional para la exportación masiva de facturas, diseñada
        específicamente para asesorías contables y empresas que manejan grandes
        volúmenes de documentación fiscal.
        
        🚀 **Características Principales**
        
        * **Múltiples formatos de compresión**: ZIP estándar, ZIP optimizado, TAR.GZ
        * **Nomenclatura inteligente**: Nombres descriptivos automáticos para cada archivo
        * **Procesamiento por lotes**: Optimizado para manejar miles de facturas eficientemente
        * **Filtrado avanzado**: Por fecha, estado, tipo de documento y empresa
        * **Seguridad robusta**: Control de acceso integrado con permisos de Odoo
        * **Métricas en tiempo real**: Tiempo de procesamiento y ratios de compresión
        
        📊 **Optimizado para Alto Rendimiento**
        
        * Procesamiento en lotes configurable para uso eficiente de memoria
        * Algoritmos de compresión seleccionables según necesidades velocidad/tamaño
        * Gestión inteligente de archivos temporales con limpieza automática
        * Compatible con exportaciones de más de 1000 facturas simultáneamente
        
        🏢 **Diseñado para Asesorías Fiscales**
        
        * Nomenclatura automática que incluye tipo, número, cliente y fecha
        * Filtros específicos para períodos fiscales y tipos de documento
        * Separación automática entre facturas de cliente y proveedor
        * Integración perfecta con el flujo de trabajo existente de Odoo
        
        🔧 **Instalación y Desinstalación Limpia**
        
        * No modifica modelos core de Odoo (herencia limpia de vistas)
        * Configuración automática basada en facturas preseleccionadas
        * Compatible con instalaciones multi-empresa
        * Traducciones completas al español incluidas
        * Desinstalación completa sin rastros en el sistema
    """,
    
    # INFORMACIÓN DEL DESARROLLADOR
    # ============================
    'author': 'Tu Nombre Aquí',
    'website': 'https://tu-sitio-web.com',
    'license': 'LGPL-3',
    
    # DEPENDENCIAS DEL MÓDULO
    # ======================
    # Lista mínima de módulos de Odoo que DEBEN estar instalados antes de este módulo
    # Mantenemos solo las dependencias esenciales para evitar problemas de instalación
    'depends': [
        'account',      # Módulo de contabilidad (facturas, asientos contables)
    ],
    
    # DEPENDENCIAS EXTERNAS OPCIONALES
    # ================================
    # Bibliotecas Python que mejoran la funcionalidad pero no son críticas
    # El módulo funciona sin ellas, pero con funcionalidad reducida
    'external_dependencies': {
        'python': ['py7zr'],  # Para soporte de compresión 7-Zip (opcional)
    },
    
    # ARCHIVOS DE DATOS A CARGAR
    # ==========================
    # ORDEN CRÍTICO: Los archivos se cargan en el orden especificado aquí
    # Solo incluimos archivos que sabemos que existen o vamos a crear
    'data': [
        # 1. SEGURIDAD (siempre primero)
        # Los permisos deben cargarse antes que cualquier otra cosa
        'security/ir.model.access.csv',      # Permisos básicos de acceso a modelos
        
        # 2. WIZARDS
        # El wizard principal con toda su funcionalidad
        'wizard/invoice_export_wizard_views.xml', # Interfaz del wizard de exportación
        
        # 3. HERENCIAS DE VISTAS (al final)
        # Las herencias van al final para asegurar que las vistas base existan
        'views/account_move_views.xml',      # Botón añadido a vista de facturas
    ],
    
    # DATOS DE DEMOSTRACIÓN
    # ====================
    # Comentamos esta sección hasta que creemos los archivos demo
    # 'demo': [
    #     'demo/demo_export_templates.xml',    # Plantillas de ejemplo para testing
    # ],
    
    # CONFIGURACIÓN DEL MÓDULO
    # ========================
    'installable': True,    # El módulo está listo para instalación
    'application': False,   # No es una aplicación principal (es una extensión)
    'auto_install': False,  # No se instala automáticamente con dependencias
    
    # HOOKS DE CICLO DE VIDA (COMENTADOS HASTA IMPLEMENTAR)
    # =====================================================
    # Funciones Python que se ejecutan en momentos específicos del ciclo de vida
    # Los comentamos hasta que implementemos las funciones correspondientes
    # 'post_init_hook': 'post_init_hook',      # Después de instalar el módulo
    # 'uninstall_hook': 'uninstall_hook',      # Antes de desinstalar el módulo
    
    # ASSETS WEB (PREPARADO PARA FUTURO)
    # ================================== 
    # Archivos JavaScript/CSS para el frontend (preparado para futuras mejoras)
    # Los comentamos hasta que creemos los archivos correspondientes
    'assets': {
        # 'web.assets_backend': [
        #     'invoice_download_pdf/static/src/js/export_widget.js',
        #     'invoice_download_pdf/static/src/css/export_styles.css',
        # ],
    },
    
    # METADATOS ADICIONALES PARA APP STORE
    # ====================================
    # Información que mejora la presentación en el App Store de Odoo
    # Comentamos hasta que creemos los archivos de imagen correspondientes
    # 'images': [
    #     'static/description/banner.png',      # Banner principal del módulo
    #     'static/description/screenshot1.png', # Captura del wizard en acción
    #     'static/description/screenshot2.png', # Captura de resultados
    # ],
    
    # PALABRAS CLAVE PARA BÚSQUEDA
    # ============================
    # Facilitan encontrar el módulo en el App Store
    'tags': ['accounting', 'export', 'batch', 'invoices', 'zip', 'compression'],
}

"""
NOTAS CRÍTICAS PARA EL DESARROLLADOR
====================================

¿Por qué esta versión es más segura?
-----------------------------------
Esta versión del manifest solo referencia archivos que sabemos que existen:
- security/ir.model.access.csv (ya existe)
- wizard/invoice_export_wizard_views.xml (ya existe) 
- views/account_move_views.xml (ya existe)

Todos los demás archivos están comentados hasta que los creemos, evitando
errores de "archivo no encontrado" durante la carga del módulo.

Manejo de Dependencias Externas
-------------------------------
py7zr está listado como dependencia externa, pero nuestro código maneja
graciosamente su ausencia usando try/except. Esto significa que:
- Si py7zr está instalado: el usuario tendrá compresión 7-Zip disponible
- Si py7zr NO está instalado: el módulo funciona pero sin esa opción

Para instalar py7zr en el servidor:
    pip3 install --break-system-packages py7zr

Expansión Futura del Módulo  
---------------------------
Los elementos comentados (hooks, assets, demo data) están preparados para
cuando queramos expandir el módulo. Solo necesitamos:
1. Crear los archivos correspondientes
2. Descomentar las líneas en el manifest
3. Actualizar el módulo en Odoo

Versionado Correcto
------------------
Cambié la versión a 17.0.2.0.0 para indicar que esta es una versión mejorada
del módulo original. Esto es importante para:
- Distinguir claramente las versiones
- Permitir actualizaciones futuras con versionado semántico correcto
- Mantener trazabilidad de cambios

Orden de Carga Optimizado
-------------------------
El orden actual es mínimo pero correcto:
1. Permisos (crítico que vaya primero)
2. Vistas del wizard (contiene la funcionalidad principal)
3. Herencia de vistas (modifica vistas existentes)

Este orden garantiza que no habrá errores de dependencias durante la carga.
"""
