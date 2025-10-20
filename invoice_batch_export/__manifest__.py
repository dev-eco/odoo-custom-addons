# -*- coding: utf-8 -*-
{
    'name': 'Mass Invoice Export to ZIP',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Exportar múltiples facturas en formato ZIP con nombres informativos',
    'description': """
        Mass Invoice Export to ZIP
        ===========================
        
        Este módulo permite a los usuarios:
        
        * Seleccionar múltiples facturas de clientes y/o proveedores
        * Exportarlas en un archivo ZIP comprimido
        * Nombres de archivo informativos con formato:
          [TIPO]_[NÚMERO]_[PARTNER]_[FECHA].pdf
        * Manejo robusto de errores y validaciones
        * Compatible con facturas de múltiples empresas
        * Optimizado para grandes volúmenes de facturas
        
        Perfecto para asesorías fiscales y gestión documental.
    """,
    'author': 'EcoCaucho',
    'website': 'https://www.ecocaucho.org',
    'license': 'LGPL-3',
    'depends': [
        'account',  # Módulo base de contabilidad
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/invoice_export_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    
    # Assets para JavaScript (si decides agregar funcionalidad frontend)
    'assets': {},
}
