# -*- coding: utf-8 -*-
# © 2025 ECOCAUCHO - https://ecocaucho.org
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from . import models


def uninstall_hook(env):
    """
    Hook ejecutado al desinstalar el módulo.
    
    Esta función se ejecuta automáticamente cuando se desinstala el módulo
    y se encarga de limpiar cualquier referencia o configuración que podría
    causar problemas después de la desinstalación.
    
    En v2.0, este hook es principalmente preventivo ya que el módulo ya no
    modifica reportes del sistema. Sin embargo, lo incluimos para:
    1. Mantener buenas prácticas
    2. Permitir futuras limpiezas si son necesarias
    3. Registrar en el log la desinstalación
    """
    import logging
    _logger = logging.getLogger(__name__)
    
    _logger.info("="*80)
    _logger.info("Desinstalando módulo Plantilla Factura EcoCaucho v2.0")
    _logger.info("="*80)
    
    # Buscar si algún parámetro del sistema hace referencia a nuestro reporte
    config_params = env['ir.config_parameter'].search([
        ('value', 'ilike', 'plantilla_factura%')
    ])
    
    if config_params:
        _logger.warning(
            "Se encontraron %d parámetros de configuración que referencian "
            "este módulo. Estos parámetros NO se eliminarán automáticamente "
            "para evitar romper configuraciones personalizadas del usuario.",
            len(config_params)
        )
        for param in config_params:
            _logger.warning("  - %s = %s", param.key, param.value)
    else:
        _logger.info("No se encontraron parámetros de configuración que limpiar.")
    
    _logger.info("Desinstalación completada exitosamente.")
    _logger.info("El reporte estándar de Odoo sigue funcionando normalmente.")
    _logger.info("="*80)
