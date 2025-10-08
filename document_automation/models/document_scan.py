# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class DocumentScan(models.Model):
    _name = 'document.scan'
    _description = 'Documento Escaneado'
    _order = 'create_date desc'
    
    name = fields.Char(string='Nombre', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Archivo', ondelete='cascade')
    document_type_id = fields.Many2one('document.type', string='Tipo de Documento')
    document_type_code = fields.Char(string='Código de Tipo', index=True)
    
    source = fields.Selection([
        ('scanner', 'Escáner Local'),
        ('email', 'Correo Electrónico'),
        ('api', 'API Externa')
    ], string='Fuente', default='scanner', required=True)
    
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('done', 'Completado'),
        ('error', 'Error')
    ], string='Estado', default='pending', required=True)
    
    confidence_score = fields.Float(string='Confianza OCR', default=0.0)
    processed_date = fields.Datetime(string='Fecha de Procesamiento')
    processing_time = fields.Float(string='Tiempo de Procesamiento (s)', default=0.0)
    is_auto_validated = fields.Boolean(string='Validación Automática', default=False)
    
    result_model = fields.Char(string='Modelo Resultante', index=True)
    result_record_id = fields.Integer(string='ID Registro Resultante')
    result_url = fields.Char(string='URL Resultado', compute='_compute_result_url')
    
    notes = fields.Text(string='Notas')
    ocr_text = fields.Text(string='Texto OCR')
    ocr_data = fields.Text(string='Datos OCR')
    
    log_ids = fields.One2many('document.scan.log', 'document_id', string='Logs')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    
    document_preview = fields.Binary(related='attachment_id.datas', string='Vista previa')
    
    @api.depends('result_model', 'result_record_id')
    def _compute_result_url(self):
        """Calcula la URL del resultado para acceso directo"""
        for record in self:
            if record.result_model and record.result_record_id:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                record.result_url = f"{base_url}/web#model={record.result_model}&id={record.result_record_id}"
            else:
                record.result_url = False
    
    def action_process(self):
        """Procesa el documento manualmente"""
        self.ensure_one()
        
        if not self.attachment_id:
            self._add_log('error', 'No hay archivo adjunto para procesar')
            return False
            
        # Cambiamos el estado a procesando
        self.write({
            'status': 'processing',
        })
        
        # Procesamiento real aquí - por ahora simulado
        self._add_log('info', 'Iniciando procesamiento OCR')
        
        try:
            # Aquí añadirías el procesamiento real
            # Por ejemplo:
            # - OCR del documento
            # - Extracción de campos
            # - Creación de documentos correspondientes
            
            # Por ahora, solo actualizamos el estado
            self.write({
                'status': 'done',
                'processed_date': fields.Datetime.now(),
                'confidence_score': 0.95,
            })
            
            self._add_log('success', 'Procesamiento completado con éxito')
            return True
            
        except Exception as e:
            _logger.error(f"Error en el procesamiento del documento {self.id}: {e}")
            self.write({
                'status': 'error'
            })
            self._add_log('error', f'Error en procesamiento: {str(e)}')
            return False
    
    def _add_log(self, log_type, description):
        """Añade una entrada de log al documento"""
        self.ensure_one()
        
        self.env['document.scan.log'].create({
            'document_id': self.id,
            'type': log_type,
            'description': description,
            'user_id': self.env.user.id,
        })

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
