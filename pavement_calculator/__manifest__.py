{
    'name': 'Pavimento de Caucho - Calculadora',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': 'Calculadora de materiales para instalaciones de pavimento de caucho',
    'description': """
Calculadora de Pavimento de Caucho
==================================
Este módulo proporciona una calculadora para estimar las cantidades de materiales 
necesarios para instalaciones de pavimento de caucho. Permite calcular:

* Cantidad de granza (SBR, EPDM, Encapsulado)
* Cantidad de resina
* Número de paquetes
* Costo estimado

Además, permite generar presupuestos directamente desde la calculadora.
""",
    'author': 'ARTEPARQUES SL',
    'website': 'https://arteparques.com',
    'depends': ['base', 'sale_management', 'product'],
    'data': [
        'security/pavement_calculator_security.xml',
        'security/ir.model.access.csv',
        'views/pavement_calculator_views.xml',
        'views/pavement_material_views.xml',
        'views/sale_order_views.xml',
        'data/pavement_material_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
