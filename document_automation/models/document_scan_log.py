# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DocumentScanLog(models.Model):
    _name = 'document.scan.log'
    _description = 'Log de Documento Escaneado'
    _order = 'create_date desc'
    
    document_id = fields.Many2one('document.scan', string='Documento', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user.id)
    type = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
        ('success', 'Éxito'),
    ], string='Tipo', default='info')
    description = fields.Text(string='Descripción', required=True)
    action = fields.Char(string='Acción', compute='_compute_action')
    
    @api.depends('type', 'description')
    def _compute_action(self):
        """Calcula la acción basada en el tipo y descripción"""
        for record in self:
            if record.type == 'info':
                record.action = 'Información'
            elif record.type == 'warning':
                record.action = 'Advertencia'
            elif record.type == 'error':
                record.action = 'Error'
            elif record.type == 'success':
                record.action = 'Éxito'
            else:
                record.action = 'Desconocido'
