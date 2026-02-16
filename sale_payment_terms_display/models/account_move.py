# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import qrcode
import io
import base64

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Campos calculados automáticamente
    payment_reference = fields.Char(
        string='Referencia de Pago',
        compute='_compute_payment_reference',
        store=True,
        help='Referencia única para identificar el pago'
    )
    early_payment_discount_amount = fields.Monetary(
        string='Descuento Pronto Pago',
        compute='_compute_early_discount',
        help='Importe del descuento por pago anticipado'
    )
    early_payment_due_date = fields.Date(
        string='Fecha Límite Descuento',
        compute='_compute_early_due_date',
        help='Fecha límite para obtener descuento'
    )
    early_payment_final_amount = fields.Monetary(
        string='Total con Descuento',
        compute='_compute_early_discount',
        help='Importe final aplicando descuento pronto pago'
    )
    payment_qr_code = fields.Binary(
        string='Código QR de Pago',
        compute='_compute_payment_qr',
        help='Código QR para pago rápido'
    )
    
    # Campos de configuración por factura
    show_bank_info = fields.Boolean(
        string='Mostrar Información Bancaria',
        default=lambda self: self.env.company.show_bank_info_default
    )
    show_payment_qr = fields.Boolean(
        string='Mostrar QR de Pago',
        default=lambda self: self.env.company.show_payment_qr_default
    )
    show_early_discount = fields.Boolean(
        string='Mostrar Descuento Pronto Pago',
        default=lambda self: self.env.company.show_early_discount_default
    )
    custom_payment_instructions = fields.Html(
        string='Instrucciones Personalizadas',
        help='Instrucciones específicas para esta factura'
    )
    
    # Métodos de pago disponibles
    available_payment_methods = fields.Many2many(
        'sale.payment.method',
        'account_move_payment_method_rel',
        'move_id',
        'method_id',
        string='Métodos de Pago Disponibles',
        help='Métodos de pago aceptados para esta factura'
    )
    preferred_payment_method = fields.Many2one(
        'sale.payment.method',
        string='Método de Pago Preferido',
        help='Método recomendado según el cliente'
    )
    
    # Información adicional
    bank_account_to_show = fields.Many2one(
        'res.partner.bank',
        string='Cuenta Bancaria a Mostrar',
        help='Cuenta específica para esta factura'
    )
    payment_urgency = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgente'),
        ('immediate', 'Inmediato')
    ], string='Urgencia de Pago', default='normal')
    
    @api.depends('name', 'ref', 'move_type')
    def _compute_payment_reference(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund'):
                # Para facturas, usar el número de factura directamente sin formato personalizado
                # Si existe 'ref' (referencia del cliente), usarla; sino usar 'name' (número de factura)
                if move.name and move.name != '/':
                    move.payment_reference = move.name
                elif move.ref:
                    move.payment_reference = move.ref
                else:
                    move.payment_reference = ''
            else:
                move.payment_reference = move.name if move.name != '/' else ''
    
    @api.depends('amount_total', 'company_id.early_payment_discount_rate', 'company_id.enable_early_discount', 'move_type')
    def _compute_early_discount(self):
        for move in self:
            if (move.move_type in ('out_invoice', 'out_refund') and
                move.company_id.enable_early_discount and 
                move.company_id.early_payment_discount_rate > 0):
                discount_rate = move.company_id.early_payment_discount_rate / 100
                move.early_payment_discount_amount = move.amount_total * discount_rate
                move.early_payment_final_amount = move.amount_total - move.early_payment_discount_amount
            else:
                move.early_payment_discount_amount = 0
                move.early_payment_final_amount = move.amount_total
    
    @api.depends('invoice_date', 'company_id.early_payment_days', 'move_type')
    def _compute_early_due_date(self):
        for move in self:
            if (move.move_type in ('out_invoice', 'out_refund') and
                move.invoice_date and move.company_id.early_payment_days):
                move.early_payment_due_date = move.invoice_date + timedelta(
                    days=move.company_id.early_payment_days
                )
            else:
                move.early_payment_due_date = False
    
    @api.depends('amount_total', 'payment_reference', 'bank_account_to_show', 'move_type')
    def _compute_payment_qr(self):
        for move in self:
            if (move.move_type in ('out_invoice', 'out_refund') and
                move.company_id.enable_payment_qr and 
                move.amount_total > 0 and 
                (move.bank_account_to_show or move.company_id.primary_bank_account)):
                move.payment_qr_code = move._generate_payment_qr()
            else:
                move.payment_qr_code = False
    
    def _generate_payment_qr(self):
        """Genera QR code según estándar EPC (SEPA)"""
        try:
            bank_account = self.bank_account_to_show or self.company_id.primary_bank_account
            if not bank_account:
                return False
            
            # Formato EPC QR Code según estándar europeo
            epc_data = [
                'BCD',  # Service Tag
                '002',  # Version
                '1',    # Character set (UTF-8)
                'SCT',  # Identification
                bank_account.bank_id.bic or '',  # BIC
                self.company_id.name[:70],  # Beneficiary Name (max 70 chars)
                bank_account.acc_number or '',  # Beneficiary Account (IBAN)
                f'EUR{self.amount_total:.2f}',  # Amount
                '',     # Purpose (empty)
                self.payment_reference[:140] if self.payment_reference else '',  # Remittance Information
                ''      # Remittance Information (structured)
            ]
            
            qr_string = '\n'.join(epc_data)
            
            # Generar QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            # Crear imagen
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return base64.b64encode(buffer.getvalue())
            
        except Exception as e:
            # Log error pero no fallar
            return False

    @api.constrains('payment_reference')
    def _check_unique_payment_reference(self):
        for move in self:
            if move.payment_reference and move.payment_reference != '/':
                existing = self.search([
                    ('payment_reference', '=', move.payment_reference),
                    ('company_id', '=', move.company_id.id),
                    ('id', '!=', move.id),
                    ('move_type', 'in', ('out_invoice', 'out_refund'))
                ])
                if existing:
                    raise ValidationError(
                        f'Ya existe otra factura con la referencia de pago {move.payment_reference}'
                    )
