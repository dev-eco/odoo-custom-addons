# -*- coding: utf-8 -*-
{
    'name': 'Portal B2B - Direcciones de Entrega',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Gestión de múltiples direcciones de entrega para distribuidores B2B',
    'description': """
Portal B2B - Direcciones de Entrega
====================================

Módulo complementario para gestión de múltiples direcciones de entrega.

Funcionalidades:
----------------
* Gestión CRUD de direcciones de entrega desde portal
* Múltiples direcciones por distribuidor
* Alias personalizados para direcciones (ej: "Obra Madrid", "Almacén Norte")
* Información de contacto específica por dirección
* Requisitos especiales de entrega (cita previa, camión con plataforma elevadora)
* Notas de entrega personalizadas
* Selección de dirección en creación de pedidos
* Dirección por defecto configurable
* Soft delete (desactivación en lugar de eliminación)
* Etiquetas de cliente final para distribuidores
* Sincronización automática con dirección de envío en PDF
* Ocultar información de empresa en documentos
* Subida de documentos (etiquetas transporte, albaranes)
* Gestión completa de clientes finales desde portal

Características técnicas:
-------------------------
* Depende de portal_b2b_base
* Modelos nuevos: delivery.address, distributor.label
* Extensión de sale.order con delivery_address_id y distributor_label_id
* Seguridad por record rules
* API JSON para gestión desde portal
* Responsive Bootstrap 5
* Subida de archivos con validación

Rutas del portal:
-----------------
* /mis-direcciones - Lista de direcciones
* /mis-direcciones/crear - Crear nueva dirección
* /mis-direcciones/<id>/editar - Editar dirección
* /mis-direcciones/<id>/eliminar - Desactivar dirección
* /mis-direcciones/<id>/por-defecto - Marcar como predeterminada
* /mis-etiquetas - Lista de etiquetas cliente final
* /mis-etiquetas/crear - Crear nueva etiqueta
* /mis-etiquetas/<id>/editar - Editar etiqueta
* /mis-etiquetas/<id>/eliminar - Desactivar etiqueta
* /mis-etiquetas/<id>/descargar/<doc_type> - Descargar documentos

Autor: Generic
Licencia: LGPL-3
    """,
    'author': 'Generic',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'portal_b2b_base',
        'website',
    ],
    'data': [
        # Seguridad
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # Configuración del sitio web
        'data/website_config.xml',
        
        # Vistas backend
        'views/delivery_address_views.xml',
        'views/distributor_label_views.xml',
        'views/sale_order_views.xml',
        
        # Templates portal
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'portal_b2b_delivery_addresses/static/src/scss/delivery_addresses.scss',
            'portal_b2b_delivery_addresses/static/src/js/delivery_addresses.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
