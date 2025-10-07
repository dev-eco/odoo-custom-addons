import base64
import io
import json
import logging
import os
import tempfile
from datetime import datetime

from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    _logger.warning("Tesseract or required Python libraries not available. OCR features will be disabled.")
    TESSERACT_AVAILABLE = False

class DocumentOCR:
    """Clase para manejar el procesamiento OCR con Tesseract"""
    
    def __init__(self, env):
        """Inicializa la clase OCR con el entorno Odoo"""
        self.env = env
        self.config = {
            'lang': env['ir.config_parameter'].sudo().get_param('document_automation.ocr_language', 'spa'),
            'tesseract_cmd': env['ir.config_parameter'].sudo().get_param('document_automation.tesseract_path', 'tesseract')
        }
        
        # Configurar Tesseract si está disponible
        if TESSERACT_AVAILABLE:
            try:
                # Comprobar si podemos configurar la ruta de tesseract
                if self.config['tesseract_cmd']:
                    pytesseract.pytesseract.tesseract_cmd = self.config['tesseract_cmd']
            except Exception as e:
                _logger.error(f"Error configurando Tesseract: {str(e)}")
    
    def is_available(self):
        """Comprueba si el OCR está disponible"""
        if not TESSERACT_AVAILABLE:
            return False
            
        try:
            # Intentamos verificar la versión de tesseract para asegurarnos que funciona
            version = pytesseract.get_tesseract_version()
            _logger.info(f"Tesseract disponible, versión: {version}")
            return True
        except Exception as e:
            _logger.error(f"Tesseract no disponible: {str(e)}")
            return False
    
    def process_pdf(self, pdf_data):
        """Procesa un PDF con OCR y extrae texto e información estructurada
        
        Args:
            pdf_data (bytes): Datos del PDF en formato bytes
            
        Returns:
            dict: Diccionario con el texto extraído y datos estructurados
        """
        if not self.is_available():
            raise UserError(_("OCR no disponible. Verifique que Tesseract esté instalado correctamente."))
        
        try:
            # Convertir PDF a imágenes
            with tempfile.TemporaryDirectory() as temp_dir:
                images = convert_from_bytes(
                    pdf_data,
                    dpi=300,
                    output_folder=temp_dir,
                    fmt='jpeg',
                    output_file='page'
                )
                
                # Procesar cada página con OCR
                full_text = ""
                confidence_sum = 0
                
                for i, image in enumerate(images):
                    # Ejecutamos OCR en la imagen
                    page_data = pytesseract.image_to_data(
                        image, 
                        lang=self.config['lang'],
                        output_type=pytesseract.Output.DICT,
                        config='--psm 1'  # Modo de segmentación automática de página
                    )
                    
                    # Extraemos texto y confianza
                    page_text = " ".join([word for word in page_data['text'] if word.strip()])
                    confidences = [int(conf) for conf in page_data['conf'] if conf != '-1']
                    
                    if confidences:
                        page_confidence = sum(confidences) / len(confidences)
                    else:
                        page_confidence = 0
                    
                    confidence_sum += page_confidence
                    full_text += f"--- Página {i+1} ---\n{page_text}\n\n"
            
            # Calcular confianza promedio
            avg_confidence = confidence_sum / len(images) if images else 0
            
            # Extraer datos estructurados mediante análisis del texto
            structured_data = self.extract_structured_data(full_text)
            
            return {
                'text': full_text,
                'confidence': avg_confidence,
                'structured_data': structured_data,
                'pages': len(images)
            }
            
        except Exception as e:
            _logger.error(f"Error en procesamiento OCR: {str(e)}")
            raise UserError(_("Error procesando documento con OCR: %s") % str(e))
    
    def extract_structured_data(self, text):
        """Analiza el texto para extraer datos estructurados
        
        Args:
            text (str): Texto extraído del documento
            
        Returns:
            dict: Datos estructurados extraídos
        """
        # Inicializamos diccionario de resultados
        data = {
            'document_type': self._detect_document_type(text),
            'invoice_number': self._extract_invoice_number(text),
            'invoice_date': self._extract_date(text),
            'partner_name': self._extract_partner_name(text),
            'partner_vat': self._extract_vat(text),
            'total_amount': self._extract_total_amount(text),
            'currency_code': self._extract_currency(text),
            'tax_amount': self._extract_tax_amount(text),
        }
        
        # Establecer confianza basada en cuántos campos se pudieron extraer
        fields_found = sum(1 for v in data.values() if v)
        data['confidence'] = (fields_found / len(data)) * 100
        
        return data
    
    def _detect_document_type(self, text):
        """Detecta el tipo de documento basado en el contenido"""
        text = text.lower()
        
        # Palabras clave para diferentes tipos de documento
        keywords = {
            'invoice': ['factura', 'invoice', 'importe', 'total', 'base imponible', 'iva'],
            'credit_note': ['abono', 'credit', 'nota de crédito', 'devolución'],
            'delivery_note': ['albarán', 'entrega', 'delivery note', 'bultos', 'cantidad'],
            'purchase_order': ['pedido', 'orden de compra', 'purchase order'],
            'ticket': ['ticket', 'recibo', 'caja', 'tienda'],
        }
        
        # Contar coincidencias para cada tipo
        scores = {}
        for doc_type, words in keywords.items():
            scores[doc_type] = sum(1 for word in words if word in text)
        
        # Determinar el tipo con mayor puntuación
        if scores:
            max_type = max(scores.items(), key=lambda x: x[1])
            if max_type[1] > 0:
                return max_type[0]
        
        return 'generic'
    
    def _extract_invoice_number(self, text):
        """Extrae el número de factura del texto"""
        import re
        
        # Patrones comunes de números de factura
        patterns = [
            r'(?:factura|invoice|fra\.?|fac\.?|nº|numero|number)[\s:]*([A-Za-z0-9\-\/]+)',
            r'(?:factura|invoice|fra\.?|fac\.?|nº|numero|number)(?:\s+(?:n[oº]\.?|num\.?|number))[\s:]*([A-Za-z0-9\-\/]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                if match.group(1).strip():
                    return match.group(1).strip()
        
        return None
    
    def _extract_date(self, text):
        """Extrae la fecha del texto"""
        import re
        from datetime import datetime
        
        # Patrones de fecha comunes
        patterns = [
            # DD/MM/YYYY
            r'(?:fecha|date)[\s:]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            # Formato texto español (01 de Enero de 2023)
            r'(?:fecha|date)[\s:].*?(\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{2,4})',
            # Buscar cualquier fecha en el texto
            r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                date_str = match.group(1).strip()
                try:
                    # Intentar convertir a fecha
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            day, month, year = parts
                            # Ajustar año si es necesario
                            if len(year) == 2:
                                year = f"20{year}" if int(year) < 50 else f"19{year}"
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif '-' in date_str:
                        parts = date_str.split('-')
                        if len(parts) == 3:
                            day, month, year = parts
                            if len(year) == 2:
                                year = f"20{year}" if int(year) < 50 else f"19{year}"
                            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                except:
                    continue
        
        return None
    
    def _extract_partner_name(self, text):
        """Extrae el nombre del proveedor del texto"""
        import re
        
        # Patrones para nombres de proveedor
        patterns = [
            r'(?:proveedor|supplier|vendedor|vendor|emisor)[\s:]*([A-Za-z0-9\s\.,]+?)(?:\r?\n|$)',
            r'(?:razon social|business name|nombre fiscal)[\s:]*([A-Za-z0-9\s\.,]+?)(?:\r?\n|$)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                if match.group(1).strip():
                    return match.group(1).strip()
        
        return None
    
    def _extract_vat(self, text):
        """Extrae el NIF/CIF del texto"""
        import re
        
        # Patrones para NIF/CIF español
        patterns = [
            # CIF/NIF español (letra + 8 dígitos o 8 dígitos + letra)
            r'(?:nif|cif|tax id|vat|tax number)[\s:]*([A-Za-z0-9]{1,2}\d{7,8}[A-Za-z0-9]?)',
            # Buscar directamente patrones de NIF/CIF
            r'([ABCDEFGHJKLMNPQRSUVW]\d{7}[A-J0-9])',  # CIF
            r'(\d{8}[A-Z])',  # NIF
            r'([XYZ]\d{7}[A-Z])',  # NIE
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                if match.group(1).strip():
                    return match.group(1).strip().upper()
        
        return None
    
    def _extract_total_amount(self, text):
        """Extrae el importe total del texto"""
        import re
        
        # Patrones para importes totales
        patterns = [
            r'(?:total|importe total|amount|suma)[\s:]*[\€\$\£]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))',
            r'(?:total|importe total|amount|suma)[\s:]*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))\s*[\€\$\£]?',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                amount_str = match.group(1).strip()
                try:
                    # Normalizar separadores
                    if ',' in amount_str and '.' in amount_str:
                        # Determinar cuál es el separador de miles y cuál el decimal
                        if amount_str.rindex(',') > amount_str.rindex('.'):
                            # La coma es el separador decimal
                            amount_str = amount_str.replace('.', '')
                            amount_str = amount_str.replace(',', '.')
                        else:
                            # El punto es el separador decimal
                            amount_str = amount_str.replace(',', '')
                    elif ',' in amount_str:
                        # Si solo hay comas, asumir que es el separador decimal
                        amount_str = amount_str.replace(',', '.')
                    
                    return float(amount_str)
                except:
                    continue
        
        return None
    
    def _extract_currency(self, text):
        """Extrae el código de moneda del texto"""
        import re
        
        # Buscar símbolos de moneda
        currency_map = {
            '€': 'EUR',
            '$': 'USD',
            '£': 'GBP',
            'eur': 'EUR',
            'euros': 'EUR',
            'euro': 'EUR',
            'usd': 'USD',
            'dolares': 'USD',
            'dólar': 'USD',
            'dollar': 'USD',
            'dollars': 'USD',
            'gbp': 'GBP',
            'libras': 'GBP',
            'pounds': 'GBP',
        }
        
        text_lower = text.lower()
        
        for symbol, code in currency_map.items():
            if symbol in text_lower:
                return code
        
        # Por defecto, asumimos euros para España
        return 'EUR'
    
    def _extract_tax_amount(self, text):
        """Extrae el importe de impuestos del texto"""
        import re
        
        # Patrones para IVA/impuestos
        patterns = [
            r'(?:iva|vat|igic|impuesto|tax)[^\n]*?(\d{1,2}(?:[.,]\d{1,2})?)[\s]*[%]',  # Porcentaje IVA
            r'(?:iva|vat|igic|impuesto|tax|i\.v\.a)[^\n]*?[\€\$\£]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))',  # Importe IVA
            r'(?:iva|vat|igic|impuesto|tax|i\.v\.a)[^\n]*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))\s*[\€\$\£]?',  # Importe IVA
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text.lower())
            for match in matches:
                tax_str = match.group(1).strip()
                try:
                    # Si parece un porcentaje (entre 0 y 100), lo ignoramos
                    if float(tax_str.replace(',', '.')) <= 100 and '%' in match.group(0):
                        continue
                        
                    # Normalizar separadores
                    if ',' in tax_str:
                        tax_str = tax_str.replace(',', '.')
                        
                    return float(tax_str)
                except:
                    continue
        
        return None


# Añadimos el OCR a los modelos de Odoo
class DocumentScan(models.Model):
    _inherit = 'document.scan'
    
    def _process_with_tesseract_ocr(self, pdf_data=None):
        """Procesa un documento PDF con Tesseract OCR"""
        self.ensure_one()
        
        if not pdf_data and self.attachment_id:
            pdf_data = base64.b64decode(self.attachment_id.datas)
        
        if not pdf_data:
            raise UserError(_("No se encontró contenido PDF para procesar"))
        
        # Crear instancia OCR
        ocr = DocumentOCR(self.env)
        
        # Verificar disponibilidad
        if not ocr.is_available():
            self.write({
                'status': 'error',
                'notes': f"{self.notes or ''}\nOCR no disponible. Verifique que Tesseract esté instalado correctamente.",
            })
            return False
        
        try:
            # Procesar documento
            self.write({'status': 'processing'})
            
            # Registrar inicio
            start_time = datetime.now()
            
            # Ejecutar OCR
            ocr_result = ocr.process_pdf(pdf_data)
            
            # Actualizar documento con resultados
            self.write({
                'ocr_text': ocr_result['text'],
                'ocr_data': json.dumps(ocr_result['structured_data']),
                'confidence_score': ocr_result['structured_data']['confidence'],
                'processing_notes': f"{self.processing_notes or ''}\n\nDocumento procesado con Tesseract OCR\n"
                                    f"Páginas: {ocr_result['pages']}\n"
                                    f"Confianza: {ocr_result['confidence']:.2f}%",
                'processing_time': (datetime.now() - start_time).total_seconds(),
            })
            
            # Registramos la acción en el log
            self.env['document.scan.log'].create({
                'document_id': self.id,
                'user_id': self.env.user.id,
                'action': 'ocr_processing',
                'description': _('OCR procesado con Tesseract. Confianza: %s%%') % round(ocr_result['structured_data']['confidence'], 2)
            })
            
            return True
            
        except Exception as e:
            self.write({
                'status': 'error',
                'notes': f"{self.notes or ''}\nError OCR: {str(e)}",
            })
            
            _logger.error(f"Error en OCR: {str(e)}")
            
            # Registramos el error en el log
            self.env['document.scan.log'].create({
                'document_id': self.id,
                'user_id': self.env.user.id,
                'action': 'error',
                'description': _('Error en procesamiento OCR: %s') % str(e)
            })
            
            return False
    
    def _process_with_alternative_ocr(self):
        """Implementación alternativa de OCR usando Tesseract"""
        return self._process_with_tesseract_ocr()
