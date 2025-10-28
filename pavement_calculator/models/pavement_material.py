# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PavementMaterial(models.Model):
    _name = 'pavement.material'
    _description = 'Configuración de Materiales para Pavimento'
    _rec_name = 'name'
    
    name = fields.Char('Nombre', required=True, index=True)
    material_type = fields.Selection([
        ('sbr', 'Granza SBR'),
        ('epdm', 'Granza EPDM'),
        ('encapsulated', 'Granza Encapsulado')
    ], string='Tipo de Material', required=True)
    density = fields.Float(
        'Densidad (kg/m³)', 
        required=True, 
        help="Densidad del material en kg/m³"
    )
    resin_consumption = fields.Float(
        'Consumo de Resina (L/m² por 10mm)', 
        required=True,
        help="Litros de resina por m² para un espesor de referencia de 10mm"
    )
    reference_thickness = fields.Float(
        'Espesor de Referencia (mm)',
        default=10.0,
        help="Espesor de referencia para el consumo de resina, normalmente 10mm"
    )
    pack_size = fields.Float(
        'Tamaño de Paquete (kg)', 
        required=True,
        help="Tamaño estándar de los paquetes de material en kg"
    )
    price_per_kg = fields.Float(
        'Precio por kg (EUR)', 
        required=True,
        help="Precio por kilogramo del material en euros"
    )
    resin_price_per_l = fields.Float(
        'Precio Resina por L (EUR)', 
        required=True,
        help="Precio por litro de la resina en euros"
    )
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía', 
        required=True, 
        default=lambda self: self.env.company
    )
    active = fields.Boolean(default=True)
    min_thickness = fields.Float(
        'Espesor Mínimo (mm)', 
        default=10.0,
        help="Espesor mínimo recomendado para este material"
    )
    max_thickness = fields.Float(
        'Espesor Máximo (mm)', 
        default=100.0,
        help="Espesor máximo recomendado para este material"
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Producto Asociado',
        help="Producto que se usará en el presupuesto para este material"
    )
    resin_product_id = fields.Many2one(
        'product.product', 
        string='Producto de Resina',
        help="Producto que se usará en el presupuesto para la resina"
    )
    
    @api.constrains('density', 'resin_consumption', 'pack_size', 'price_per_kg', 'resin_price_per_l')
    def _check_positive_values(self):
        for record in self:
            if record.density <= 0:
                raise ValidationError(_("La densidad debe ser mayor que 0"))
            if record.resin_consumption <= 0:
                raise ValidationError(_("El consumo de resina debe ser mayor que 0"))
            if record.pack_size <= 0:
                raise ValidationError(_("El tamaño del paquete debe ser mayor que 0"))
            if record.price_per_kg < 0:
                raise ValidationError(_("El precio por kg no puede ser negativo"))
            if record.resin_price_per_l < 0:
                raise ValidationError(_("El precio de la resina no puede ser negativo"))
    
    @api.constrains('min_thickness', 'max_thickness')
    def _check_thickness_range(self):
        for record in self:
            if record.min_thickness <= 0:
                raise ValidationError(_("El espesor mínimo debe ser mayor que 0"))
            if record.max_thickness <= 0:
                raise ValidationError(_("El espesor máximo debe ser mayor que 0"))
            if record.min_thickness >= record.max_thickness:
                raise ValidationError(_("El espesor mínimo debe ser menor que el espesor máximo"))
