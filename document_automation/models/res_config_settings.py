import base64
import uuid
import logging
import tempfile
import os
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Configuración general
    document_automation_enable_email = fields.Boolean(
        string="Habilitar recepción por email",
        help="Activa la recepción automática de documentos por email",
    )
    
    document_automation_email_alias = fields.Char(
        string="Alias de correo",
        help="Dirección de correo donde se pueden enviar documentos (ej. documentos@empresa.com)",
    )
    
    document_automation_enable_scanner = fields.Boolean(
        string="Habilitar escáner local",
        help="Activa el procesamiento de documentos mediante escáner local",
    )
    
    # Configuración de API
    document_automation_api_key = fields.Char(
        string="API Key",
        help="Clave API para el cliente de escaneo",
    )
    
    document_automation_api_secret = fields.Char(
        string="API Secret",
        help="Secreto API para firma HMAC",
    )
    
    document_automation_show_api_key = fields.Boolean(
        string="Mostrar API Key",
        help="Marca para mostrar la API Key en pantalla",
    )
    
    # Configuración de OCR Tesseract
    document_automation_tesseract_path = fields.Char(
        string="Ruta a Tesseract",
        help="Ruta al ejecutable de Tesseract OCR (por defecto 'tesseract')",
    )
    
    document_automation_ocr_language = fields.Char(
        string="Idioma OCR",
        help="Código de idioma para Tesseract (por defecto 'spa' para español)",
    )
    
    # Configuración de procesamiento
    document_automation_auto_process = fields.Boolean(
        string="Procesamiento automático",
        help="Procesar automáticamente documentos al recibirlos"
    )
    
    document_automation_auto_validate = fields.Boolean(
        string="Validación automática",
        help="Validar automáticamente documentos con alta confianza de OCR"
    )
    
    document_automation_validation_threshold = fields.Float(
        string="Umbral de validación automática",
        help="Porcentaje mínimo de confianza para validar automáticamente (0-100)",
        default=90.0,
    )
    
    document_automation_retry_attempts = fields.Integer(
        string="Intentos de procesamiento",
        help="Número máximo de reintentos para documentos fallidos",
        default=3,
    )
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        # Obtenemos valores desde parámetros del sistema
        params = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'document_automation_enable_email': params.get_param('document_automation.enable_email', default=False),
            'document_automation_email_alias': params.get_param('document_automation.email_alias', default=''),
            'document_automation_enable_scanner': params.get_param('document_automation.enable_scanner', default=False),
            'document_automation_api_key': params.get_param('document_automation.api_key', default=''),
            'document_automation_api_secret': params.get_param('document_automation.api_secret', default=''),
            'document_automation_auto_process': params.get_param('document_automation.auto_process', default=False),
            'document_automation_auto_validate': params.get_param('document_automation.auto_validate', default=False),
            'document_automation_validation_threshold': float(params.get_param('document_automation.validation_threshold', default=90.0)),
            'document_automation_retry_attempts': int(params.get_param('document_automation.retry_attempts', default=3)),
            'document_automation_tesseract_path': params.get_param('document_automation.tesseract_path', default='tesseract'),
            'document_automation_ocr_language': params.get_param('document_automation.ocr_language', default='spa'),
        })
        
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        
        # Guardamos los valores en parámetros del sistema
        params = self.env['ir.config_parameter'].sudo()
        
        params.set_param('document_automation.enable_email', self.document_automation_enable_email)
        params.set_param('document_automation.email_alias', self.document_automation_email_alias or '')
        params.set_param('document_automation.enable_scanner', self.document_automation_enable_scanner)
        params.set_param('document_automation.auto_process', self.document_automation_auto_process)
        params.set_param('document_automation.auto_validate', self.document_automation_auto_validate)
        params.set_param('document_automation.validation_threshold', str(self.document_automation_validation_threshold))
        params.set_param('document_automation.retry_attempts', str(self.document_automation_retry_attempts))
        params.set_param('document_automation.tesseract_path', self.document_automation_tesseract_path or 'tesseract')
        params.set_param('document_automation.ocr_language', self.document_automation_ocr_language or 'spa')
        
        # Solo actualizamos API key y secret si están definidos
        if self.document_automation_api_key:
            params.set_param('document_automation.api_key', self.document_automation_api_key)
        
        if self.document_automation_api_secret:
            params.set_param('document_automation.api_secret', self.document_automation_api_secret)
        
        # Configuración de alias de correo
        if self.document_automation_enable_email and self.document_automation_email_alias:
            self._configure_email_alias()
    
    def _configure_email_alias(self):
        """Configura el alias de correo para recepción de documentos"""
        try:
            # Verificamos si existe el alias para documentos
            alias_name = self.document_automation_email_alias.split('@')[0] if '@' in self.document_automation_email_alias else self.document_automation_email_alias
            
            alias = self.env['mail.alias'].search([
                ('alias_name', '=', alias_name)
            ], limit=1)
            
            if not alias:
                # Creamos un nuevo alias
                alias = self.env['mail.alias'].create({
                    'alias_name': alias_name,
                    'alias_model_id': self.env['ir.model']._get('document.scan').id,
                    'alias_defaults': "{'source': 'email'}",
                })
                _logger.info(f"Alias de email creado: {alias_name}")
            else:
                # Actualizamos el alias existente
                alias.write({
                    'alias_model_id': self.env['ir.model']._get('document.scan').id,
                    'alias_defaults': "{'source': 'email'}",
                })
                _logger.info(f"Alias de email actualizado: {alias_name}")
                
        except Exception as e:
            _logger.error(f"Error al configurar alias de email: {str(e)}")
    
    def action_generate_api_credentials(self):
        """Genera nuevas credenciales de API"""
        # Generamos una nueva API Key y Secret
        api_key = f"doca_{uuid.uuid4().hex[:16]}"
        api_secret = uuid.uuid4().hex
        
        # Actualizamos los campos
        self.write({
            'document_automation_api_key': api_key,
            'document_automation_api_secret': api_secret,
            'document_automation_show_api_key': True,
        })
        
        # Notificamos al usuario
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Credenciales generadas'),
                'message': _('Se han generado nuevas credenciales API. Guárdalas en un lugar seguro.'),
                'sticky': True,
                'type': 'success',
            }
        }
    
    def action_test_tesseract(self):
        """Prueba la configuración de Tesseract OCR"""
        try:
            # Importar dependencias
            try:
                import pytesseract
                from PIL import Image
                import io
            except ImportError:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error de dependencias'),
                        'message': _('Las bibliotecas Python necesarias (pytesseract, Pillow) no están instaladas.'),
                        'sticky': True,
                        'type': 'danger',
                    }
                }
            
            # Configurar ruta de tesseract
            tesseract_path = self.document_automation_tesseract_path or 'tesseract'
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # Verificar versión de tesseract
            try:
                version = pytesseract.get_tesseract_version()
                _logger.info(f"Tesseract version: {version}")
            except Exception as e:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error de Tesseract'),
                        'message': _('No se pudo encontrar Tesseract. Error: %s') % str(e),
                        'sticky': True,
                        'type': 'danger',
                    }
                }
            
            # Crear una imagen de prueba simple
            text = "Prueba de OCR con Tesseract"
            image = Image.new('RGB', (400, 100), color=(255, 255, 255))
            
            # Guardar y procesar la imagen
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                image.save(tmp_file, format='PNG')
                tmp_path = tmp_file.name
            
            # Procesar con OCR
            try:
                result = pytesseract.image_to_string(
                    tmp_path,
                    lang=self.document_automation_ocr_language or 'spa'
                )
                
                # Limpiar el archivo temporal
                os.unlink(tmp_path)
                
                # Si llegamos aquí, todo está bien
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Tesseract configurado correctamente'),
                        'message': _('Versión de Tesseract: %s') % version,
                        'sticky': False,
                        'type': 'success',
                    }
                }
                
            except Exception as e:
                # Limpiar el archivo temporal
                os.unlink(tmp_path)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error en prueba de OCR'),
                        'message': _('Tesseract está instalado pero hubo un error procesando la imagen: %s') % str(e),
                        'sticky': True,
                        'type': 'warning',
                    }
                }
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error general: %s') % str(e),
                    'sticky': True,
                    'type': 'danger',
                }
            }
