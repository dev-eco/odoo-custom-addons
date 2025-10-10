# models/document_type.py
from odoo import models, fields, api, _
import json

class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Tipo de Documento'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    
    name = fields.Char('Nombre', required=True, translate=True)
    code = fields.Char('Código', required=True, help="Código técnico para identificación interna")
    model_id = fields.Many2one('ir.model', 'Modelo Asociado', 
                              domain=[('transient', '=', False)])
    active = fields.Boolean('Activo', default=True)
    sequence = fields.Integer('Secuencia', default=10, 
                             help="Determina el orden de evaluación de tipos de documento")
    
    company_id = fields.Many2one('res.company', 'Compañía',
                                default=lambda self: self.env.company)
    
    # Campos para detección automática
    keywords = fields.Text('Palabras Clave', 
                         help='Palabras clave separadas por comas para identificar este tipo de documento')
    
    regex_patterns = fields.Text('Patrones Regex',
                               help='Patrones de expresión regular (uno por línea) para identificar este tipo')
    
    advanced_patterns = fields.Text('Patrones Avanzados',
                                  help='Patrones avanzados en formato JSON para identificación precisa')
    
    # Plantilla de extracción
    extraction_template = fields.Text('Plantilla de Extracción', 
                                    help='Plantilla JSON para la extracción de datos')
    
    # Campos para validación y flujo de trabajo
    validation_rules = fields.Text('Reglas de Validación',
                                 help='Reglas para validar los datos extraídos')
    
    approval_required = fields.Boolean('Requiere Aprobación', default=False,
                                     help='Requiere aprobación manual antes de crear documentos')
    
    approval_user_ids = fields.Many2many('res.users', 'document_type_approval_users_rel',
                                       'type_id', 'user_id', string='Aprobadores')
    
    notify_user_ids = fields.Many2many('res.users', 'document_type_notify_users_rel',
                                     'type_id', 'user_id', string='Usuarios a Notificar')
    
    # Estadísticas
    document_count = fields.Integer('Documentos', compute='_compute_document_count')
    success_rate = fields.Float('Tasa de Éxito (%)', compute='_compute_success_rate')
    
    _sql_constraints = [
        ('unique_code', 'UNIQUE(code, company_id)', 
         'El código del tipo de documento debe ser único por compañía')
    ]
    
    @api.constrains('extraction_template')
    def _check_extraction_template(self):
        for record in self:
            if record.extraction_template:
                try:
                    template = json.loads(record.extraction_template)
                    if not isinstance(template, dict):
                        raise ValueError("La plantilla debe ser un objeto JSON")
                except Exception as e:
                    raise models.ValidationError(_(f"Plantilla JSON inválida: {str(e)}"))
    
    @api.constrains('advanced_patterns')
    def _check_advanced_patterns(self):
        for record in self:
            if record.advanced_patterns:
                try:
                    patterns = json.loads(record.advanced_patterns)
                    if not isinstance(patterns, list):
                        raise ValueError("Los patrones deben ser una lista de objetos")
                    
                    for pattern in patterns:
                        if not isinstance(pattern, dict):
                            raise ValueError("Cada patrón debe ser un objeto")
                        if 'pattern' not in pattern:
                            raise ValueError("Cada patrón debe tener una clave 'pattern'")
                except Exception as e:
                    raise models.ValidationError(_(f"Patrones JSON inválidos: {str(e)}"))
    
    def _compute_document_count(self):
        for record in self:
            record.document_count = self.env['document.automation'].search_count([
                ('document_type_id', '=', record.id)
            ])
    
    def _compute_success_rate(self):
        for record in self:
            # Calcular tasa de éxito (documentos vinculados correctamente / total)
            total = self.env['document.automation'].search_count([
                ('document_type_id', '=', record.id)
            ])
            
            if total == 0:
                record.success_rate = 0.0
                continue
                
            success = self.env['document.automation'].search_count([
                ('document_type_id', '=', record.id),
                ('state', 'in', ['validated', 'linked'])
            ])
            
            record.success_rate = (success / total) * 100.0 if total > 0 else 0.0
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('Documentos'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.automation',
            'view_mode': 'tree,form',
            'domain': [('document_type_id', '=', self.id)],
            'context': {'default_document_type_id': self.id}
        }
    
    def generate_template_skeleton(self):
        """Genera un esqueleto de plantilla de extracción según el modelo"""
        self.ensure_one()
        
        if not self.model_id:
            return
            
        model = self.env[self.model_id.model]
        fields_info = model.fields_get()
        
        # Crear esqueleto básico para campos comunes
        template = {
            "fields": []
        }
        
        # Campos básicos según el modelo
        if self.model_id.model == 'account.move':
            # Plantilla para facturas
            template["fields"] = [
                {
                    "name": "invoice_number",
                    "type": "text",
                    "patterns": [
                        {"regex": "(?:Factura|Invoice)[: ]\\s*([A-Za-z0-9_\\-/]+)"},
                        {"regex": "No\\.?[: ]\\s*([A-Za-z0-9_\\-/]+)"}
                    ]
                },
                {
                    "name": "invoice_date",
                    "type": "date",
                    "patterns": [
                        {"regex": "(?:Fecha|Date)[: ]\\s*(\\d{1,2}[/.-]\\d{1,2}[/.-]\\d{2,4})"}
                    ]
                },
                {
                    "name": "vat",
                    "type": "text",
                    "patterns": [
                        {"regex": "(?:NIF|CIF|VAT)[: ]?\\s*([A-Za-z0-9]{8,15})"}
                    ]
                },
                {
                    "name": "amount_total",
                    "type": "amount",
                    "patterns": [
                        {"regex": "(?:Total|Amount)[: ]\\s*(?:EUR|€|USD|\\$)?\\s*([0-9.,]+)"}
                    ]
                }
            ]
        elif self.model_id.model == 'purchase.order':
            # Plantilla para pedidos
            template["fields"] = [
                {
                    "name": "order_number",
                    "type": "text",
                    "patterns": [
                        {"regex": "(?:Pedido|Order)[: ]\\s*([A-Za-z0-9_\\-/]+)"}
                    ]
                },
                {
                    "name": "date_order",
                    "type": "date",
                    "patterns": [
                        {"regex": "(?:Fecha|Date)[: ]\\s*(\\d{1,2}[/.-]\\d{1,2}[/.-]\\d{2,4})"}
                    ]
                },
                {
                    "name": "vendor_vat",
                    "type": "text",
                    "patterns": [
                        {"regex": "(?:NIF|CIF|VAT)[: ]?\\s*([A-Za-z0-9]{8,15})"}
                    ]
                }
            ]
        elif self.model_id.model == 'stock.picking':
            # Plantilla para albaranes
            template["fields"] = [
                {
                    "name": "delivery_number",
                    "type": "text",
                    "patterns": [
                        {"regex": "(?:Albarán|Delivery)[: ]\\s*([A-Za-z0-9_\\-/]+)"}
                    ]
                },
                {
                    "name": "date",
                    "type": "date",
                    "patterns": [
                        {"regex": "(?:Fecha|Date)[: ]\\s*(\\d{1,2}[/.-]\\d{1,2}[/.-]\\d{2,4})"}
                    ]
                },
                {
                    "name": "order_reference",
                    "type": "text",
                    "patterns": [
                        {"regex": "(?:Pedido|Order)[: ]\\s*([A-Za-z0-9_\\-/]+)"}
                    ]
                }
            ]
        
        # Añadir reglas de validación básicas
        template["validation"] = []
        
        # Serializar a JSON con formato bonito
        json_template = json.dumps(template, indent=2, ensure_ascii=False)
        
        return self.write({'extraction_template': json_template})
