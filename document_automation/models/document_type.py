import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Tipo de Documento'
    _order = 'sequence, name'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        translate=True
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        help='Código único para identificar este tipo de documento'
    )
    
    description = fields.Text(
        string='Descripción',
        translate=True,
        help='Descripción detallada de este tipo de documento'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Determina el orden de los tipos de documento'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    # Configuración de procesamiento
    target_model = fields.Char(
        string='Modelo Destino',
        required=True,
        help='Modelo Odoo donde se creará el documento final'
    )
    
    target_model_defaults = fields.Text(
        string='Valores Predeterminados',
        default='{}',
        help='Diccionario JSON con valores predeterminados para el modelo destino'
    )
    
    ocr_template = fields.Char(
        string='Plantilla OCR',
        help='Identificador de la plantilla de OCR a utilizar'
    )
    
    field_mappings = fields.Text(
        string='Mapeo de Campos',
        default='{}',
        help='Mapeo JSON entre campos del modelo destino y datos extraídos por OCR'
    )
    
    # Estadísticas
    document_count = fields.Integer(
        string='Documentos',
        compute='_compute_document_count',
        help='Número de documentos de este tipo'
    )
    
    success_rate = fields.Float(
        string='Tasa de Éxito',
        compute='_compute_success_rate',
        help='Porcentaje de documentos procesados correctamente'
    )
    
    avg_confidence = fields.Float(
        string='Confianza Media',
        compute='_compute_avg_confidence',
        help='Puntuación de confianza media para este tipo de documento'
    )
    
    @api.depends('code')
    def _compute_document_count(self):
        """Calcula el número de documentos para este tipo"""
        for record in self:
            count = self.env['document.scan'].search_count([
                ('document_type_code', '=', record.code)
            ])
            record.document_count = count
    
    @api.depends('code')
    def _compute_success_rate(self):
        """Calcula la tasa de éxito para este tipo de documento"""
        for record in self:
            total = self.env['document.scan'].search_count([
                ('document_type_code', '=', record.code)
            ])
            
            if total > 0:
                success = self.env['document.scan'].search_count([
                    ('document_type_code', '=', record.code),
                    ('status', '=', 'processed')
                ])
                record.success_rate = (success / total) * 100
            else:
                record.success_rate = 0
    
    @api.depends('code')
    def _compute_avg_confidence(self):
        """Calcula la confianza media para este tipo de documento"""
        for record in self:
            documents = self.env['document.scan'].search([
                ('document_type_code', '=', record.code),
                ('confidence_score', '>', 0)
            ])
            
            if documents:
                avg = sum(documents.mapped('confidence_score')) / len(documents)
                record.avg_confidence = avg
            else:
                record.avg_confidence = 0
    
    @api.constrains('code')
    def _check_code_unique(self):
        """Verifica que el código sea único"""
        for record in self:
            count = self.search_count([
                ('code', '=', record.code),
                ('id', '!=', record.id)
            ])
            if count > 0:
                raise ValidationError(_("El código debe ser único para cada tipo de documento"))
    
    @api.constrains('target_model_defaults')
    def _check_target_model_defaults_format(self):
        """Verifica que los valores predeterminados tengan formato JSON válido"""
        for record in self:
            if record.target_model_defaults:
                try:
                    json.loads(record.target_model_defaults)
                except json.JSONDecodeError:
                    raise ValidationError(_("El campo 'Valores Predeterminados' debe ser un JSON válido"))
    
    @api.constrains('field_mappings')
    def _check_field_mappings_format(self):
        """Verifica que el mapeo de campos tenga formato JSON válido"""
        for record in self:
            if record.field_mappings:
                try:
                    json.loads(record.field_mappings)
                except json.JSONDecodeError:
                    raise ValidationError(_("El campo 'Mapeo de Campos' debe ser un JSON válido"))
    
    @api.onchange('target_model')
    def _onchange_target_model(self):
        """Actualiza los campos disponibles cuando cambia el modelo destino"""
        if not self.target_model:
            return
            
        # Verificar si el modelo existe
        if not self.env.get(self.target_model):
            warning = {
                'title': _('Advertencia'),
                'message': _('El modelo %s no existe en el sistema') % self.target_model
            }
            return {'warning': warning}
    
    def action_view_documents(self):
        """Acción para ver documentos de este tipo"""
        self.ensure_one()
        
        action = self.env.ref('document_automation.action_document_scan').read()[0]
        action['domain'] = [('document_type_code', '=', self.code)]
        action['context'] = {'default_document_type_code': self.code}
        
        return action
    
    def action_test_mapping(self):
        """Acción para probar el mapeo de campos"""
        self.ensure_one()
        
        # Aquí implementaríamos una acción para probar el mapeo
        # Por ejemplo, mostrando un wizard para subir un documento de prueba
        
        # Por ahora, solo mostramos un mensaje
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mapeo de Campos'),
                'message': _('Esta funcionalidad permitirá probar el mapeo de campos con un documento de prueba'),
                'sticky': False,
                'type': 'info',
            }
        }
    
    def name_get(self):
        """Personaliza la representación del nombre"""
        result = []
        for record in self:
            name = f"{record.name} [{record.code}]"
            result.append((record.id, name))
        return result
