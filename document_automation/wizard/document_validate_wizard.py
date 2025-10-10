# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DocumentValidateWizard(models.TransientModel):
    _name = 'document.validate.wizard'
    _description = 'Asistente de Validación de Documentos'

    document_id = fields.Many2one(
        'document.automation', 
        string='Documento', 
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    
    note = fields.Text('Notas de validación')
    
    extraction_result = fields.Text(
        'Resultado de la extracción', 
        readonly=True,
        related='document_id.extracted_data'
    )
    
    # Campos para corregir datos extraídos
    # Estos campos se podrían generar dinámicamente según el tipo de documento
    partner_id = fields.Many2one('res.partner', 'Socio')
    reference = fields.Char('Referencia')
    date = fields.Date('Fecha')
    amount = fields.Float('Importe')
    
    @api.model
    def default_get(self, fields_list):
        """
        Rellena los campos según los datos extraídos del documento
        """
        res = super().default_get(fields_list)
        
        # Si hay un documento activo, intentamos extraer sus datos
        document_id = self.env.context.get('active_id')
        if document_id:
            document = self.env['document.automation'].browse(document_id)
            if document.extracted_data:
                try:
                    # Aquí podríamos parsear los datos extraídos e inicializar los campos
                    # Este es un ejemplo muy básico
                    import json
                    data = json.loads(document.extracted_data)
                    
                    # Asignamos los valores a los campos del wizard
                    if 'partner_name' in data and data['partner_name']:
                        partners = self.env['res.partner'].search([
                            ('name', 'ilike', data['partner_name'])
                        ], limit=1)
                        if partners:
                            res['partner_id'] = partners.id
                            
                    if 'reference' in data:
                        res['reference'] = data['reference']
                        
                    if 'date' in data:
                        res['date'] = data['date']
                        
                    if 'amount' in data:
                        res['amount'] = data['amount']
                except:
                    # Si hay un error, simplemente continuamos sin cargar datos
                    pass
                    
        return res
    
    def action_validate(self):
        """
        Valida el documento y crea el registro correspondiente
        """
        self.ensure_one()
        
        if not self.document_id:
            raise UserError(_('No se ha seleccionado ningún documento'))
            
        # Actualizamos el estado del documento
        self.document_id.write({
            'state': 'validated',
            'validated_date': fields.Datetime.now(),
        })
        
        # Añadimos una nota si es necesario
        if self.note:
            self.document_id.message_post(body=self.note)
            
        # Registramos la validación en el log
        self.document_id.log_action('validate', _('Documento validado por %s') % self.env.user.name)
        
        # Aquí podríamos crear el registro correspondiente según el tipo de documento
        # Por ejemplo, una factura, un pedido, etc.
        
        # Mensaje de éxito
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Documento validado correctamente'),
                'sticky': False,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }
