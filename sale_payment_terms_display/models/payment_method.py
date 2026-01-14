# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PaymentMethod(models.Model):
    _name = 'sale.payment.method'
    _description = 'Método de Pago Avanzado'
    _order = 'sequence, name'
    
    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    description = fields.Html(string='Descripción')
    
    # Configuración específica
    requires_bank_account = fields.Boolean(string='Requiere Cuenta Bancaria')
    supports_qr_payment = fields.Boolean(string='Soporta Pago QR')
    early_discount_applicable = fields.Boolean(string='Aplica Descuento Pronto Pago')
    processing_days = fields.Integer(string='Días de Procesamiento', default=0)
    
    # Información para clientes
    customer_instructions = fields.Html(string='Instrucciones para Cliente')
    fees_info = fields.Html(string='Información de Comisiones')
    
    # Validaciones y restricciones
    min_amount = fields.Monetary(string='Importe Mínimo', default=0)
    max_amount = fields.Monetary(string='Importe Máximo', default=0)
    currency_id = fields.Many2one('res.currency', string='Moneda', 
                                 default=lambda self: self.env.company.currency_id)
    
    # Configuración técnica
    payment_provider = fields.Selection([
        ('bank_transfer', 'Transferencia Bancaria'),
        ('credit_card', 'Tarjeta de Crédito'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('redsys', 'Redsys'),
        ('bizum', 'Bizum'),
        ('other', 'Otro')
    ], string='Proveedor de Pago')
    
    # Campos de empresa
    company_id = fields.Many2one('res.company', string='Empresa', 
                                default=lambda self: self.env.company)
    
    # Campo para marcar método principal
    is_primary = fields.Boolean(
        string='Método Principal', 
        default=False,
        help='Marcar como método de pago principal para la empresa',
        copy=False
    )
    
    @api.constrains('min_amount', 'max_amount')
    def _check_amounts(self):
        for method in self:
            if method.max_amount > 0 and method.min_amount > method.max_amount:
                raise ValidationError('El importe mínimo no puede ser mayor al máximo')
    
    @api.constrains('code')
    def _check_unique_code(self):
        for method in self:
            if method.code:
                existing = self.search([
                    ('code', '=', method.code),
                    ('company_id', '=', method.company_id.id),
                    ('id', '!=', method.id)
                ])
                if existing:
                    raise ValidationError(f'Ya existe un método de pago con el código {method.code}')
    
    @api.constrains('is_primary')
    def _check_unique_primary(self):
        for method in self:
            if method.is_primary:
                existing = self.search([
                    ('is_primary', '=', True),
                    ('company_id', '=', method.company_id.id),
                    ('id', '!=', method.id),
                    ('active', '=', True)  # Solo considerar métodos activos
                ])
                if existing:
                    existing.write({'is_primary': False})  # Desmarcar el anterior
