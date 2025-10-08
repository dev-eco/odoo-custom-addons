# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Tipo de Documento'
    _order = 'sequence, id'
    
    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True, index=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    
    description = fields.Text(string='Descripción')
    target_model = fields.Char(string='Modelo Destino')
    target_model_defaults = fields.Text(string='Valores por Defecto')
    ocr_template = fields.Text(string='Plantilla OCR')
    field_mappings = fields.Text(string='Mapeo de Campos')
    
    document_count = fields.Integer(string='Documentos', compute='_compute_document_count')
    success_rate = fields.Float(string='Tasa de Éxito', compute='_compute_stats')
    avg_confidence = fields.Float(string='Confianza Media', compute='_compute_stats')
    
    @api.depends('code')
    def _compute_document_count(self):
        """Calcula el número de documentos por tipo"""
        for record in self:
            record.document_count = self.env['document.scan'].search_count([
                ('document_type_code', '=', record.code)
            ])
    
    @api.depends('code')
    def _compute_stats(self):
        """Calcula estadísticas del tipo de documento"""
        for record in self:
            # Documentos completados
            completed_docs = self.env['document.scan'].search([
                ('document_type_code', '=', record.code),
                ('status', '=', 'done')
            ])
            
            # Total documentos
            total_docs = self.env['document.scan'].search_count([
                ('document_type_code', '=', record.code)
            ])
            
            # Tasa de éxito
            if total_docs:
                record.success_rate = len(completed_docs) / total_docs
            else:
                record.success_rate = 0.0
                
            # Confianza media
            if completed_docs:
                total_confidence = sum(doc.confidence_score for doc in completed_docs)
                record.avg_confidence = total_confidence / len(completed_docs)
            else:
                record.avg_confidence = 0.0
    
    @api.onchange('target_model')
    def _onchange_target_model(self):
        """Avisa al usuario sobre los campos disponibles cuando cambia el modelo destino"""
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
