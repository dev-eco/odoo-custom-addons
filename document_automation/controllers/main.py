import base64
import json
import logging
import hmac
import hashlib
from datetime import datetime
import traceback

from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import AccessDenied, ValidationError

_logger = logging.getLogger(__name__)

class DocumentAutomationController(http.Controller):
    
    @http.route('/api/v1/document/scan', type='json', auth='none', methods=['POST'], csrf=False)
    def receive_scanned_document(self, **post):
        """Endpoint para recibir documentos escaneados desde el cliente externo"""
        try:
            # Verificamos la autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            timestamp = headers.get('X-Timestamp')
            signature = headers.get('X-Signature')
            
            # Validamos la API Key
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key')
            api_secret = api_config.get_param('document_automation.api_secret')
            
            # Si la API Key no está configurada, rechazamos
            if not valid_api_key or not api_secret:
                _logger.error("API Key no configurada en el sistema")
                return self._json_response(
                    success=False, 
                    message="API no configurada", 
                    status=500
                )
                
            # Verificamos la API key
            if api_key != valid_api_key:
                _logger.error(f"API Key inválida: {api_key}")
                return self._json_response(
                    success=False, 
                    message="Autenticación fallida", 
                    status=401
                )
            
            # Verificamos la firma HMAC para mayor seguridad
            if timestamp and signature:
                expected_signature = hmac.new(
                    api_secret.encode('utf-8'),
                    f"{api_key}{timestamp}".encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                if signature != expected_signature:
                    _logger.error(f"Firma de seguridad inválida: {signature} != {expected_signature}")
                    return self._json_response(
                        success=False,
                        message="Firma de seguridad inválida",
                        status=401
                    )
            else:
                _logger.warning("Petición sin firma de seguridad")
            
            # Procesamos la petición
            data = request.jsonrequest
            
            # Validamos datos mínimos requeridos
            if not data.get('pdf_file_b64'):
                return self._json_response(
                    success=False, 
                    message="Datos incompletos: se requiere el archivo PDF", 
                    status=400
                )
            
            # Obtenemos tipo de documento si se especificó
            document_type_code = data.get('document_type', 'generic')
            
            # Decodificamos el archivo PDF en Base64
            pdf_data = base64.b64decode(data['pdf_file_b64'])
            filename = data.get('filename', f"documento_escaneado_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
            
            # Metadatos adicionales
            metadata = {
                'source': 'scanner',
                'scanner_name': data.get('scanner_name', 'Unknown'),
                'document_type': document_type_code,
                'scan_date': datetime.now().isoformat(),
                'scan_user': data.get('user', 'Sistema'),
                'notes': data.get('notes', ''),
                'client_version': data.get('client_version', 'Unknown')
            }
            
            # Procesamos el documento con el modelo adecuado
            document = request.env['document.scan'].sudo().create({
                'name': filename,
                'document_type_code': document_type_code,
                'source': 'scanner',
                'status': 'pending',
                'metadata': json.dumps(metadata),
                'notes': data.get('notes', ''),
            })
            
            # Adjuntamos el PDF
            attachment = request.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_data),
                'res_model': 'document.scan',
                'res_id': document.id,
                'mimetype': 'application/pdf'
            })
            
            # Asignamos el adjunto al documento
            document.attachment_id = attachment.id
            
            # Iniciamos procesamiento OCR si está configurado para ser automático
            auto_process = api_config.get_param('document_automation.auto_process', 'false').lower() == 'true'
            if auto_process:
                document.action_process()
            
            # Retornamos respuesta exitosa
            return self._json_response(
                success=True,
                message="Documento recibido correctamente",
                document_id=document.id,
                status=200
            )
            
        except Exception as e:
            _logger.error(f"Error al procesar documento escaneado: {str(e)}")
            _logger.error(traceback.format_exc())
            return self._json_response(
                success=False,
                message=f"Error interno: {str(e)}",
                status=500
            )
    
    @http.route('/api/v1/document/types', type='json', auth='none', methods=['GET'], csrf=False)
    def get_document_types(self, **post):
        """Endpoint para obtener los tipos de documentos disponibles"""
        try:
            # Verificamos la autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            
            # Validamos la API Key
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key')
            
            if not valid_api_key or api_key != valid_api_key:
                _logger.error("API Key inválida o no configurada")
                return self._json_response(
                    success=False, 
                    message="Autenticación fallida", 
                    status=401
                )
            
            # Obtenemos los tipos de documentos activos
            doc_types = request.env['document.type'].sudo().search([('active', '=', True)])
            
            # Formateamos la respuesta
            types_data = []
            for doc_type in doc_types:
                types_data.append({
                    'id': doc_type.id,
                    'name': doc_type.name,
                    'code': doc_type.code,
                    'description': doc_type.description,
                    'sequence': doc_type.sequence,
                })
            
            return self._json_response(
                success=True,
                document_types=types_data,
                status=200
            )
            
        except Exception as e:
            _logger.error(f"Error al obtener tipos de documento: {str(e)}")
            return self._json_response(
                success=False,
                message=f"Error interno: {str(e)}",
                status=500
            )
    
    @http.route('/api/v1/document/status/<int:document_id>', type='json', auth='none', methods=['GET'], csrf=False)
    def get_document_status(self, document_id, **post):
        """Endpoint para verificar el estado de un documento procesado"""
        try:
            # Verificamos la autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            
            # Validamos la API Key
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key')
            
            if not valid_api_key or api_key != valid_api_key:
                _logger.error("API Key inválida o no configurada")
                return self._json_response(
                    success=False, 
                    message="Autenticación fallida", 
                    status=401
                )
            
            # Obtenemos el documento
            document = request.env['document.scan'].sudo().browse(document_id)
            
            if not document.exists():
                return self._json_response(
                    success=False,
                    message="Documento no encontrado",
                    status=404
                )
            
            # Preparamos información del documento
            result_model = document.result_model
            result_record_id = document.result_record_id
            
            result_data = None
            if result_model and result_record_id:
                record = request.env[result_model].sudo().browse(result_record_id)
                if record.exists():
                    # Información básica del registro creado
                    result_data = {
                        'id': record.id,
                        'model': result_model,
                        'name': record.display_name,
                    }
            
            # Formateamos la respuesta con el estado actual
            return self._json_response(
                success=True,
                document: {
                    'id': document.id,
                    'name': document.name,
                    'status': document.status,
                    'document_type': document.document_type_code,
                    'confidence': document.confidence_score,
                    'processed_date': document.processed_date,
                    'result': result_data,
                },
                status=200
            )
            
        except Exception as e:
            _logger.error(f"Error al obtener estado de documento: {str(e)}")
            return self._json_response(
                success=False,
                message=f"Error interno: {str(e)}",
                status=500
            )
    
    def _json_response(self, success=True, message="", status=200, **kwargs):
        """Construye una respuesta JSON estándar"""
        data = {
            'success': success,
            'message': message,
            **kwargs
        }
        return {
            'jsonrpc': '2.0',
            'id': None,
            'result': data
        }
