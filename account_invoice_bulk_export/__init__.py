# -*- coding: utf-8 -*-

from . import models
from . import wizard
from . import controllers

def _post_init_hook(cr, registry):
    """Hook ejecutado después de la instalación del módulo."""
    pass

def _uninstall_hook(cr, registry):
    """Hook ejecutado antes de la desinstalación del módulo."""
    pass
