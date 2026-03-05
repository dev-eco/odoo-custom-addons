# -*- coding: utf-8 -*-
{
    "name": "Industry Reports Base",
    "version": "17.0.1.0.0",
    "category": "Sales/Reporting",
    "summary": "Base module for industry reporting with product technical fields",
    "description": """
Industry Reports Base
=====================

Módulo base para sistema de reportes industriales.

Características:
- Campos técnicos de dimensiones en productos (largo, ancho, alto, diámetro)
- Campo computed para mostrar dimensiones en formato legible
- Base compartida para módulos de reportes especializados

Fase Piloto - Solo Dimensiones
-------------------------------
Este módulo implementa únicamente campos de dimensiones.
Campos de material, acabado y packaging se añadirán en Fase 2.
    """,
    "author": "Tu Empresa",
    "website": "https://www.tuempresa.com",
    "license": "LGPL-3",
    "depends": [
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
