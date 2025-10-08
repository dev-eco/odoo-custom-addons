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
            # Log ultra detallado para depuración
            _logger.info("===== INICIO PETICIÓN API =====")
            _logger.info(f"Headers: {dict(request.httprequest.headers)}")
            _logger.info(f"Params: {request.params}")
            _logger.info(f"Content-Type: {request.httprequest.headers.get('Content-Type')}")
            _logger.info(f"Files: {request.httprequest.files}")
            _logger.info(f"Method: {request.httprequest.method}")
            _logger.info(f"URL: {request.httprequest.url}")
            
            # Autenticación simplificada - saltamos esto por ahora
            api_config = request.env['ir.config_parameter'].sudo()
            api_debug_mode = api_config.get_param('document_automation.api_debug_mode', 'true').lower() == 'true'
            
            # Verificación extra para el archivo
            if not request.httprequest.files:
                _logger.error("No se recibieron archivos en la petición multipart/form-data")
                
                # Intenta obtener datos del cuerpo raw
                content_type = request.httprequest.headers.get('Content-Type', '')
                
                if content_type.startswith('multipart/form-data'):
                    _logger.info("Content-Type es multipart/form-data pero no se recibieron archivos")
                    _logger.info(f"Content-Length: {request.httprequest.headers.get('Content-Length')}")
                    
                    # Verifica si hay datos en el cuerpo
                    if request.httprequest.data:
                        _logger.info(f"Hay datos en el cuerpo: {len(request.httprequest.data)} bytes")
                    else:
                        _logger.info("No hay datos en el cuerpo")
                    
                    return self._http_response({
                        "success": False, 
                        "message": "No se recibió ningún archivo. El Content-Type es multipart/form-data pero no se recibieron archivos."
                    }, 400)
                else:
                    _logger.info(f"Content-Type incorrecto: {content_type}")
                    return self._http_response({
                        "success": False, 
                        "message": f"Content-Type incorrecto: {content_type}. Debe ser multipart/form-data."
                    }, 400)
            
            # Obtén el archivo enviado
            file = None
            for field_name, file_obj in request.httprequest.files.items():
                _logger.info(f"Archivo recibido: {field_name} - {file_obj.filename}")
                file = file_obj
                break
            
            if not file:
                _logger.error("No se encontró archivo en la petición")
                return self._http_response({"success": False, "message": "No se recibió ningún archivo identificable"}, 400)
                
            # Leemos los datos y el nombre del archivo
            pdf_data = file.read()
            filename = file.filename
            
            if not pdf_data:
                _logger.error(f"El archivo {filename} está vacío")
                return self._http_response({"success": False, "message": f"El archivo {filename} está vacío"}, 400)
                
            _logger.info(f"Archivo leído correctamente: {filename} ({len(pdf_data)} bytes)")
            
            # Resto del código como antes...
            # [...]
            
            return self._http_response({
                "success": True,
                "message": "Documento recibido correctamente",
                "document_id": 123  # ID de prueba
            }, 200)
                
        except Exception as e:
            _logger.error(f"===== FIN PETICIÓN API (ERROR) =====")
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
