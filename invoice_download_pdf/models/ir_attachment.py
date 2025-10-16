# Añade esta función en una clase separada en models/ir_attachment.py
from odoo import models
import hashlib
import os

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    
    def _generate_access_token(self):
        """Genera un token de acceso para descargar archivos."""
        # Usar una semilla aleatoria para el token
        return hashlib.sha256(os.urandom(32)).hexdigest()
