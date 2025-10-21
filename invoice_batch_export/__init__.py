# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL] 
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

"""
Mass Invoice Export Module - Odoo 17.0
======================================

Este módulo permite la exportación masiva de facturas en múltiples formatos
de compresión con plantillas de nomenclatura personalizables.

Arquitectura del módulo:
- models/: Modelos persistentes (plantillas, configuraciones)  
- wizard/: Modelos transitorios (wizards de exportación)
- views/: Vistas XML y interfaces de usuario
- security/: Reglas de acceso y permisos
- data/: Datos maestros y configuraciones por defecto
"""

# Importar modelos principales ANTES que wizards
from . import models
from . import wizard

# Hooks de instalación/desinstalación
def post_init_hook(env):
    """
    Hook ejecutado después de la instalación del módulo.
    Configura datos iniciales y plantillas por defecto.
    """
    # Crear plantillas por defecto para empresas existentes
    companies = env['res.company'].search([])
    for company in companies:
        if not company.export_template_ids:
            env['export.template'].create({
                'name': f'Plantilla {company.name}',
                'company_id': company.id,
                'pattern': '{type}_{number}_{partner}_{date}.pdf',
                'is_default': True,
                'active': True,
            })

def uninstall_hook(env):
    """
    Hook ejecutado antes de la desinstalación.
    Limpia datos huérfanos y configuraciones.
    """
    # Limpiar plantillas de exportación
    templates = env['export.template'].search([])
    templates.unlink()
