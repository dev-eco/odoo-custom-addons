# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import logging
import time

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
        ('processed', 'Procesado'),
        ('manual', 'Revisión Manual'),
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
    
    def action_view_result(self):
    """Abre el documento resultado en una vista de formulario"""
    self.ensure_one()
    
    if not self.result_model or not self.result_record_id:
        raise UserError(_("No hay documento resultado asociado"))
    
    # Verificamos que el modelo y registro existan
    record = self.env[self.result_model].sudo().browse(self.result_record_id)
    if not record.exists():
        raise UserError(_("El documento resultado ya no existe"))
    
    # Creamos la acción para abrir el documento
    action = {
        'type': 'ir.actions.act_window',
        'name': _('Documento Resultado'),
        'res_model': self.result_model,
        'res_id': self.result_record_id,
        'view_mode': 'form',
        'target': 'current',
    }
    
    # Si es una factura, usamos la acción predefinida para facturas
    if self.result_model == 'account.move':
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
        action['res_id'] = self.result_record_id
    
    # Si es un albarán, usamos la acción predefinida para albaranes
    elif self.result_model == 'stock.picking':
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
        action['res_id'] = self.result_record_id
    
    return action

    def action_reset(self):
        """Reinicia el estado de procesamiento del documento para intentarlo de nuevo"""
        self.ensure_one()
        
        # Verificamos que no esté en estado pendiente
        if self.status == 'pending':
            return
        
        # Volvemos a poner en estado pendiente
        self.write({
            'status': 'pending',
            'processed_date': False,
            'confidence_score': 0.0,
            'processing_time': 0.0,
        })
        
        self._add_log('info', 'Documento reiniciado para nuevo procesamiento')
        
        return True

    def action_force_manual(self):
        """Marca el documento para revisión manual"""
        self.ensure_one()
        
        # Si ya está en revisión manual, no hacemos nada
        if self.status == 'manual':
            return
        
        # Marcamos para revisión manual
        self.write({
            'status': 'manual',
            'processed_date': fields.Datetime.now(),
        })
        
        self._add_log('warning', 'Documento marcado para revisión manual')
        
        return True

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
        
    @api.model
    def _cron_check_email_documents(self):
        """Proceso programado para verificar documentos en correos electrónicos
        
        Este método busca nuevos correos electrónicos en las bandejas de entrada configuradas,
        extrae los adjuntos y los procesa como documentos.
        """
        _logger.info("Iniciando verificación de documentos por correo electrónico")
        
        try:
            # Obtenemos configuración
            config = self.env['ir.config_parameter'].sudo()
            enabled = config.get_param('document_automation.email_enabled', 'false').lower() == 'true'
            
            if not enabled:
                _logger.info("Procesamiento de correos desactivado en configuración")
                return
                
            # Aquí implementaríamos la lógica real para procesar correos
            # Por ahora, solo registramos una ejecución
            _logger.info("Verificación de documentos por correo electrónico completada")
            
        except Exception as e:
            _logger.error(f"Error al verificar documentos por correo: {e}")
    
    @api.model
    def _cron_process_ocr_queue(self):
        """Proceso programado para procesar la cola de OCR
        
        Este método busca documentos pendientes de procesamiento OCR
        y los procesa en orden de prioridad.
        """
        _logger.info("Iniciando procesamiento de cola OCR")
        
        try:
            # Buscamos documentos pendientes
            docs_to_process = self.search([
                ('status', '=', 'pending'),
                ('attachment_id', '!=', False)
            ], limit=10, order='create_date asc')
            
            if not docs_to_process:
                _logger.info("No hay documentos pendientes en la cola OCR")
                return
                
            # Procesamos cada documento
            processed_count = 0
            for doc in docs_to_process:
                try:
                    start_time = time.time()
                    result = doc.action_process()
                    processing_time = time.time() - start_time
                    
                    if result:
                        doc.write({'processing_time': processing_time})
                        processed_count += 1
                        
                except Exception as e:
                    _logger.error(f"Error procesando documento {doc.id}: {e}")
                    doc.write({'status': 'error'})
                    doc._add_log('error', f"Error en procesamiento automático: {e}")
            
            _logger.info(f"Procesamiento de cola OCR completado. Documentos procesados: {processed_count}")
            
        except Exception as e:
            _logger.error(f"Error al procesar cola OCR: {e}")
