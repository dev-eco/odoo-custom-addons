# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import qrcode
import io
import base64

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
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
    
    # Campos de configuración por pedido
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
        help='Instrucciones específicas para este pedido'
    )
    
    # Métodos de pago disponibles
    available_payment_methods = fields.Many2many(
        'sale.payment.method',
        string='Métodos de Pago Disponibles',
        help='Métodos de pago aceptados para este pedido'
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
        help='Cuenta específica para este pedido'
    )
    payment_urgency = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgente'),
        ('immediate', 'Inmediato')
    ], string='Urgencia de Pago', default='normal')
    
    @api.depends('name', 'company_id')
    def _compute_payment_reference(self):
        for order in self:
            if order.name and order.company_id.bank_payment_reference_format:
                format_str = order.company_id.bank_payment_reference_format
                order.payment_reference = format_str.format(name=order.name)
            else:
                order.payment_reference = order.name or ''
    
    @api.depends('amount_total', 'company_id.early_payment_discount_rate', 'company_id.enable_early_discount')
    def _compute_early_discount(self):
        for order in self:
            if (order.company_id.enable_early_discount and 
                order.company_id.early_payment_discount_rate > 0):
                discount_rate = order.company_id.early_payment_discount_rate / 100
                order.early_payment_discount_amount = order.amount_total * discount_rate
                order.early_payment_final_amount = order.amount_total - order.early_payment_discount_amount
            else:
                order.early_payment_discount_amount = 0
                order.early_payment_final_amount = order.amount_total
    
    @api.depends('date_order', 'company_id.early_payment_days')
    def _compute_early_due_date(self):
        for order in self:
            if order.date_order and order.company_id.early_payment_days:
                order.early_payment_due_date = order.date_order.date() + timedelta(
                    days=order.company_id.early_payment_days
                )
            else:
                order.early_payment_due_date = False
    
    @api.depends('amount_total', 'payment_reference', 'bank_account_to_show')
    def _compute_payment_qr(self):
        for order in self:
            if (order.company_id.enable_payment_qr and 
                order.amount_total > 0 and 
                (order.bank_account_to_show or order.company_id.primary_bank_account)):
                order.payment_qr_code = order._generate_payment_qr()
            else:
                order.payment_qr_code = False
    
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
        for order in self:
            if order.payment_reference:
                existing = self.search([
                    ('payment_reference', '=', order.payment_reference),
                    ('company_id', '=', order.company_id.id),
                    ('id', '!=', order.id)
                ])
                if existing:
                    raise ValidationError(
                        f'Ya existe otro pedido con la referencia de pago {order.payment_reference}'
                    )

    def _prepare_invoice(self):
        """Heredar datos de pago al crear factura desde pedido"""
        invoice_vals = super()._prepare_invoice()
        
        # Transferir información de pago del pedido a la factura
        # NOTA: NO transferimos payment_reference porque la factura debe usar su propio número
        invoice_vals.update({
            'show_bank_info': self.show_bank_info,
            'show_payment_qr': self.show_payment_qr,
            'show_early_discount': self.show_early_discount,
            'custom_payment_instructions': self.custom_payment_instructions,
            'available_payment_methods': [(6, 0, self.available_payment_methods.ids)],
            'preferred_payment_method': self.preferred_payment_method.id if self.preferred_payment_method else False,
            'bank_account_to_show': self.bank_account_to_show.id if self.bank_account_to_show else False,
            'payment_urgency': self.payment_urgency,
        })
        
        return invoice_vals
