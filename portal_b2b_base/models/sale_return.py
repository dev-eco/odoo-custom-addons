# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleReturn(models.Model):
    """Devoluciones de venta (RMA) para distribuidores."""
    
    _name = 'sale.return'
    _description = 'Devolución de Venta'
    _order = 'create_date desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Número RMA',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nuevo')
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    order_id = fields.Many2one(
        'sale.order',
        string='Pedido Original',
        ondelete='set null',
        help='Pedido de venta original'
    )
    
    return_date = fields.Date(
        string='Fecha Devolución',
        default=fields.Date.today,
        required=True
    )
    
    received_date = fields.Datetime(
        string='Fecha Recepción',
        readonly=True,
        help='Fecha en que se recibió la devolución'
    )
    
    reason = fields.Selection([
        ('defective', 'Producto Defectuoso'),
        ('wrong_item', 'Producto Incorrecto'),
        ('damaged', 'Dañado en Transporte'),
        ('not_needed', 'No Necesario'),
        ('quality', 'Problema de Calidad'),
        ('other', 'Otro'),
    ], string='Motivo', required=True)
    
    reason_description = fields.Text(
        string='Descripción del Motivo',
        help='Descripción detallada del motivo de devolución'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('submitted', 'Enviado'),
        ('received', 'Recibido'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
        ('processed', 'Procesado'),
    ], string='Estado', default='draft', tracking=True)
    
    line_ids = fields.One2many(
        'sale.return.line',
        'return_id',
        string='Líneas de Devolución',
        copy=True
    )
    
    total_amount = fields.Monetary(
        string='Total Devolución',
        currency_field='currency_id',
        compute='_compute_total_amount',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )
    
    notes = fields.Text(
        string='Notas Internas'
    )
    
    customer_notes = fields.Text(
        string='Notas del Distribuidor',
        help='Notas adicionales del distribuidor'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'sale_return_attachment_rel',
        'return_id',
        'attachment_id',
        string='Documentos'
    )
    
    approval_date = fields.Datetime(
        string='Fecha Aprobación',
        readonly=True
    )
    
    approval_user_id = fields.Many2one(
        'res.users',
        string='Aprobado por',
        readonly=True
    )
    
    rejection_reason = fields.Text(
        string='Motivo Rechazo',
        readonly=True
    )
    
    refund_method = fields.Selection([
        ('credit_note', 'Nota de Crédito'),
        ('refund', 'Reembolso'),
        ('replacement', 'Reemplazo'),
        ('store_credit', 'Crédito en Cuenta'),
    ], string='Método de Reembolso', default='credit_note')
    
    credit_note_id = fields.Many2one(
        'account.move',
        string='Nota de Crédito',
        readonly=True,
        help='Nota de crédito generada'
    )
    
    @api.depends('line_ids', 'line_ids.subtotal')
    def _compute_total_amount(self):
        """Calcula el total de la devolución."""
        for return_obj in self:
            return_obj.total_amount = sum(return_obj.line_ids.mapped('subtotal'))
    
    @api.model
    def create(self, vals):
        """Override para generar número RMA."""
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.return') or _('Nuevo')
        
        return super().create(vals)
    
    def action_submit(self):
        """Envía la devolución para aprobación."""
        self.ensure_one()
        
        if not self.line_ids:
            raise ValidationError(_('Debe agregar al menos una línea de devolución'))
        
        self.write({'state': 'submitted'})
        
        _logger.info(f"Devolución {self.name} enviada por {self.env.user.login}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Devolución Enviada'),
                'message': _('Su devolución ha sido enviada para aprobación.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_mark_received(self):
        """Marca la devolución como recibida."""
        self.ensure_one()
        
        self.write({
            'state': 'received',
            'received_date': fields.Datetime.now(),
        })
        
        _logger.info(f"Devolución {self.name} marcada como recibida")
    
    def action_approve(self):
        """Aprueba la devolución (solo usuarios internos)."""
        self.ensure_one()
        
        self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now(),
            'approval_user_id': self.env.user.id,
        })
        
        _logger.info(f"Devolución {self.name} aprobada por {self.env.user.login}")
    
    def action_reject(self, reason):
        """Rechaza la devolución."""
        self.ensure_one()
        
        self.write({
            'state': 'rejected',
            'rejection_reason': reason,
        })
        
        _logger.info(f"Devolución {self.name} rechazada por {self.env.user.login}")
    
    def action_process(self):
        """Procesa la devolución y genera nota de crédito si aplica."""
        self.ensure_one()
        
        if self.state != 'approved':
            raise ValidationError(_('La devolución debe estar aprobada'))
        
        # Generar nota de crédito si es necesario
        if self.refund_method == 'credit_note':
            self._create_credit_note()
        
        self.write({'state': 'processed'})
        
        _logger.info(f"Devolución {self.name} procesada")
    
    def action_close(self):
        """Cierra la devolución."""
        self.ensure_one()
        self.write({'state': 'processed'})
        
        _logger.info(f"Devolución {self.name} cerrada")
    
    def _create_credit_note(self):
        """Crea una nota de crédito para la devolución."""
        self.ensure_one()
        
        # Crear líneas de nota de crédito
        invoice_lines = []
        for line in self.line_ids:
            invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'name': f'Devolución: {line.product_id.name}',
            }))
        
        # Crear nota de crédito
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': invoice_lines,
            'ref': f'Devolución {self.name}',
        })
        
        self.credit_note_id = credit_note.id
        
        _logger.info(f"Nota de crédito {credit_note.name} creada para devolución {self.name}")
    
    def action_close(self):
        """Cierra la devolución."""
        self.ensure_one()
        self.write({'state': 'closed'})


class SaleReturnLine(models.Model):
    """Líneas de devolución."""
    
    _name = 'sale.return.line'
    _description = 'Línea de Devolución'
    _order = 'sequence, id'
    
    return_id = fields.Many2one(
        'sale.return',
        string='Devolución',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='restrict'
    )
    
    quantity = fields.Float(
        string='Cantidad',
        default=1.0,
        required=True
    )
    
    unit_price = fields.Monetary(
        string='Precio Unitario',
        currency_field='currency_id',
        required=True
    )
    
    subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='return_id.currency_id',
        store=True
    )
    
    condition = fields.Selection([
        ('new', 'Nuevo'),
        ('used', 'Usado'),
        ('damaged', 'Dañado'),
        ('defective', 'Defectuoso'),
    ], string='Condición', default='new')
    
    notes = fields.Text(
        string='Notas'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )
    
    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        """Calcula el subtotal de la línea."""
        for line in self:
            line.subtotal = line.quantity * line.unit_price
    
    @api.constrains('quantity')
    def _check_quantity(self):
        """Valida que la cantidad sea positiva."""
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('La cantidad debe ser mayor a 0'))
