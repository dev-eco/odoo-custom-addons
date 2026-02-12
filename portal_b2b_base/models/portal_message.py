# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PortalMessage(models.Model):
    """Mensajes de chat entre distribuidor y empresa."""
    
    _name = 'portal.message'
    _description = 'Mensaje Portal B2B'
    _order = 'create_date desc'
    _rec_name = 'subject'
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    subject = fields.Char(
        string='Asunto',
        required=True,
        tracking=True
    )
    
    message = fields.Text(
        string='Mensaje',
        required=True
    )
    
    body = fields.Html(
        string='Cuerpo HTML',
        help='Versión HTML del mensaje'
    )
    
    sender_type = fields.Selection([
        ('distributor', 'Distribuidor'),
        ('company', 'Empresa'),
    ], string='Remitente', required=True, default='distributor')
    
    sender_user_id = fields.Many2one(
        'res.users',
        string='Usuario Remitente',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsable',
        help='Usuario asignado para responder'
    )
    
    is_read = fields.Boolean(
        string='Leído',
        default=False,
        index=True,
        tracking=True
    )
    
    read_date = fields.Datetime(
        string='Fecha Lectura',
        readonly=True
    )
    
    related_model = fields.Char(
        string='Modelo Relacionado',
        help='Modelo del registro relacionado (ej: sale.order)'
    )
    
    related_id = fields.Integer(
        string='ID Relacionado',
        help='ID del registro relacionado'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'portal_message_attachment_rel',
        'message_id',
        'attachment_id',
        string='Adjuntos'
    )
    
    parent_id = fields.Many2one(
        'portal.message',
        string='Mensaje Padre',
        ondelete='cascade',
        help='Para respuestas en hilo'
    )
    
    child_ids = fields.One2many(
        'portal.message',
        'parent_id',
        string='Respuestas'
    )
    
    reply_count = fields.Integer(
        string='Número de Respuestas',
        compute='_compute_reply_count',
        store=True
    )
    
    priority = fields.Selection([
        ('low', 'Baja'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ], string='Prioridad', default='normal', tracking=True)
    
    state = fields.Selection([
        ('open', 'Abierto'),
        ('answered', 'Respondido'),
        ('closed', 'Cerrado'),
    ], string='Estado', default='open', tracking=True)
    
    message_type = fields.Selection([
        ('inquiry', 'Consulta'),
        ('complaint', 'Reclamación'),
        ('suggestion', 'Sugerencia'),
        ('support', 'Soporte'),
        ('other', 'Otro'),
    ], string='Tipo', default='inquiry')
    
    @api.depends('child_ids')
    def _compute_reply_count(self):
        """Calcula el número de respuestas."""
        for message in self:
            message.reply_count = len(message.child_ids)
    
    def action_mark_read(self):
        """Marca el mensaje como leído."""
        self.ensure_one()
        self.write({
            'is_read': True,
            'read_date': fields.Datetime.now(),
        })
        
        _logger.info(f"Mensaje {self.id} marcado como leído por {self.env.user.login}")
    
    def action_reply(self):
        """Acción para responder al mensaje."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Responder Mensaje'),
            'res_model': 'portal.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_parent_id': self.id,
                'default_subject': f'Re: {self.subject}',
                'default_sender_type': 'company',
            },
        }
    
    def action_close(self):
        """Cierra el mensaje."""
        self.ensure_one()
        self.write({'state': 'closed'})
        
        _logger.info(f"Mensaje {self.id} cerrado por {self.env.user.login}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mensaje Cerrado'),
                'message': _('El mensaje ha sido cerrado.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def get_unread_count(self, partner_id, sender_type=None):
        """
        Obtiene el número de mensajes no leídos.
        
        Args:
            partner_id: ID del partner
            sender_type: Filtrar por tipo de remitente
        
        Returns:
            int: Número de mensajes no leídos
        """
        domain = [
            ('partner_id', '=', partner_id),
            ('is_read', '=', False),
        ]
        
        if sender_type:
            domain.append(('sender_type', '=', sender_type))
        
        return self.search_count(domain)
    
    @api.model
    def get_recent_messages(self, partner_id, limit=20):
        """
        Obtiene los mensajes recientes.
        
        Args:
            partner_id: ID del partner
            limit: Número máximo de mensajes
        
        Returns:
            list: Lista de mensajes formateados
        """
        messages = self.search([
            ('partner_id', '=', partner_id),
            ('parent_id', '=', False),  # Solo mensajes principales
        ], limit=limit, order='create_date desc')
        
        return [
            {
                'id': m.id,
                'subject': m.subject,
                'message': m.message,
                'sender_type': m.sender_type,
                'sender_name': m.sender_user_id.name,
                'is_read': m.is_read,
                'create_date': m.create_date.strftime('%d/%m/%Y %H:%M'),
                'priority': m.priority,
                'state': m.state,
                'reply_count': m.reply_count,
            }
            for m in messages
        ]
    
    def create(self, vals):
        """Override para validaciones y notificaciones."""
        # Si no hay body HTML, usar el mensaje de texto
        if 'body' not in vals and 'message' in vals:
            vals['body'] = f'<p>{vals["message"]}</p>'
        
        message = super().create(vals)
        
        # Crear notificación si es mensaje de empresa a distribuidor
        if message.sender_type == 'company' and message.partner_id:
            try:
                self.env['portal.notification'].sudo().create_notification(
                    partner_id=message.partner_id.id,
                    title=f'Nuevo Mensaje: {message.subject}',
                    message=f'Ha recibido un nuevo mensaje de la empresa.',
                    notification_type='info',
                    action_url=f'/mis-mensajes/{message.id}',
                    related_model='portal.message',
                    related_id=message.id,
                )
            except Exception as e:
                _logger.warning(f"No se pudo crear notificación: {str(e)}")
        
        _logger.info(f"Mensaje {message.id} creado por {self.env.user.login}")
        
        return message
    
    def write(self, vals):
        """Override para actualizar estado cuando se responde."""
        result = super().write(vals)
        
        # Si se añade una respuesta, actualizar estado del padre
        if 'parent_id' in vals and vals['parent_id']:
            parent = self.env['portal.message'].browse(vals['parent_id'])
            if parent.exists() and parent.state == 'open':
                parent.write({'state': 'answered'})
        
        return result
