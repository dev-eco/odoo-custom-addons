# -*- coding: utf-8 -*-
import base64
import logging
import os
import tempfile
from PIL import Image
import cv2
import numpy as np
import pytesseract
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class DocumentOCR(models.AbstractModel):
    """Modelo abstracto para funcionalidades de OCR"""
    _name = 'document.ocr'
    _description = 'Funcionalidades OCR para documentos'

    @api.model
    def preprocess_image(self, image_path, dpi=300):
        """
        Preprocesa la imagen para mejorar resultados del OCR
        """
        try:
            # Leer la imagen
            img = cv2.imread(image_path)
            if img is None:
                _logger.error("No se pudo cargar la imagen: %s", image_path)
                return image_path

            # Convertir a escala de grises
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Cambiar resolución si es necesario (mayor resolución = mejor OCR)
            height, width = gray.shape
            if width > 2000 or height > 2000:
                # La imagen ya es de alta resolución
                pass
            else:
                # Calcular factor de escala para llegar a ~300 DPI
                scale_factor = dpi / 72.0  # Asumiendo imagen estándar de 72 DPI
                gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

            # Método de binarización adaptativa
            # Probamos dos métodos y nos quedamos con el mejor
            binary_adaptive1 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            _, binary_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # Reducción de ruido
            denoised1 = cv2.fastNlMeansDenoising(binary_adaptive1, h=10)
            denoised2 = cv2.fastNlMeansDenoising(binary_otsu, h=10)

            # Guardar imágenes preprocesadas
            processed_path1 = image_path + '_adaptive.png'
            processed_path2 = image_path + '_otsu.png'
            
            cv2.imwrite(processed_path1, denoised1)
            cv2.imwrite(processed_path2, denoised2)

            # Devolver rutas de ambas imágenes para intentar ambos métodos
            return [processed_path1, processed_path2]
        except Exception as e:
            _logger.error("Error en preprocesamiento de imagen: %s", str(e))
            return [image_path]  # Devolver imagen original si hay error

    @api.model
    def convert_pdf_to_images(self, pdf_path, dpi=300):
        """
        Convierte un PDF a imágenes para OCR
        """
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=dpi)
            
            image_paths = []
            for i, image in enumerate(images):
                img_path = f"{pdf_path}_page{i+1}.png"
                image.save(img_path, 'PNG')
                image_paths.append(img_path)
                
            return image_paths
        except Exception as e:
            _logger.error("Error al convertir PDF a imágenes: %s", str(e))
            return []

    @api.model
    def perform_ocr_with_tesseract(self, image_path, lang='spa+eng'):
        """
        Realiza OCR utilizando Tesseract con configuración optimizada
        """
        try:
            # Configuración óptima para documentos comerciales
            # Ver: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
            custom_config = f'--oem 3 --psm 6 -l {lang} --dpi 300 -c preserve_interword_spaces=1 -c textord_min_linesize=2.5'
            
            # Obtener el texto
            text = pytesseract.image_to_string(image_path, config=custom_config)
            return text
        except Exception as e:
            _logger.error("Error en OCR con Tesseract: %s", str(e))
            return ""

    @api.model
    def extract_text_from_image(self, image_path, lang='spa+eng'):
        """
        Proceso completo de extracción de texto optimizado
        """
        # Preprocesar imagen
        processed_paths = self.preprocess_image(image_path)
        
        # Intentar OCR en todas las versiones preprocesadas
        results = []
        for path in processed_paths:
            text = self.perform_ocr_with_tesseract(path, lang)
            results.append((path, text))
            
            # Eliminar archivo temporal
            try:
                if os.path.exists(path) and path != image_path:
                    os.unlink(path)
            except:
                pass
        
        # Seleccionar el mejor resultado (el más largo asumiendo que capturó más texto)
        best_result = max(results, key=lambda x: len(x[1]))
        return best_result[1]

    @api.model
    def extract_text_from_document(self, document_file, file_type, langs='spa+eng'):
        """
        Extrae texto de un documento (PDF o imagen)
        """
        if not document_file:
            return ""
            
        try:
            # Decodificar archivo base64
            file_data = base64.b64decode(document_file)
            
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(file_type)) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name
            
            # Procesar según tipo de archivo
            if 'pdf' in file_type.lower():
                # Convertir PDF a imágenes
                image_paths = self.convert_pdf_to_images(temp_file_path)
                
                # Realizar OCR en cada página
                full_text = ""
                for img_path in image_paths:
                    text = self.extract_text_from_image(img_path, langs)
                    full_text += text + "\n\n"
                    
                    # Eliminar archivo temporal
                    try:
                        os.unlink(img_path)
                    except:
                        pass
                        
                result = full_text
            else:
                # Imagen directa
                result = self.extract_text_from_image(temp_file_path, langs)
            
            # Eliminar archivo temporal principal
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
            return result
        except Exception as e:
            _logger.error("Error extrayendo texto del documento: %s", str(e))
            return ""
    
    @api.model
    def _get_file_extension(self, file_type):
        """Devuelve la extensión adecuada según el tipo de archivo"""
        if 'pdf' in file_type.lower():
            return '.pdf'
        elif 'jpeg' in file_type.lower() or 'jpg' in file_type.lower():
            return '.jpg'
        elif 'png' in file_type.lower():
            return '.png'
        elif 'tiff' in file_type.lower() or 'tif' in file_type.lower():
            return '.tiff'
        else:
            return '.bin'
