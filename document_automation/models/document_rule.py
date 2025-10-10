# models/document_rule.py
from odoo import models, fields, api, _

class DocumentRule(models.Model):
    _name = 'document.rule'
    _description = 'Reglas de Procesamiento de Documentos'
    _order = 'sequence, id'
    
    name = fields.Char('Nombre', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    active = fields.Boolean('Activo', default=True)
    
    # Usa referencias por nombre (string) para evitar importaciones
    document_type_id = fields.Many2one('document.type', 'Tipo de documento aplicable')
    
    # Condiciones
    condition = fields.Text('Condición Python', 
                          help='Condición que debe cumplirse para aplicar la regla')
    
    # Acciones
    action_type = fields.Selection([
        ('set_field', 'Establecer campo'),
        ('create_record', 'Crear registro'),
        ('python', 'Código Python')
    ], string='Tipo de acción', required=True, default='set_field')
    
    action_data = fields.Text('Datos de acción',
                            help='JSON con parámetros de la acción')
    
    action_python = fields.Text('Código Python',
                              help='Código Python a ejecutar si action_type es python')
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                               default=lambda self: self.env.company)
    
    # Estadísticas
    usage_count = fields.Integer('Usos', compute='_compute_usage_count')
    
    def _compute_usage_count(self):
        for record in self:
            # Hacemos la búsqueda por nombre y no por importación directa
            # para evitar ciclos
            record.usage_count = self.env['document.automation.log'].search_count([
                ('action', '=', 'rule'),
                ('message', 'ilike', record.name)
            ])
