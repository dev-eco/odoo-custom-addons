# -*- coding: utf-8 -*-
{
    "name": "Industry Reports Base",
    "version": "17.0.1.0.0",
    "category": "Sales/Reporting",
    "summary": "Base module for industry reporting with product technical fields and company configuration",
    "description": """
Industry Reports Base
=====================

Módulo base para sistema de reportes industriales profesionales.

Características Productos:
---------------------------
- Campos técnicos de material y acabado
- Dimensiones detalladas (largo, ancho, alto, diámetro)
- Campo computed para mostrar dimensiones en formato legible
- Información de packaging (unidades por caja, peso)
- Adjuntar fichas técnicas PDF

Características Empresa:
------------------------
- Logos corporativos para cabecera y pie de reportes
- Disclaimers legales personalizables (presupuestos, albaranes, facturas)
- Configuración técnica Py3o (timeout, cache)

Fase Piloto - Sprint 1.1
-------------------------
Implementa campos técnicos completos y configuración base para reportes.
Base compartida para módulos especializados (presupuestos, albaranes, facturas).
    """,
    "author": "Tu Empresa",
    "website": "https://www.tuempresa.com",
    "license": "LGPL-3",
    "depends": [
        "product",
        "base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/default_disclaimers.xml",
        "views/product_template_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
