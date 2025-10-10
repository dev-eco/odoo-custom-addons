# controllers/main.py
from odoo import http
from odoo.http import request, Response
import json
import base64
import logging

_logger = logging.getLogger(__name__)

class DocumentAutomationController(http.Controller):
    @http.route('/api/document_automation/upload', type='json', auth='user', methods=['POST'], csrf=False)
    def upload_document(self, **post):
        """API para subir documentos"""
        try:
            # Obtener datos del request
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validar datos mínimos
            if not data.get('document') or not data.get('name'):
                return {'success': False, 'error': 'Faltan datos requeridos (documento y nombre)'}
            
            # Decodificar documento
            try:
                document_data = base64.b64decode(data.get('document'))
            except Exception:
                return {'success': False, 'error': 'El documento debe estar en formato base64'}
                
            # Crear documento
            document_vals = {
                'name': '/', # Se asignará secuencia
                'document_file': data.get('document'),
                'filename': data.get('filename', data.get('name')),
                'source': 'api',
                'user_id': request.env.user.id,
            }
            
            # Asignar tipo de documento si se proporciona
            if data.get('document_type_code'):
                doc_type = request.env['document.type'].sudo().search(
                    [('code', '=', data.get('document_type_code'))], 
                    limit=1
                )
                if doc_type:
                    document_vals['document_type_id'] = doc_type.id
            
            # Crear documento
            document = request.env['document.automation'].sudo().create(document_vals)
            
            # Añadir notas si existen
            if data.get('notes'):
                document.message_post(body=data.get('notes'))
                
            # Iniciar procesamiento si se solicita
            if data.get('process', False):
                document.with_delay().process_document()
                
            return {
                'success': True, 
                'document_id': document.id,
                'document_name': document.name,
            }
            
        except Exception as e:
            _logger.exception("Error en la API de documentos: %s", str(e))
            return {'success': False, 'error': str(e)}
    
    @http.route('/api/document_automation/<int:document_id>', type='http', auth='user', methods=['GET'])
    def get_document_status(self, document_id, **kwargs):
        """API para consultar estado de un documento"""
        try:
            document = request.env['document.automation'].sudo().browse(document_id)
            if not document.exists():
                return Response(
                    json.dumps({'success': False, 'error': 'Documento no encontrado'}),
                    content_type='application/json',
                    status=404
                )
                
            result = {
                'success': True,
                'document': {
                    'id': document.id,
                    'name': document.name,
                    'state': document.state,
                    'document_type': document.document_type_id.name if document.document_type_id else False,
                    'confidence': document.confidence_score,
                    'status_message': document.status_message,
                    'created_at': document.create_date.isoformat() if document.create_date else False,
                    'processed_at': document.processed_date.isoformat() if document.processed_date else False,
                }
            }
            
            # Añadir datos extraídos si existen y si están autorizados
            if document.extracted_data and request.env.user.has_group('document_automation.group_document_automation_manager'):
                result['document']['extracted_data'] = json.loads(document.extracted_data)
                
            # Añadir información del documento resultante si existe
            if document.result_model and document.result_id:
                result['document']['result'] = {
                    'model': document.result_model,
                    'id': document.result_id,
                    'reference': document.result_reference,
                }
                
            return Response(
                json.dumps(result),
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.exception("Error en la API de consulta de documento: %s", str(e))
            return Response(
                json.dumps({'success': False, 'error': str(e)}),
                content_type='application/json',
                status=500
            )
