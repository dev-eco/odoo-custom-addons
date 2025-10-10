# __init__.py
from . import models
from . import wizard
from . import controllers
# from . import tests

def post_init_hook(cr, registry):
    """Inicialización después de instalación"""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Crear tipos de documento predeterminados si no existen
    if not env['document.type'].search_count([]):
        env.ref('document_automation.document_type_invoice').write({'active': True})
        env.ref('document_automation.document_type_order').write({'active': True})
        env.ref('document_automation.document_type_delivery').write({'active': True})

def uninstall_hook(cr, registry):
    """Limpiar al desinstalar"""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Limpiar configuraciones
    env['ir.config_parameter'].sudo().search([
        ('key', 'like', 'document_automation.%')
    ]).unlink()
