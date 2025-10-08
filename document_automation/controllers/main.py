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

    @http.route('/api/v1/document/scan', type='json', auth='public', methods=['POST'], csrf=False)
    def receive_scanned_document(self, **kwargs):
        """Endpoint para recibir documentos escaneados desde el cliente externo"""
        try:
            _logger.info("===== INICIO PETICIÓN DOCUMENTO =====")
            
            # Acceder directamente a los datos recibidos en kwargs
            _logger.info(f"Datos recibidos: {kwargs}")
            
            # Verificar autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            
            # Validación de API Key (omitida para brevedad)
            
            # IMPORTANTE: Obtener el PDF directamente de los argumentos recibidos
            pdf_file_b64 = kwargs.get('pdf_file_b64')
            if not pdf_file_b64:
                _logger.error("No se recibió archivo codificado en base64")
                return {"success": False, "message": "No se recibió ningún archivo"}
            
            # Decodificar archivo
            try:
                file_data = base64.b64decode(pdf_file_b64)
                filename = kwargs.get('filename', 'document.pdf')
                document_type = kwargs.get('document_type', 'generic')
                supplier_name = kwargs.get('supplier_name', '')
                notes = kwargs.get('notes', '')
                user = kwargs.get('user', 'system')
                scanner_name = kwargs.get('scanner_name', 'default_scanner')
                
                _logger.info(f"Archivo decodificado: {filename} ({len(file_data)} bytes)")
                
                # Resto del código igual...    
    
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
