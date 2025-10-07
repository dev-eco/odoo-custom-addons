import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # Campos de trazabilidad para documentos automatizados
    document_scan_id = fields.Many2one(
        'document.scan',
        string='Documento Original',
        readonly=True,
        copy=False,
        help='Documento escaneado que originó esta factura'
    )
    
    is_auto_processed = fields.Boolean(
        string="Procesada automáticamente",
        readonly=True,
        default=False,
        help="Indica si la factura fue procesada mediante el sistema de automatización",
        copy=False
    )
    
    auto_processing_confidence = fields.Float(
        string="Nivel de confianza OCR",
        readonly=True,
        help="Puntuación de confianza del procesamiento automático (0-100%)",
        copy=False
    )
    
    auto_processing_date = fields.Datetime(
        string="Fecha de procesamiento",
        readonly=True,
        copy=False
    )
    
    def write(self, vals):
        """Sobrescribe el método write para mantener referencia al documento original"""
        # Si hay un documento original y se está validando la factura
        if vals.get('state') == 'posted' and any(move.document_scan_id for move in self):
            for move in self.filtered(lambda m: m.document_scan_id):
                # Actualizamos el documento original para indicar que se ha validado
                if move.document_scan_id and move.document_scan_id.status == 'processed':
                    move.document_scan_id.sudo().write({
                        'is_auto_validated': True,
                        'notes': f"{move.document_scan_id.notes or ''}\n\nDocumento validado manualmente."
                    })
                    
                    # Añadimos entrada en el log
                    self.env['document.scan.log'].sudo().create({
                        'document_id': move.document_scan_id.id,
                        'user_id': self.env.user.id,
                        'action': 'status_change',
                        'description': _('Documento validado manualmente por %s') % self.env.user.name
                    })
        
        return super(AccountMove, self).write(vals)
    
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """Sobrescribe método para procesar emails entrantes con documentos adjuntos"""
        # Primero llamamos al método original para crear la factura
        res = super(AccountMove, self).message_new(msg_dict, custom_values)
        
        # Configuramos para que sea identificable como procesada automáticamente
        res.write({
            'is_auto_processed': True,
            'auto_processing_date': fields.Datetime.now(),
        })
        
        try:
            # Procesamos los adjuntos PDF
            if msg_dict.get('attachments'):
                for attachment in msg_dict.get('attachments'):
                    filename = attachment[0]
                    file_content = attachment[1]
                    
                    # Si es un PDF, registramos como documento escaneado
                    if filename.lower().endswith('.pdf'):
                        # Crear documento escaneado
                        doc_scan = self.env['document.scan'].sudo().create({
                            'name': filename,
                            'source': 'email',
                            'status': 'pending',
                            'document_type_code': 'invoice',  # Por defecto asumimos factura
                            'notes': f"Recibido por email: {msg_dict.get('subject', '')}",
                        })
                        
                        # Crear adjunto para el documento
                        attachment_id = self.env['ir.attachment'].sudo().create({
                            'name': filename,
                            'datas': file_content,
                            'res_model': 'document.scan',
                            'res_id': doc_scan.id,
                            'mimetype': 'application/pdf'
                        })
                        
                        # Vincular adjunto al documento
                        doc_scan.attachment_id = attachment_id.id
                        
                        # Vincular documento escaneado a la factura
                        res.document_scan_id = doc_scan.id
                        
                        # Actualizar documento escaneado con referencia a la factura
                        doc_scan.write({
                            'result_model': 'account.move',
                            'result_record_id': res.id,
                            'status': 'processed',
                        })
                        
                        # Registrar en el log
                        self.env['document.scan.log'].sudo().create({
                            'document_id': doc_scan.id,
                            'user_id': self.env.user.id,
                            'action': 'create_target',
                            'description': _('Factura creada automáticamente desde email: %s') % res.name
                        })
        
        except Exception as e:
            _logger.error(f"Error procesando documento por email: {str(e)}")
        
        return res
