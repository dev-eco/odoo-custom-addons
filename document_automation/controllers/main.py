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
from odoo.exceptions import AccessDenied, ValidationError

_logger = logging.getLogger(__name__)

class DocumentAutomationController(http.Controller):
    
    @http.route('/api/v1/invoice/health', type='http', auth='public', methods=['GET'], csrf=False)
    def health_check(self, **kwargs):
        """Endpoint para verificar que la API está funcionando"""
        try:
            response = {
                "status": "healthy",
                "service": "invoice_ocr_api",
                "version": "1.0.0"
            }
            return self._http_response(response, 200)
        except Exception as e:
            _logger.error(f"Error en la API: {str(e)}")
            _logger.error(traceback.format_exc())
            return self._http_response({"status": "error", "message": str(e)}, 500)
    
    @http.route('/api/v1/document/scan', type='http', auth='public', methods=['POST'], csrf=False)
    def receive_scanned_document(self, **kwargs):
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
                return self._http_response({"success": False, "message": "API no configurada"}, 500)
                
            # Verificamos la API key
            if api_key != valid_api_key:
                _logger.error(f"API Key inválida: {api_key}")
                return self._http_response({"success": False, "message": "Autenticación fallida"}, 401)
            
            # Verificamos la firma HMAC para mayor seguridad
            if timestamp and signature:
                expected_signature = hmac.new(
                    api_secret.encode('utf-8'),
                    f"{api_key}{timestamp}".encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                if signature != expected_signature:
                    _logger.error(f"Firma inválida: {signature}")
                    return self._http_response({"success": False, "message": "Autenticación fallida (firma)"}, 401)
            
            # Obtenemos el archivo del form-data
            file = request.httprequest.files.get('file')
            if not file:
                _logger.error("No se recibió ningún archivo")
                return self._http_response({"success": False, "message": "No se recibió ningún archivo"}, 400)
            
            # Leemos los datos y el nombre del archivo
            pdf_data = file.read()
            filename = file.filename
            
            # Obtenemos parámetros adicionales
            document_type_code = request.params.get('document_type', 'invoice')
            source = request.params.get('source', 'scanner')
            
            # Buscamos el tipo de documento por código
            document_type = request.env['document.type'].sudo().search([('code', '=', document_type_code)], limit=1)
            if not document_type:
                document_type = request.env['document.type'].sudo().search([], limit=1)
            
            # Creamos el registro de documento escaneado
            document_vals = {
                'name': filename,
                'document_type_id': document_type.id if document_type else False,
                'document_type_code': document_type_code,
                'source': source,
                'status': 'pending',
            }
            
            document = request.env['document.scan'].sudo().create(document_vals)
            
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
            return self._http_response({
                "success": True,
                "message": "Documento recibido correctamente",
                "document_id": document.id
            }, 200)
            
        except Exception as e:
            _logger.error(f"Error al procesar documento escaneado: {str(e)}")
            _logger.error(traceback.format_exc())
            return self._http_response({
                "success": False,
                "message": f"Error interno: {str(e)}"
            }, 500)
    
    @http.route('/api/v1/document/types', type='http', auth='public', methods=['GET'], csrf=False)
    def get_document_types(self, **kwargs):
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
                return self._http_response({"success": False, "message": "Autenticación fallida"}, 401)
            
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
            
            return self._http_response({
                "success": True,
                "document_types": types_data
            }, 200)
            
        except Exception as e:
            _logger.error(f"Error al obtener tipos de documento: {str(e)}")
            return self._http_response({
                "success": False,
                "message": f"Error interno: {str(e)}"
            }, 500)
    
    @http.route('/api/v1/document/status/<int:document_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_document_status(self, document_id, **kwargs):
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
        return Response(
            json.dumps(data),
            status=status_code,
            content_type='application/json'
        )
