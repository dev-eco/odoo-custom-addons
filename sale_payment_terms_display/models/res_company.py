# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # Información bancaria principal
    primary_bank_account = fields.Many2one(
        'res.partner.bank', 
        string='Cuenta Bancaria Principal',
        help='Cuenta bancaria por defecto para mostrar en presupuestos'
    )
    bank_payment_reference_format = fields.Char(
        string='Formato de Referencia',
        default='SO-{name}',
        help='Formato para referencias de pago. Use {name} para número de pedido'
    )
    bank_payment_instructions = fields.Html(
        string='Instrucciones de Pago',
        help='Instrucciones específicas para transferencias bancarias'
    )
    
    # QR Codes y pagos móviles  
    enable_payment_qr = fields.Boolean(
        string='Habilitar QR de Pago',
        default=True
    )
    qr_payment_concept = fields.Char(
        string='Concepto para QR',
        default='Pedido {name}',
        help='Concepto automático para pagos QR'
    )
    
    # Descuentos por pronto pago
    enable_early_discount = fields.Boolean(
        string='Habilitar Descuento Pronto Pago',
        default=False
    )
    early_payment_discount_rate = fields.Float(
        string='% Descuento Pronto Pago',
        help='Porcentaje de descuento por pago anticipado'
    )
    early_payment_days = fields.Integer(
        string='Días para Descuento',
        default=15,
        help='Días antes del vencimiento para aplicar descuento'
    )
    
    # Información adicional
    payment_terms_note = fields.Html(
        string='Términos y Condiciones de Pago',
        help='Información legal y términos específicos'
    )
    
    # Configuración de visualización por defecto
    show_bank_info_default = fields.Boolean(
        string='Mostrar Info Bancaria por Defecto',
        default=True
    )
    show_payment_qr_default = fields.Boolean(
        string='Mostrar QR por Defecto',
        default=True
    )
    show_early_discount_default = fields.Boolean(
        string='Mostrar Descuento por Defecto',
        default=True
    )
    
    @api.constrains('early_payment_discount_rate')
    def _check_discount_rate(self):
        for company in self:
            if company.early_payment_discount_rate < 0 or company.early_payment_discount_rate > 100:
                raise ValidationError('El porcentaje de descuento debe estar entre 0 y 100.')
    
    @api.constrains('early_payment_days')
    def _check_early_payment_days(self):
        for company in self:
            if company.early_payment_days < 0:
                raise ValidationError('Los días para descuento no pueden ser negativos.')
