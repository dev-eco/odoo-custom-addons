# -*- coding: utf-8 -*-
{
    'name': 'Información de Pago Avanzada en Ventas',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Información completa de pago en presupuestos y pedidos',
    'description': '''
    Módulo que enriquece los presupuestos y pedidos de venta con información completa de pago:
    
    🏦 Información Bancaria Detallada
    • Cuentas bancarias de la empresa con IBAN, BIC
    • Referencias de pago automáticas y personalizables
    • Instrucciones específicas por método de pago
    
    💳 Métodos de Pago Configurables  
    • Gestión avanzada de métodos de pago aceptados
    • Información de comisiones y tiempos de procesamiento
    • Restricciones por importe y país
    
    🎯 Descuentos por Pronto Pago
    • Cálculo automático de descuentos por pago anticipado
    • Fechas límite y condiciones configurables
    • Visualización clara en documentos
    
    📱 Códigos QR para Pago Rápido
    • Generación automática de QR codes SEPA
    • Integración con apps bancarias móviles
    • Referencias de pago incluidas automáticamente
    
    📋 Reportes Mejorados
    • PDFs profesionales con toda la información de pago
    • Volantes de pago independientes
    • Personalización por empresa y cliente
    
    Compatible con localización española y estándares SEPA.
    ''',
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': [
        'sale',
        'account', 
        'base',
        'web',
    ],
    'data': [
        # Seguridad
        'security/ir.model.access.csv',
        
        # Datos iniciales
        'data/payment_methods_data.xml',
        
        # Vistas
        'views/payment_method_views.xml',
        'views/res_company_views.xml',
        'views/sale_order_views.xml',
        
        # Reportes
        'reports/sale_order_payment_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_payment_terms_display/static/src/css/payment_info_styles.css',
            'sale_payment_terms_display/static/src/js/payment_calculator.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
