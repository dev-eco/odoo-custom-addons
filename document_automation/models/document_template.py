# models/document_template.py
from odoo import models, fields, api, _

class DocumentTemplate(models.Model):
    _name = 'document.template'
    _description = 'Plantilla de Documento'
    
    name = fields.Char('Nombre', required=True)
    document_type_id = fields.Many2one('document.type', 'Tipo de documento', required=True)
    active = fields.Boolean('Activo', default=True)
    template_content = fields.Text('Contenido de la plantilla')
