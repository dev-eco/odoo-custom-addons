# -*- coding: utf-8 -*-
# © 2025 ECOCAUCHO - https://ecocaucho.org
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

{
    'name': 'Facturas Personalizadas EcoCaucho',
    'version': '17.0.2.0.0',
    'summary': 'Plantilla de factura personalizada optimizada como opción adicional',
    'description': """
        Plantilla de Factura Personalizada para EcoCaucho
        ===================================================
        
        Este módulo agrega una plantilla de factura alternativa, optimizada y profesional
        que coexiste con la plantilla estándar de Odoo.
        
        Características principales:
        ----------------------------
        * Plantilla de factura personalizada con diseño optimizado
        * Campos adicionales: referencia del cliente, contacto de facturación, 
          instrucciones especiales
        * Muestra pedidos relacionados automáticamente
        * Formato compacto que aprovecha mejor el espacio del papel
        * Diseño profesional y limpio
        * Completamente compatible con multi-empresa
        
        Uso:
        ----
        1. Después de instalar, verás un nuevo reporte llamado "Factura EcoCaucho"
        2. Puedes seleccionarlo desde el menú "Imprimir" de cualquier factura
        3. También puedes configurarlo como predeterminado en Ajustes > Técnico > 
           Informes > Facturas de Cliente
        
        Ventajas sobre la plantilla estándar:
        --------------------------------------
        * Menos espacio desperdiciado
        * Toda la información relevante visible en una página
        * Paginación mejorada para facturas con múltiples pedidos
        * Referencias de pedido mostradas claramente
        
        Nota Importante:
        ----------------
        Este módulo NO reemplaza la plantilla estándar de Odoo. Ambas plantillas
        coexisten y puedes elegir cuál usar. Esto permite desinstalar el módulo
        sin problemas si es necesario.
    """,
    'category': 'Accounting/Accounting',
    'author': 'ECOCAUCHO',
    'website': 'https://ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'sale',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/report_facturas_templates.xml',
        'views/report_facturas_DEBUG.xml',
        'reports/invoice_reports.xml',
        'views/account_move_views.xml',  # Nuevo archivo para añadir campos en formulario
    ],
    'assets': {
        'web.report_assets_common': [
            'plantilla_factura/static/src/scss/invoice_report_style.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'application': False,
    'installable': True,
    'auto_install': False,
    
    # Información de actualización
    'uninstall_hook': 'uninstall_hook',
}
