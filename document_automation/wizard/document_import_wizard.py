# wizard/document_import_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64

class DocumentImportWizard(models.TransientModel):
    _name = 'document.import.wizard'
    _description = 'Importador de Documentos'
    
    name = fields.Char('Nombre', required=True)
    document_file = fields.Binary('Archivo', required=True)
    filename = fields.Char('Nombre de archivo')
    document_type_id = fields.Many2one(
        'document.type',
        string='Tipo de documento',
        help="Si se conoce, especificar el tipo de documento"
    )
    note = fields.Text('Notas')
    
    def action_import(self):
        """Importar documento"""
        self.ensure_one()
        
        if not self.document_file:
            raise UserError(_("Debe seleccionar un archivo para importar."))
            
        # Crear documento
        doc_vals = {
            'name': '/',  # Secuencia automática
            'document_file': self.document_file,
            'filename': self.filename,
            'source': 'upload',
            'user_id': self.env.user.id,
        }
        
        if self.document_type_id:
            doc_vals['document_type_id'] = self.document_type_id.id
            
        document = self.env['document.automation'].create(doc_vals)
        
        # Añadir nota si existe
        if self.note:
            document.message_post(body=self.note)
            
        # Redirigir a documento creado
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'document.automation',
            'res_id': document.id,
            'view_mode': 'form',
            'target': 'current',
        }
