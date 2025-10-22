# -*- coding: utf-8 -*-
{
    'name': 'Direcciones de Entrega Inline para Presupuestos',
    'version': '17.0.1.1.0',
    'category': 'Ventas',
    'summary': 'Edición inline de direcciones de entrega en presupuestos - Versión España',
    'description': """
Gestión Avanzada de Direcciones de Entrega - EcoCaucho España
============================================================

Este módulo permite editar direcciones de entrega directamente desde el formulario 
del presupuesto de venta, sin necesidad de abrir la vista del partner. 

Diseñado específicamente para empresas españolas que fabrican y distribuyen losas 
de caucho reciclado, con funcionalidades especializadas para distribuidores.

Características Principales:
---------------------------
🚛 **Gestión de Distribuidores**
   • Identificación automática de distribuidores
   • Múltiples direcciones de entrega por distribuidor
   • Selección rápida desde dropdown en presupuestos
   
📍 **Edición Inline de Direcciones**
   • Campos adaptados a España (Provincia, Código Postal)
   • Edición directa sin abrir formularios adicionales
   • Validaciones específicas para direcciones españolas
   
🏭 **Funcionalidades para Fabricación de Losas**
   • Información logística (acceso de camiones, equipo de descarga)
   • Capacidad de instalación del cliente
   • Preferencias de productos específicas
   • Horarios y restricciones de entrega
   
📝 **Registro y Auditoría**
   • Log automático de cambios en chatter
   • Historial completo de modificaciones
   • Notificaciones de nuevas direcciones creadas
   
🔒 **Seguridad y Permisos**
   • Permisos diferenciados por grupos de usuarios
   • Validaciones de integridad de datos
   • Compatible con configuraciones multi-empresa

Sectores de Aplicación:
----------------------
✅ Fabricación de losas de caucho reciclado
✅ Distribución de materiales de pavimentación
✅ Instalación de pavimentos continuos
✅ Venta B2B con múltiples puntos de entrega
✅ Gestión de proyectos de pavimentación

Casos de Uso Típicos:
--------------------
• **Distribuidor Regional**: Gestiona 5-10 almacenes en diferentes provincias
• **Cliente Instalador**: Tiene obras en múltiples ubicaciones
• **Gran Superficie**: Múltiples centros comerciales o tiendas
• **Administración Pública**: Diferentes ubicaciones municipales
• **Empresa Constructora**: Proyectos en diferentes ubicaciones

Flujo de Trabajo:
----------------
1. 📋 Marcar cliente como "Distribuidor" si corresponde
2. 🏢 Crear direcciones de entrega adicionales si es necesario
3. 💼 Al crear presupuesto, se detecta automáticamente si es distribuidor
4. 📍 Seleccionar dirección de entrega desde dropdown o crear nueva
5. ✍️  Editar campos de dirección directamente en el presupuesto
6. 💾 Los cambios se guardan automáticamente y se registran
7. 📧 Generar documentos con dirección de entrega correcta

Compatibilidad:
--------------
• Odoo 17.0 Community Edition
• Compatible con módulos OCA (sale-workflow, partner-contact)
• Sintaxis moderna de Odoo 17.0 (sin attrs deprecated)
• Multi-empresa y multi-idioma
• Bases de datos PostgreSQL 12+

Instalación y Configuración:
----------------------------
1. Instalar el módulo desde Aplicaciones
2. Marcar clientes como "Distribuidores" según corresponda
3. Crear direcciones de entrega adicionales
4. Configurar permisos de usuarios si es necesario
5. Personalizar campos específicos según necesidades

Soporte Técnico:
---------------
Para soporte técnico, consultas o personalizaciones adicionales:
📧 Email: desarrollo@ecocaucho.org
🌐 Web: https://www.ecocaucho.org
📱 Teléfono: +34 XXX XXX XXX

Desarrollado específicamente para el sector de fabricación y distribución 
de losas de caucho reciclado en España.
""",
    'author': 'EcoCaucho España - Equipo de Desarrollo',
    'website': 'https://www.ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'sale',           # Módulo de ventas de Odoo
        'contacts',       # Gestión de contactos
    ],
    'data': [
        # Archivos de seguridad (SIEMPRE PRIMERO)
        'security/ir.model.access.csv',
        
        # Vistas de partners
        'views/res_partner_views.xml',
        
        # Vistas de pedidos de venta
        'views/sale_order_views.xml',
        
        # Datos de demostración (opcional)
        # 'data/demo_data.xml',
    ],
    'demo': [
        # Datos demo para testing
        # 'data/demo_partners.xml',
        # 'data/demo_sale_orders.xml',
    ],
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
        'static/description/screenshot_1.png',
        'static/description/screenshot_2.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 100,
    
    # Configuración avanzada
    'external_dependencies': {
        'python': [],  # Dependencias Python adicionales si fueran necesarias
    },
    
    # Información de desarrollo
    'development_status': 'Production/Stable',
    'maintainer': 'EcoCaucho España',
    'contributors': [
        'Equipo Desarrollo EcoCaucho',
    ],
    
    # Configuración de actualización
    'pre_init_hook': None,
    'post_init_hook': None,
    'uninstall_hook': None,
    
    # Precio y licencia (si fuera comercial)
    'price': 0.00,
    'currency': 'EUR',
    'support': 'desarrollo@ecocaucho.org',
}
