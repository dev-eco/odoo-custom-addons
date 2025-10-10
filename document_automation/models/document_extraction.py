# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import tempfile
from PIL import Image
import google.generativeai as genai
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class DocumentExtraction(models.AbstractModel):
    """Modelo abstracto para funcionalidades de extracción de datos"""
    _name = 'document.extraction'
    _description = 'Funcionalidades de extracción de datos para documentos'

    @api.model
    def _get_gemini_api_key(self):
        """Obtiene la API key de Gemini desde la configuración"""
        api_key = self.env['ir.config_parameter'].sudo().get_param('document_automation.gemini_api_key')
        if not api_key:
            raise UserError(_('Gemini API Key no configurada. Configúrela en Ajustes > Automatización Documental.'))
        return api_key

    @api.model
    def _setup_gemini(self):
        """Configura la API de Gemini"""
        api_key = self._get_gemini_api_key()
        genai.configure(api_key=api_key)
        # Para texto
        return genai.GenerativeModel('gemini-pro')

    @api.model
    def _setup_gemini_vision(self):
        """Configura la API de Gemini para visión"""
        api_key = self._get_gemini_api_key()
        genai.configure(api_key=api_key)
        # Para imágenes y texto
        return genai.GenerativeModel('gemini-pro-vision')

    @api.model
    def extract_data_with_gemini_from_text(self, text, document_type=None):
        """
        Extrae datos estructurados de texto usando Gemini AI
        
        Args:
            text (str): Texto del documento
            document_type (str): Tipo de documento (factura, albarán, etc.)
            
        Returns:
            dict: Datos estructurados extraídos
        """
        if not text:
            return {}
        
        try:
            # Configura Gemini
            model = self._setup_gemini()
            
            # Define el prompt específico según el tipo de documento
            doc_type = document_type or "documento"
            
            # Plantilla base de extracción
            extraction_template = """
            - Número de documento/referencia
            - Fecha de emisión
            - Nombre del proveedor/cliente
            - NIF/CIF
            - Dirección
            - Importe total
            - Base imponible
            - IVA (porcentaje y cantidad)
            - Método de pago (si está presente)
            """
            
            # Personalizar según tipo de documento
            if 'factura' in doc_type.lower():
                extraction_template += """
                - Fecha de vencimiento
                - Número de pedido relacionado
                - Líneas de factura con:
                  - Descripción
                  - Cantidad
                  - Precio unitario
                  - Importe
                """
            elif 'albar' in doc_type.lower():
                extraction_template += """
                - Fecha de entrega
                - Número de pedido relacionado
                - Dirección de entrega
                - Líneas de producto con:
                  - Referencia
                  - Descripción
                  - Cantidad
                """
            elif 'pedido' in doc_type.lower():
                extraction_template += """
                - Fecha prevista de entrega
                - Condiciones de pago
                - Dirección de entrega
                - Líneas de producto con:
                  - Referencia
                  - Descripción
                  - Cantidad
                  - Precio unitario
                  - Importe
                """
                
            prompt = f"""
            Extrae la siguiente información de este {doc_type}:
            {extraction_template}

            Devuelve solo un objeto JSON válido con estos campos. Si no encuentras alguno, déjalo como null.
            Si un campo tiene formato específico (fechas, importes, etc.), asegúrate de estandarizarlo.
            
            Para fechas, usa formato YYYY-MM-DD.
            Para importes, usa solo números con dos decimales, sin símbolos de moneda.
            
            Documento:
            {text}
            """
            
            response = model.generate_content(prompt)
            
            # Extraer el JSON de la respuesta
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
                
            json_str = json_str.strip()
            extracted_data = json.loads(json_str)
            return extracted_data
        except Exception as e:
            _logger.error("Error en extracción con Gemini: %s", str(e))
            return {"error": str(e)}

    @api.model
    def extract_data_with_gemini_from_image(self, document_file, file_type, document_type=None):
        """
        Extrae datos estructurados directamente de la imagen usando Gemini AI
        
        Args:
            document_file (str): Archivo del documento en base64
            file_type (str): Tipo de archivo (pdf, jpg, etc.)
            document_type (str): Tipo de documento (factura, albarán, etc.)
            
        Returns:
            dict: Datos estructurados extraídos
        """
        if not document_file:
            return {}
        
        try:
            # Guardar imagen temporalmente
            image_data = base64.b64decode(document_file)
            file_ext = '.pdf' if 'pdf' in file_type.lower() else '.png'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
            temp_file_path = temp_file.name
            temp_file.write(image_data)
            temp_file.close()
            
            # Si es PDF, convertir primera página a imagen
            if 'pdf' in file_type.lower():
                from pdf2image import convert_from_path
                image = convert_from_path(temp_file_path, first_page=1, last_page=1)[0]
                temp_image_path = temp_file_path.replace('.pdf', '.png')
                image.save(temp_image_path)
                temp_file_path = temp_image_path
            
            # Cargar imagen
            image = Image.open(temp_file_path)
            
            # Configurar y llamar a Gemini
            model = self._setup_gemini_vision()
            
            # Define el prompt específico según el tipo de documento
            doc_type = document_type or "documento"
            
            # Plantilla base de extracción
            extraction_template = """
            - Número de documento/referencia
            - Fecha de emisión
            - Nombre del proveedor/cliente
            - NIF/CIF
            - Dirección
            - Importe total
            - Base imponible
            - IVA (porcentaje y cantidad)
            - Método de pago (si está presente)
            """
            
            # Personalizar según tipo de documento
            if 'factura' in doc_type.lower():
                extraction_template += """
                - Fecha de vencimiento
                - Número de pedido relacionado
                - Líneas de factura con:
                  - Descripción
                  - Cantidad
                  - Precio unitario
                  - Importe
                """
            elif 'albar' in doc_type.lower():
                extraction_template += """
                - Fecha de entrega
                - Número de pedido relacionado
                - Dirección de entrega
                - Líneas de producto con:
                  - Referencia
                  - Descripción
                  - Cantidad
                """
            elif 'pedido' in doc_type.lower():
                extraction_template += """
                - Fecha prevista de entrega
                - Condiciones de pago
                - Dirección de entrega
                - Líneas de producto con:
                  - Referencia
                  - Descripción
                  - Cantidad
                  - Precio unitario
                  - Importe
                """
                
            prompt = f"""
            Analiza esta imagen de {doc_type} y extrae la siguiente información:
            {extraction_template}

            Devuelve solo un objeto JSON válido con estos campos. Si no encuentras alguno, déjalo como null.
            Si un campo tiene formato específico (fechas, importes, etc.), asegúrate de estandarizarlo.
            
            Para fechas, usa formato YYYY-MM-DD.
            Para importes, usa solo números con dos decimales, sin símbolos de moneda.
            """
            
            response = model.generate_content([prompt, image])
            
            # Eliminar archivos temporales
            os.unlink(temp_file_path)
            if 'pdf' in file_type.lower() and os.path.exists(temp_file_path.replace('.pdf', '.png')):
                os.unlink(temp_file_path.replace('.pdf', '.png'))
            
            # Extraer el JSON de la respuesta
            json_str = response.text.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
                
            json_str = json_str.strip()
            extracted_data = json.loads(json_str)
            return extracted_data
        except Exception as e:
            _logger.error("Error en extracción con Gemini desde imagen: %s", str(e))
            return {"error": str(e)}

    @api.model
    def validate_extracted_data(self, data, document_type=None):
        """
        Valida los datos extraídos y asigna un nivel de confianza
        
        Args:
            data (dict): Datos extraídos
            document_type (str): Tipo de documento
            
        Returns:
            tuple: (datos validados, score de confianza)
        """
        if not data or "error" in data:
            return data, 0.0
            
        score = 0.0
        total_fields = 0
        filled_fields = 0
        
        # Campos críticos según tipo de documento
        critical_fields = ['numero_documento', 'referencia', 'fecha', 'importe_total']
        
        if 'factura' in (document_type or '').lower():
            critical_fields.extend(['base_imponible', 'iva'])
        elif 'albar' in (document_type or '').lower():
            critical_fields.extend(['fecha_entrega'])
        
        # Contar campos completados
        for key, value in data.items():
            total_fields += 1
            if value is not None and value != "":
                filled_fields += 1
                # Campos críticos tienen mayor peso
                if any(critical in key.lower() for critical in critical_fields):
                    score += 2
                else:
                    score += 1
        
        if total_fields > 0:
            # Normalizar puntuación a 0-1
            score = min(score / (total_fields + len(critical_fields)), 1.0)
        else:
            score = 0.0
            
        return data, score
