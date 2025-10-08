# -*- coding: utf-8 -*-
import base64
import json
import logging
import hmac
import hashlib
import traceback
from datetime import datetime

from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class DocumentAutomationController(http.Controller):
    
    @http.route('/api/v1/invoice/health', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def health_check(self, **kwargs):
        """Endpoint para verificar que la API está funcionando"""
        try:
            response = {
                "status": "healthy",
                "service": "document_automation_api",
                "version": "1.0.0"
            }
            return self._http_response(response, 200)
        except Exception as e:
            _logger.error(f"Error en la API: {str(e)}")
            return self._http_response({"status": "error", "message": str(e)}, 500)
    
    @http.route('/api/v1/document/scan', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def receive_scanned_document(self, **kwargs):
        """Endpoint para recibir documentos escaneados desde el cliente externo"""
        try:
            _logger.info("===== INICIO PETICIÓN DOCUMENTO =====")
            _logger.info(f"Datos recibidos: {request.jsonrequest}")
            
            # Obtener datos del JSON
            json_data = request.jsonrequest
            
            # Verificar autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            timestamp = headers.get('X-Timestamp')
            signature = headers.get('X-Signature')
            
            _logger.info(f"Headers de autenticación: API Key={api_key}, Timestamp={timestamp}")
            
            # Validamos la API Key (en desarrollo siempre permitimos)
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key', '')
            api_secret = api_config.get_param('document_automation.api_secret', '')
            api_debug_mode = api_config.get_param('document_automation.api_debug_mode', 'true').lower() == 'true'
            
            if not api_debug_mode and valid_api_key and api_key != valid_api_key:
                _logger.error(f"API Key inválida: {api_key} != {valid_api_key}")
                return {"success": False, "message": "Autenticación fallida"}
            
            # Verificar que tenemos los datos necesarios
            if not json_data.get('pdf_file_b64'):
                _logger.error("No se recibió archivo codificado en base64")
                return {"success": False, "message": "No se recibió ningún archivo"}
            
            # Decodificar archivo
            try:
                file_data = base64.b64decode(json_data.get('pdf_file_b64'))
                filename = json_data.get('filename', 'document.pdf')
                document_type = json_data.get('document_type', 'generic')
                supplier_name = json_data.get('supplier_name', '')
                notes = json_data.get('notes', '')
                user = json_data.get('user', 'system')
                scanner_name = json_data.get('scanner_name', 'default_scanner')
                
                _logger.info(f"Archivo decodificado: {filename} ({len(file_data)} bytes)")
                
            except Exception as e:
                _logger.error(f"Error decodificando archivo: {str(e)}")
                return {"success": False, "message": f"Error decodificando archivo: {str(e)}"}
            
            # Buscamos el tipo de documento por código
            document_type_obj = request.env['document.type'].sudo().search([('code', '=', document_type)], limit=1)
            if not document_type_obj:
                document_type_obj = request.env['document.type'].sudo().search([], limit=1)
            
            # Creamos el registro de documento escaneado
            document_vals = {
                'name': filename,
                'document_type_id': document_type_obj.id if document_type_obj else False,
                'document_type_code': document_type,
                'source': 'scanner',
                'status': 'pending',
                'notes': notes,
            }
            
            document = request.env['document.scan'].sudo().create(document_vals)
            _logger.info(f"Documento creado: ID={document.id}")
            
            # Creamos el adjunto
            attachment = request.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(file_data),
                'res_model': 'document.scan',
                'res_id': document.id,
                'mimetype': 'application/pdf' if filename.lower().endswith('.pdf') else 'application/octet-stream',
            })
            
            # Asignamos el adjunto al documento
            document.attachment_id = attachment.id
            
            # Procesamiento automático si está configurado
            auto_process = api_config.get_param('document_automation.auto_process', 'false').lower() == 'true'
            if auto_process:
                try:
                    document.action_process()
                    _logger.info(f"Procesamiento automático iniciado para documento ID={document.id}")
                except Exception as e:
                    _logger.error(f"Error en procesamiento automático: {str(e)}")
            
            # Respuesta exitosa
            _logger.info(f"Documento procesado correctamente: ID={document.id}")
            return {
                "success": True,
                "message": _("Documento recibido correctamente"),
                "document_id": document.id
            }
            
        except Exception as e:
            _logger.error(f"Error al procesar documento: {str(e)}")
            _logger.error(traceback.format_exc())
            return {"success": False, "message": f"Error interno: {str(e)}"}
    
    @http.route('/api/v1/document/types', type='json', auth='public', methods=['POST'], csrf=False)
    def get_document_types(self, **post):
        """Endpoint para obtener los tipos de documentos disponibles"""
        try:
            # Verificamos la autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            
            # Validamos la API Key (en desarrollo siempre permitimos)
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key', '')
            api_debug_mode = api_config.get_param('document_automation.api_debug_mode', 'true').lower() == 'true'
            
            if not api_debug_mode and valid_api_key and api_key != valid_api_key:
                _logger.error(f"API Key inválida: {api_key}")
                return {"success": False, "message": "Autenticación fallida"}
            
            # Obtenemos los tipos de documentos activos
            doc_types = request.env['document.type'].sudo().search([('active', '=', True)])
            
            # Formateamos la respuesta
            types_data = []
            for doc_type in doc_types:
                types_data.append({
                    'id': doc_type.id,
                    'name': doc_type.name,
                    'code': doc_type.code,
                    'description': doc_type.description if hasattr(doc_type, 'description') else '',
                    'sequence': doc_type.sequence,
                })
            
            return {
                "success": True,
                "document_types": types_data
            }
            
        except Exception as e:
            _logger.error(f"Error al obtener tipos de documento: {str(e)}")
            return {"success": False, "message": f"Error interno: {str(e)}"}
    
    @http.route('/api/v1/document/status/<int:document_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_document_status(self, document_id, **post):
        """Endpoint para verificar el estado de un documento procesado"""
        try:
            # Verificamos la autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            
            # Validamos la API Key
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key', '')
            api_debug_mode = api_config.get_param('document_automation.api_debug_mode', 'true').lower() == 'true'
            
            if not api_debug_mode and valid_api_key and api_key != valid_api_key:
                _logger.error(f"API Key inválida: {api_key}")
                return self._http_response({"success": False, "message": "Autenticación fallida"}, 401)
            
            # Obtenemos el documento
            document = request.env['document.scan'].sudo().browse(document_id)
            
            if not document.exists():
                return self._http_response({"success": False, "message": "Documento no encontrado"}, 404)
            
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
            return self._http_response({
                "success": True,
                "document": {
                    'id': document.id,
                    'name': document.name,
                    'status': document.status,
                    'document_type': document.document_type_code,
                    'confidence': document.confidence_score,
                    'processed_date': document.processed_date.isoformat() if document.processed_date else None,
                    'result': result_data,
                }
            }, 200)
            
        except Exception as e:
            _logger.error(f"Error al obtener estado de documento: {str(e)}")
            return self._http_response({"success": False, "message": f"Error interno: {str(e)}"}, 500)
    
    def _http_response(self, data, status_code=200):
        """Helper para construir respuestas HTTP con formato JSON"""
        headers = [
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, X-Api-Key, X-Timestamp, X-Signature'),
        ]
        return Response(
            json.dumps(data),
            status=status_code,
            headers=headers,
            content_type='application/json'
        )
