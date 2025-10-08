# -*- coding: utf-8 -*-
import base64
import json
import logging
import hmac
import hashlib
from datetime import datetime
import traceback

from odoo import http, _
from odoo.http import request, Response, route

_logger = logging.getLogger(__name__)

class DocumentAutomationController(http.Controller):
    
    # Ruta de health check sin autenticación
    @http.route(['/api/v1/invoice/health', '/api/v1/document/health'], type='http', auth='none', methods=['GET'], csrf=False, cors='*')
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
            _logger.error(traceback.format_exc())
            return self._http_response({"status": "error", "message": str(e)}, 500)
    
    # Ruta principal para recibir documentos
    @http.route('/api/v1/document/scan', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    def receive_scanned_document(self, **kwargs):
        """Endpoint para recibir documentos escaneados desde el cliente externo"""
        try:
            # Log para depuración
            _logger.info("API llamada: /api/v1/document/scan")
            _logger.info(f"Headers: {request.httprequest.headers}")
            _logger.info(f"Params: {request.params}")
            
            # Verificamos la autenticación API Key
            headers = request.httprequest.headers
            api_key = headers.get('X-Api-Key')
            timestamp = headers.get('X-Timestamp')
            signature = headers.get('X-Signature')
            
            # Validamos la API Key
            api_config = request.env['ir.config_parameter'].sudo()
            valid_api_key = api_config.get_param('document_automation.api_key')
            api_secret = api_config.get_param('document_automation.api_secret')
            
            # Si la API Key no está configurada, permitimos en modo debug
            if not valid_api_key or not api_secret:
                _logger.warning("API Key no configurada en el sistema, permitiendo en modo debug")
                valid_api_key = "test_key"
                api_secret = "test_secret"
            
            # Verificamos la API key (excepto en modo debug)
            if api_config.get_param('document_automation.api_debug_mode', 'false').lower() != 'true':
                if not api_key or api_key != valid_api_key:
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
    # Agregar este método al final de la clase DocumentAutomationController

    @http.route(['/api', '/api/v1', '/api/v1/document', '/api/v1/invoice'], type='http', auth='public', website=True)
    def api_root_redirect(self, **kwargs):
        """Proporciona una respuesta para las rutas base de la API en website"""
        return request.redirect('/api/documentation')

    @http.route('/api/documentation', type='http', auth='public', website=True)
    def api_documentation(self, **kwargs):
        """Página de documentación de la API"""
        return http.request.render('document_automation.api_documentation', {
            'api_base_url': request.httprequest.url_root.rstrip('/') + '/api/v1',
        })
