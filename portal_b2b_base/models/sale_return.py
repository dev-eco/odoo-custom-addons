# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleReturn(models.Model):
    """Devoluciones de venta (RMA) para distribuidores."""
    
    _name = 'sale.return'
    _description = 'Devolución de Venta'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Número RMA',
        required=True,
        copy=False,
        readonly=True,
        default='/'
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
    
    available_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_available_products',
        string='Productos Disponibles',
        help='Productos del pedido original'
    )

    @api.depends('line_ids', 'line_ids.subtotal')
    def _compute_total_amount(self):
        """Calcula el total de la devolución."""
        for return_obj in self:
            return_obj.total_amount = sum(return_obj.line_ids.mapped('subtotal'))

    @api.depends('order_id', 'order_id.order_line', 'order_id.order_line.product_id')
    def _compute_available_products(self):
        """Calcula los productos disponibles del pedido original."""
        for return_obj in self:
            if return_obj.order_id:
                products = return_obj.order_id.order_line.mapped('product_id')
                return_obj.available_product_ids = [(6, 0, products.ids)]
            else:
                return_obj.available_product_ids = [(5, 0, 0)]
    
    @api.model
    def create(self, vals):
        """Override para generar número RMA solo si es usuario interno."""
        # Si es usuario portal, dejar como borrador sin secuencia
        if not self.env.user.has_group('base.group_user'):
            vals['name'] = '/'
        else:
            # Usuario interno: generar secuencia inmediatamente
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.return') or '/'
        
        return super().create(vals)
    
    def action_submit(self):
        """Envía la devolución para aprobación y notifica por email."""
        self.ensure_one()
        
        if not self.line_ids:
            raise ValidationError(_('Debe agregar al menos una línea de devolución'))
        
        self.write({'state': 'submitted'})
        
        # Enviar email automático
        self._send_return_notification_email()
        
        _logger.info(f"Devolución enviada por {self.env.user.login}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Devolución Enviada'),
                'message': _('Su solicitud de devolución ha sido enviada para revisión.'),
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
        """Aprueba la devolución y genera código RMA oficial."""
        self.ensure_one()
        
        # Generar código RMA si aún no tiene
        if self.name == '/' or not self.name or self.name == _('Nuevo'):
            self.name = self.env['ir.sequence'].next_by_code('sale.return') or '/'
        
        self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now(),
            'approval_user_id': self.env.user.id,
        })
        
        # Notificar al distribuidor
        self.message_post(
            body=f"✅ Su devolución {self.name} ha sido aprobada.",
            subject="Devolución Aprobada",
            message_type='notification',
            partner_ids=[self.partner_id.id]
        )
        
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

    @api.model
    def get_distributor_orders_with_products(self, partner_id):
        """
        Obtiene pedidos del distribuidor con sus productos para devolución.
        
        Args:
            partner_id: ID del distribuidor
        
        Returns:
            dict: Pedidos agrupados con productos
        """
        orders = self.env['sale.order'].search([
            ('partner_id', '=', partner_id),
            ('state', 'in', ['sale', 'done']),
        ], order='date_order desc', limit=20)
        
        orders_data = []
        for order in orders:
            products = []
            for line in order.order_line:
                if line.product_id and line.product_uom_qty > 0:
                    products.append({
                        'id': line.product_id.id,
                        'name': line.product_id.name,
                        'default_code': line.product_id.default_code or '',
                        'quantity_ordered': line.product_uom_qty,
                        'price_unit': line.price_unit,
                        'uom_name': line.product_uom.name,
                    })
            
            if products:  # Solo incluir pedidos con productos
                orders_data.append({
                    'id': order.id,
                    'name': order.name,
                    'date_order': order.date_order.strftime('%d/%m/%Y'),
                    'amount_total': order.amount_total,
                    'products': products,
                })
        
        return orders_data

    def action_submit(self):
        """Override para enviar email automático."""
        result = super().action_submit()
        
        # Enviar email automático
        self._send_return_notification_email()
        
        return result

    def _send_return_notification_email(self):
        """Envía notificación por email de nueva devolución."""
        self.ensure_one()
        
        try:
            # Obtener email configurado
            email_to = self.env['ir.config_parameter'].sudo().get_param(
                'portal_b2b_base.return_notification_email',
                'pedidos@ecocaucho.info'
            )
            
            # Preparar datos del email
            email_values = {
                'email_to': email_to,
                'email_from': self.env.company.email or 'noreply@ecocaucho.info',
                'subject': f'Nueva Solicitud de Devolución - {self.partner_id.name}',
                'body_html': self._get_return_email_body(),
                'auto_delete': False,
            }
            
            # Crear y enviar email
            mail = self.env['mail.mail'].sudo().create(email_values)
            mail.send()
            
            _logger.info(f"Email de devolución enviado a {email_to}")
            
        except Exception as e:
            _logger.error(f"Error enviando email de devolución: {str(e)}")

    def _get_return_email_body(self):
        """Genera el cuerpo HTML del email de devolución."""
        self.ensure_one()
        
        lines_html = ""
        for line in self.line_ids:
            lines_html += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{line.product_id.name}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{line.quantity}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{line.unit_price:.2f} €</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{line.subtotal:.2f} €</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{line.condition}</td>
        </tr>
        """
        
        return f"""
    <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #0066CC; border-bottom: 2px solid #0066CC; padding-bottom: 10px;">
            Nueva Solicitud de Devolución
        </h2>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #333;">Información del Distribuidor</h3>
            <p><strong>Distribuidor:</strong> {self.partner_id.name}</p>
            <p><strong>Email:</strong> {self.partner_id.email or 'No especificado'}</p>
            <p><strong>Teléfono:</strong> {self.partner_id.phone or 'No especificado'}</p>
            <p><strong>Fecha Devolución:</strong> {self.return_date.strftime('%d/%m/%Y')}</p>
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #333;">Detalles de la Devolución</h3>
            <p><strong>Motivo:</strong> {dict(self._fields['reason'].selection).get(self.reason)}</p>
            {f'<p><strong>Pedido Original:</strong> {self.order_id.name}</p>' if self.order_id else ''}
            {f'<p><strong>Descripción:</strong> {self.reason_description}</p>' if self.reason_description else ''}
        </div>
        
        <div style="margin: 20px 0;">
            <h3 style="color: #333;">Productos a Devolver</h3>
            <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                <thead>
                    <tr style="background: #0066CC; color: white;">
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: left;">Producto</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Cantidad</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: right;">Precio Unit.</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: right;">Subtotal</th>
                        <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Condición</th>
                    </tr>
                </thead>
                <tbody>
                    {lines_html}
                </tbody>
                <tfoot>
                    <tr style="background: #f8f9fa; font-weight: bold;">
                        <td colspan="3" style="padding: 12px; border: 1px solid #ddd; text-align: right;">TOTAL:</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right;">{self.total_amount:.2f} €</td>
                        <td style="padding: 12px; border: 1px solid #ddd;"></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        
        {f'''
        <div style="margin: 20px 0;">
            <h3 style="color: #333;">Notas del Distribuidor</h3>
            <p style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; border-radius: 3px;">
                {self.customer_notes}
            </p>
        </div>
        ''' if self.customer_notes else ''}
        
        <div style="margin: 30px 0; padding: 20px; background: #e7f3ff; border-radius: 5px;">
            <p style="margin: 0; color: #0066CC; font-weight: bold;">
                ⚠️ Esta devolución requiere revisión y aprobación en el sistema.
            </p>
            <p style="margin: 10px 0 0 0; font-size: 14px; color: #666;">
                Accede al backend de Odoo para gestionar esta devolución.
            </p>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666;">
            <p>Email generado automáticamente por el Portal B2B - {fields.Datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
    </div>
    """


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
