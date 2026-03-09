# -*- coding: utf-8 -*-
{
    "name": "Presupuestos - Avisos Sin Revisar",
    "version": "17.0.1.0.0",
    "category": "Sales",
    "summary": "Añade indicador visual de presupuestos sin revisar",
    "description": """
        Módulo que añade columna "Sin revisar" en vista de presupuestos
        con indicadores visuales (🔴/🟢) y automatización de estados.
    """,
    "author": "Tu Empresa",
    "website": "https://www.tuempresa.com",
    "depends": ["sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/sale_order_actions.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
