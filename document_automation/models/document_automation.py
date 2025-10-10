# models/document_automation.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging
import os
import tempfile
from datetime import datetime
import re
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

# Importación condicional de dependencias externas
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    import magic
    import pdfplumber
    import regex as re2  # Regex avanzado para patrones complejos
except ImportError as err:
    _logger.warning(f"Dependencia externa no encontrada: {err}")

class DocumentAutomation(models.Model):
    _name = 'document.automation'
    _description = 'Documento Automatizado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(
        string='Referencia', 
        required=True, 
        readonly=True, 
        default='/',
        copy=False, 
        tracking=True,
        help="Identificador único del documento procesado"
    )
    
    # Campos de archivo
    document_file = fields.Binary(
        string='Archivo', 
        attachment=True, 
        required=True,
        help="Documento original en formato PDF o imagen"
    )
    filename = fields.Char(
        string='Nombre de archivo',
        help="Nombre original del archivo cargado"
    )
    file_size = fields.Integer(
        string='Tamaño (KB)', 
        compute='_compute_file_size', 
        store=True,
        help="Tamaño del archivo en kilobytes"
    )
    file_type = fields.Selection([
        ('pdf', 'PDF'),
        ('image', 'Imagen'),
        ('text', 'Texto'),
        ('xml', 'XML'),
        ('other', 'Otro')
    ], string='Tipo de archivo', compute='_compute_file_type', store=True)
    
    # Campos de contenido
    ocr_text = fields.Text(
        string='Texto extraído', 
        readonly=True,
        help="Texto extraído mediante OCR del documento"
    )
    
    # Campos de clasificación
    document_type_id = fields.Many2one(
        'document.type',
        string='Tipo de documento',
        tracking=True,
        help="Tipo de documento detectado automáticamente o asignado manualmente"
    )
    detected_type_ids = fields.Many2many(
        'document.type',
        'document_automation_type_rel',
        'document_id', 
        'type_id',
        string='Tipos detectados',
        help="Tipos de documento posibles detectados automáticamente"
    )
    
    # Campos de estado
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('processing', 'Procesando'),
        ('to_validate', 'Por validar'),
        ('validated', 'Validado'),
        ('linked', 'Vinculado'),
        ('error', 'Error'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True, group_expand='_expand_states')
    
    status_message = fields.Text(
        string='Mensaje de estado',
        readonly=True,
        help="Detalles adicionales sobre el estado actual del documento"
    )
    
    # Campos de origen
    source = fields.Selection([
        ('email', 'Correo electrónico'),
        ('scan', 'Escáner'),
        ('upload', 'Carga manual'),
        ('api', 'API'),
        ('folder', 'Carpeta vigilada')
    ], string='Origen', default='upload', required=True)
    
    source_reference = fields.Char(
        string='Referencia de origen', 
        help="ID de mensaje, ruta de archivo, etc."
    )
    
    # Campos de seguimiento
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía',
        required=True, 
        default=lambda self: self.env.company
    )
    user_id = fields.Many2one(
        'res.users', 
        string='Responsable', 
        default=lambda self: self.env.user,
        tracking=True
    )
    create_date = fields.Datetime(
        string='Fecha de creación', 
        readonly=True
    )
    processed_date = fields.Datetime(
        string='Fecha de procesamiento',
        readonly=True
    )
    validated_date = fields.Datetime(
        string='Fecha de validación',
        readonly=True
    )
    
    # Campos de extracción y resultado
    confidence_score = fields.Float(
        string='Puntuación de confianza', 
        default=0.0,
        help="Nivel de confianza en la extracción automática (0-100%)"
    )
    
    extracted_data = fields.Text(
        string='Datos extraídos',
        help="Datos extraídos en formato JSON"
    )
    
    result_model = fields.Char(
        string='Modelo resultante',
        help="Modelo técnico de Odoo generado a partir del documento"
    )
    result_id = fields.Integer(
        string='ID resultante',
        help="ID del registro generado en el modelo resultante"
    )
    result_reference = fields.Char(
        string='Referencia resultante',
        compute='_compute_result_reference',
        help="Referencia legible del documento generado"
    )
    
    # Campos de deduplicación
    content_hash = fields.Char(
        string='Hash de contenido', 
        index=True,
        help="Hash único del contenido del documento para evitar duplicados"
    )
    is_duplicate = fields.Boolean(
        string='Es duplicado',
        compute='_compute_is_duplicate',
        search='_search_is_duplicate',
        help="Indica si el documento parece ser un duplicado"
    )
    duplicate_id = fields.Many2one(
        'document.automation',
        string='Documento original',
        compute='_compute_duplicate_id',
        help="Referencia al documento original del que éste podría ser duplicado"
    )
    
    # Campos relacionales
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=lambda self: [('res_model', '=', self._name)],
        string='Archivos adjuntos',
        help="Archivos adjuntos adicionales relacionados con este documento"
    )
    
    log_ids = fields.One2many(
        'document.automation.log',
        'document_id',
        string='Registro de acciones',
        help="Historial detallado de acciones realizadas sobre el documento"
    )
    
    error_count = fields.Integer(
        string='Errores', 
        compute='_compute_error_count'
    )
    
    # Restricciones SQL y validaciones
    _sql_constraints = [
        ('unique_content_hash', 'unique(content_hash, company_id)', 
         'Ya existe un documento con el mismo contenido en esta compañía')
    ]
    
    @api.constrains('document_file')
    def _check_document_file(self):
        for record in self:
            if not record.document_file:
                raise ValidationError(_("El documento debe contener un archivo."))
            
            # Validar tamaño máximo (10MB)
            file_content = base64.b64decode(record.document_file)
            if len(file_content) > 10 * 1024 * 1024:  # 10 MB en bytes
                raise ValidationError(_("El tamaño del archivo no puede exceder 10 MB."))
    
    @api.depends('document_file')
    def _compute_file_size(self):
        for record in self:
            record.file_size = 0
            if not record.document_file:
                continue
                
            try:
                # Asegurar que los datos base64 tengan el padding correcto
                data = record.document_file
                # Si es string, convertir a bytes para Python 3
                if isinstance(data, str):
                    # Asegurarnos que el padding es correcto añadiendo '=' si es necesario
                    missing_padding = len(data) % 4
                    if missing_padding:
                        data += '=' * (4 - missing_padding)
                    # Convertir a bytes si es necesario
                    if not isinstance(data, bytes):
                        data = data.encode('utf-8')
                        
                # Decodificar y calcular tamaño
                content = base64.b64decode(data)
                record.file_size = len(content)
            except Exception as e:
                # Registrar error pero continuar
                _logger.warning("Error calculando tamaño de archivo para documento %s: %s", record.id, e)    

    @api.depends('document_file', 'filename')
    def _compute_file_type(self):
        for record in self:
            if not record.document_file:
                record.file_type = 'other'
                continue
            
            # Comprobar por extensión de archivo primero
            if record.filename:
                ext = Path(record.filename).suffix.lower()
                if ext in ('.pdf'):
                    record.file_type = 'pdf'
                    continue
                elif ext in ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'):
                    record.file_type = 'image'
                    continue
                elif ext in ('.txt', '.csv', '.log'):
                    record.file_type = 'text'
                    continue
                elif ext in ('.xml', '.html'):
                    record.file_type = 'xml'
                    continue
            
            # Si no se puede determinar por extensión, intentar por contenido
            try:
                file_content = base64.b64decode(record.document_file)
                mime = magic.from_buffer(file_content, mime=True)
                
                if mime.startswith('application/pdf'):
                    record.file_type = 'pdf'
                elif mime.startswith('image/'):
                    record.file_type = 'image'
                elif mime in ('text/plain', 'text/csv'):
                    record.file_type = 'text'
                elif mime in ('text/xml', 'application/xml', 'text/html'):
                    record.file_type = 'xml'
                else:
                    record.file_type = 'other'
            except Exception as e:
                _logger.error(f"Error al determinar el tipo de archivo: {e}")
                record.file_type = 'other'
    
    @api.depends('result_model', 'result_id')
    def _compute_result_reference(self):
        for record in self:
            if record.result_model and record.result_id:
                try:
                    # Intentar obtener el registro resultante
                    result = self.env[record.result_model].browse(record.result_id).exists()
                    if result:
                        # Usar name, display_name o cualquier otro campo identificativo
                        record.result_reference = result.display_name
                    else:
                        record.result_reference = f"{record.result_model},{record.result_id}"
                except Exception as e:
                    _logger.error(f"Error al obtener referencia: {e}")
                    record.result_reference = f"{record.result_model},{record.result_id}"
            else:
                record.result_reference = False
    
    @api.depends('content_hash', 'company_id')
    def _compute_is_duplicate(self):
        for record in self:
            if not record.content_hash:
                record.is_duplicate = False
                continue
                
            # Buscar si hay documentos anteriores con el mismo hash
            count = self.env['document.automation'].search_count([
                ('id', '!=', record.id),
                ('content_hash', '=', record.content_hash),
                ('company_id', '=', record.company_id.id),
                ('create_date', '<', record.create_date or fields.Datetime.now())
            ])
            record.is_duplicate = count > 0
    
    def _search_is_duplicate(self, operator, value):
        # Implementación de búsqueda para el campo computado is_duplicate
        if operator not in ('=', '!=') or not isinstance(value, bool):
            return []
            
        # Documentos con hashes que aparecen más de una vez
        duplicated_hashes = self.env['document.automation'].read_group(
            domain=[('content_hash', '!=', False)],
            fields=['content_hash'],
            groupby=['content_hash'],
            having=[('content_hash_count', '>', 1)]
        )
        
        hash_values = [x['content_hash'] for x in duplicated_hashes]
        
        if not hash_values:
            # No hay duplicados en el sistema
            return [('id', '=', 0)] if value else [('id', '!=', 0)]
        
        # Para cada hash, encontrar todos los documentos excepto el más antiguo
        domain = []
        for hash_value in hash_values:
            oldest_doc = self.env['document.automation'].search([
                ('content_hash', '=', hash_value)
            ], order='create_date asc', limit=1)
            
            if oldest_doc:
                domain.append(('id', '!=', oldest_doc.id))
                domain.append(('content_hash', '=', hash_value))
        
        # Operador lógico OR entre cada par
        final_domain = ['&', '&'] * (len(hash_values) - 1)
        final_domain.extend(domain)
        
        if operator == '!=':
            final_domain = ['!'] + final_domain
            
        return final_domain
    
    @api.depends('content_hash', 'is_duplicate')
    def _compute_duplicate_id(self):
        for record in self:
            if not record.is_duplicate or not record.content_hash:
                record.duplicate_id = False
                continue
                
            # Buscar el documento original (más antiguo) con el mismo hash
            original = self.env['document.automation'].search([
                ('id', '!=', record.id),
                ('content_hash', '=', record.content_hash),
                ('company_id', '=', record.company_id.id)
            ], order='create_date asc', limit=1)
            
            record.duplicate_id = original.id if original else False
    
    def _compute_error_count(self):
        for record in self:
            record.error_count = self.env['document.automation.log'].search_count([
                ('document_id', '=', record.id),
                ('level', '=', 'error')
            ])
    
    def _expand_states(self, states, domain, order):
        # Para agrupar por estado en las vistas kanban/graph
        return [key for key, _val in self._fields['state'].selection]
    
    # Métodos ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Asignar secuencia para nuevos documentos
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('document.automation')
            
            # Generar hash de contenido para documentos nuevos
            if 'document_file' in vals and not vals.get('content_hash'):
                content = base64.b64decode(vals['document_file'])
                vals['content_hash'] = hashlib.sha256(content).hexdigest()
        
        documents = super(DocumentAutomation, self).create(vals_list)
        
        # Programar procesamiento automático para documentos nuevos
        for document in documents:
            document.log_action('create', _('Documento creado'))
            if document.state == 'draft':
                document.with_delay().process_document()
        
        return documents
    
    def write(self, vals):
        # Control de cambios en el archivo
        if 'document_file' in vals:
            content = base64.b64decode(vals['document_file'])
            vals['content_hash'] = hashlib.sha256(content).hexdigest()
            # Resetear estado si se cambia el archivo
            vals.update({
                'state': 'draft',
                'ocr_text': False,
                'extracted_data': False,
                'document_type_id': False,
                'detected_type_ids': [(5, 0, 0)],  # Limpiar m2m
                'processed_date': False,
                'validated_date': False,
            })
            
        result = super(DocumentAutomation, self).write(vals)
        
        # Si cambia a borrador, reprocesar
        if vals.get('state') == 'draft':
            for record in self:
                record.with_delay().process_document()
        
        # Registrar cambios importantes
        tracked_fields = ['document_type_id', 'state', 'user_id']
        for field in tracked_fields:
            if field in vals:
                for record in self:
                    record.log_action('write', _('Campo %s modificado') % field)
        
        return result
    
    def unlink(self):
        # Evitar eliminación de documentos procesados
        for record in self:
            if record.state not in ['draft', 'error', 'cancelled']:
                raise UserError(_("No se pueden eliminar documentos que ya han sido procesados."))
                
            # Registrar la eliminación
            record.log_action('unlink', _('Documento eliminado'))
        
        return super(DocumentAutomation, self).unlink()
    
    # Métodos de procesamiento
    def process_document(self):
        self.ensure_one()
        
        if self.state not in ['draft', 'error']:
            return False
        
        try:
            self.write({
                'state': 'processing',
                'status_message': _("Iniciando procesamiento...")
            })
            self.log_action('process', _('Iniciando procesamiento del documento'))
            
            # 1. Extraer texto del documento
            self._extract_text_from_document()
            
            # 2. Clasificar el documento
            self._classify_document()
            
            # 3. Extraer información según el tipo
            if self.document_type_id:
                self._extract_information()
                
                # 4. Vincular o crear el documento correspondiente en Odoo
                if self.extracted_data:
                    self._create_odoo_document()
                    
                # 5. Actualizar estado según resultado
                if self.result_model and self.result_id:
                    self.write({
                        'state': 'linked',
                        'status_message': _("Documento procesado y vinculado con éxito"),
                        'processed_date': fields.Datetime.now()
                    })
                else:
                    self.write({
                        'state': 'to_validate',
                        'status_message': _("Documento procesado. Requiere validación manual."),
                        'processed_date': fields.Datetime.now()
                    })
            else:
                self.write({
                    'state': 'to_validate',
                    'status_message': _("No se pudo determinar el tipo de documento automáticamente."),
                    'processed_date': fields.Datetime.now()
                })
                
            return True
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.write({
                'state': 'error',
                'status_message': error_msg
            })
            self.log_action('error', error_msg)
            _logger.error("Error al procesar documento %s: %s", self.name, error_msg, exc_info=True)
            return False
    
    def _extract_text_from_document(self):
        """Extrae texto del documento mediante OCR o técnicas apropiadas según el tipo de archivo"""
        if not self.document_file:
            raise ValidationError(_("No hay archivo para procesar"))
            
        file_content = base64.b64decode(self.document_file)
        
        # Registrar inicio de extracción
        self.log_action('ocr', _('Iniciando extracción de texto'))
        
        if self.file_type == 'pdf':
            text = self._extract_text_from_pdf(file_content)
        elif self.file_type == 'image':
            text = self._extract_text_from_image(file_content)
        elif self.file_type == 'text':
            text = file_content.decode('utf-8', errors='replace')
        elif self.file_type == 'xml':
            text = file_content.decode('utf-8', errors='replace')
            # Podríamos parsear XML aquí para extraer texto estructurado
        else:
            raise UserError(_("Tipo de archivo no soportado para extracción de texto"))
            
        # Limpiar y normalizar el texto extraído
        if text:
            # Eliminar caracteres no imprimibles y normalizar espacios
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'[^\x20-\x7E\n\r\t\u00A0-\u00FF\u0100-\u017F]', '', text)
            
            self.write({
                'ocr_text': text,
                'status_message': _("Texto extraído correctamente")
            })
            
            # Registrar longitud de texto extraído
            self.log_action('ocr', _('Texto extraído: %s caracteres') % len(text))
        else:
            self.write({
                'ocr_text': '',
                'status_message': _("No se pudo extraer texto del documento")
            })
            self.log_action('warning', _('No se pudo extraer texto del documento'))
            
        return bool(text)
    
    def _extract_text_from_pdf(self, file_content):
        """Extrae texto de un archivo PDF utilizando pdfplumber y OCR si es necesario"""
        text = ""
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
            
        try:
            # Primero intentar extracción directa (más rápida y precisa si el PDF tiene texto)
            with pdfplumber.open(temp_file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n\n"
                    
            # Si no se extrajo texto suficiente, utilizar OCR
            if len(text.strip()) < 100:
                self.log_action('ocr', _('Texto insuficiente, usando OCR'))
                
                # Convertir PDF a imágenes
                images = convert_from_bytes(
                    file_content, 
                    dpi=300,
                    fmt='jpeg',
                    thread_count=2
                )
                
                for i, image in enumerate(images):
                    # Usar OCR con múltiples idiomas
                    page_text = pytesseract.image_to_string(
                        image, 
                        lang='spa+eng',
                        config='--psm 1 --oem 3'
                    )
                    text += page_text + "\n\n"
        except Exception as e:
            self.log_action('error', _(f"Error en extracción de PDF: {str(e)}"))
            _logger.error("Error al extraer texto de PDF: %s", str(e), exc_info=True)
            
            # Intentar sólo OCR si falló la extracción directa
            try:
                images = convert_from_bytes(file_content)
                for i, image in enumerate(images):
                    text += pytesseract.image_to_string(image, lang='spa+eng') + "\n\n"
            except Exception as e2:
                self.log_action('error', _(f"Error en OCR de PDF: {str(e2)}"))
                _logger.error("Error en OCR de PDF: %s", str(e2), exc_info=True)
        
        finally:
            # Limpiar archivos temporales
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
                
        return text
    
    def _extract_text_from_image(self, file_content):
        """Extrae texto de una imagen utilizando OCR"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
            
        try:
            # Usar configuración óptima para OCR
            text = pytesseract.image_to_string(
                temp_file_path, 
                lang='spa+eng',
                config='--psm 1 --oem 3'
            )
            return text
        except Exception as e:
            self.log_action('error', _(f"Error en OCR de imagen: {str(e)}"))
            _logger.error("Error en OCR de imagen: %s", str(e), exc_info=True)
            return ""
        finally:
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    
    def _classify_document(self):
        """Clasifica el documento basado en su contenido"""
        if not self.ocr_text:
            self.log_action('warning', _('No hay texto para clasificar el documento'))
            return False
            
        text = self.ocr_text.lower()
        
        # Obtener todos los tipos de documento activos
        document_types = self.env['document.type'].search([
            ('active', '=', True),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)
        ])
        
        if not document_types:
            self.log_action('warning', _('No hay tipos de documento configurados'))
            return False
            
        # Evaluar cada tipo de documento
        candidates = []
        detected_types = []
        
        for doc_type in document_types:
            score = 0
            matched_patterns = []
            
            # Evaluar por palabras clave
            if doc_type.keywords:
                for keyword in doc_type.keywords.split(','):
                    keyword = keyword.strip().lower()
                    if keyword and keyword in text:
                        score += 1
                        matched_patterns.append(f"Keyword: {keyword}")
            
            # Evaluar por patrones regulares
            if doc_type.regex_patterns:
                for pattern in doc_type.regex_patterns.split('\n'):
                    pattern = pattern.strip()
                    if not pattern:
                        continue
                        
                    try:
                        if re.search(pattern, text, re.IGNORECASE):
                            score += 2  # Los patrones regex valen más que simples keywords
                            matched_patterns.append(f"Regex: {pattern}")
                    except Exception as e:
                        _logger.warning("Error en patrón regex '%s': %s", pattern, str(e))
            
            # Evaluar por patrones complejos
            if doc_type.advanced_patterns:
                for pattern_data in json.loads(doc_type.advanced_patterns or '[]'):
                    pattern = pattern_data.get('pattern', '')
                    weight = pattern_data.get('weight', 1)
                    
                    if not pattern:
                        continue
                        
                    try:
                        if re2.search(pattern, text, re2.IGNORECASE):
                            score += weight
                            matched_patterns.append(f"Advanced: {pattern[:20]}... ({weight})")
                    except Exception as e:
                        _logger.warning("Error en patrón avanzado '%s': %s", pattern, str(e))
            
            # Si obtuvo alguna puntuación, es candidato
            if score > 0:
                candidates.append({
                    'type_id': doc_type.id,
                    'score': score,
                    'confidence': min(score / 10.0, 1.0),  # Normalizar entre 0-1
                    'patterns': matched_patterns
                })
                detected_types.append(doc_type.id)
                
        # Ordenar candidatos por puntuación
        candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        
        # Registrar resultados de clasificación
        for candidate in candidates:
            self.log_action('classify', _(
                'Tipo candidato: %s (Score: %s, Confianza: %.2f%%)') % (
                    self.env['document.type'].browse(candidate['type_id']).name,
                    candidate['score'],
                    candidate['confidence'] * 100
                )
            )
        
        # Actualizar documento con el mejor candidato si hay alguno
        if candidates:
            best_candidate = candidates[0]
            self.write({
                'document_type_id': best_candidate['type_id'],
                'confidence_score': best_candidate['confidence'],
                'detected_type_ids': [(6, 0, detected_types)],
                'status_message': _("Documento clasificado como %s (Confianza: %.2f%%)") % (
                    self.env['document.type'].browse(best_candidate['type_id']).name,
                    best_candidate['confidence'] * 100
                )
            })
            return True
        else:
            self.write({
                'status_message': _("No se pudo clasificar el documento automáticamente")
            })
            self.log_action('warning', _('No se encontró un tipo de documento coincidente'))
            return False
    
    def _extract_information(self):
        """Extrae información estructurada basada en el tipo de documento"""
        if not self.document_type_id or not self.ocr_text:
            return False
            
        # Obtener plantilla de extracción para este tipo de documento
        doc_type = self.document_type_id
        
        # Registrar inicio de extracción
        self.log_action('extract', _('Iniciando extracción de datos para tipo %s') % doc_type.name)
        
        # Extraer información usando el método específico del tipo
        handler_method = f'_extract_{doc_type.code}'
        
        if hasattr(self, handler_method):
            # Usar método específico si existe
            handler = getattr(self, handler_method)
            result = handler()
        elif doc_type.extraction_template:
            # Usar plantilla genérica de extracción
            result = self._extract_with_template(doc_type.extraction_template)
        else:
            # Sin método ni plantilla
            self.log_action('warning', _('No hay método ni plantilla para extraer datos'))
            return False
            
        if not result:
            self.log_action('warning', _('Extracción de datos fallida'))
            return False
            
        # Guardar datos extraídos en formato JSON
        try:
            self.write({
                'extracted_data': json.dumps(result, indent=2, ensure_ascii=False),
                'status_message': _("Datos extraídos correctamente")
            })
            self.log_action('extract', _('Datos extraídos correctamente'))
            return True
        except Exception as e:
            self.log_action('error', _(f"Error al guardar datos extraídos: {str(e)}"))
            return False
    
    def _extract_with_template(self, template_str):
        """Extrae datos usando una plantilla JSON de patrones"""
        try:
            template = json.loads(template_str)
            text = self.ocr_text
            
            result = {}
            
            # Procesar cada campo en la plantilla
            for field in template.get('fields', []):
                field_name = field.get('name')
                field_type = field.get('type', 'text')
                
                patterns = field.get('patterns', [])
                
                # Buscar el primer patrón que coincida
                field_value = None
                
                for pattern in patterns:
                    regex = pattern.get('regex')
                    if not regex:
                        continue
                        
                    try:
                        match = re.search(regex, text, re.IGNORECASE | re.MULTILINE)
                        if match:
                            # Extraer grupo de captura o coincidencia completa
                            if match.groups():
                                field_value = match.group(1)
                            else:
                                field_value = match.group(0)
                                
                            # Aplicar post-procesamiento según tipo
                            if field_type == 'amount':
                                field_value = field_value.replace(',', '.').strip()
                                field_value = re.sub(r'[^\d.]+', '', field_value)
                                field_value = float(field_value) if field_value else 0.0
                                
                            elif field_type == 'date':
                                # Intentar varios formatos de fecha
                                date_formats = ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d']
                                parsed_date = None
                                
                                for fmt in date_formats:
                                    try:
                                        parsed_date = datetime.strptime(field_value.strip(), fmt).strftime('%Y-%m-%d')
                                        break
                                    except (ValueError, AttributeError):
                                        continue
                                
                                field_value = parsed_date
                                
                            elif field_type == 'integer':
                                field_value = re.sub(r'[^\d]+', '', field_value)
                                field_value = int(field_value) if field_value else 0
                                
                            result[field_name] = field_value
                            break
                    except Exception as e:
                        _logger.warning("Error procesando patrón '%s': %s", regex, str(e))
            
            # Validar resultados si hay reglas definidas
            if 'validation' in template:
                for rule in template.get('validation', []):
                    field = rule.get('field')
                    condition = rule.get('condition')
                    
                    if field not in result:
                        continue
                        
                    if condition == 'required' and not result[field]:
                        self.log_action('warning', _(f"Campo requerido '{field}' no encontrado"))
                        if rule.get('critical', False):
                            return None
            
            return result
            
        except Exception as e:
            self.log_action('error', _(f"Error en plantilla de extracción: {str(e)}"))
            _logger.error("Error en extracción con plantilla: %s", str(e), exc_info=True)
            return None
    
    # Métodos específicos para diferentes tipos de documento
    def _extract_invoice(self):
        """Extrae datos de una factura"""
        text = self.ocr_text
        
        # Patrones comunes para facturas
        result = {}
        
        # Extraer NIF/CIF del proveedor
        vat_match = re.search(r'(?:NIF|CIF|VAT)[:. ]?\s*([A-Za-z0-9]{8,15})', text, re.IGNORECASE)
        if vat_match:
            result['vat'] = vat_match.group(1).strip().upper()
            
        # Extraer número de factura
        invoice_number_match = re.search(r'(?:Factura|Invoice|Núm[.:]|No[.:])\s*(?:de)?[: ]?\s*([A-Za-z0-9_\-/]+)', text, re.IGNORECASE)
        if invoice_number_match:
            result['invoice_number'] = invoice_number_match.group(1).strip()
            
        # Extraer fecha de factura
        date_match = re.search(r'(?:Fecha|Date)[: ]\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}[/.-]\d{1,2}[/.-]\d{1,2})', text, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
            # Intentar varios formatos
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    result['invoice_date'] = parsed_date.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
        
        # Extraer importe total
        total_match = re.search(r'(?:Total|Amount)[: ]\s*(?:EUR|€|USD|\$)?\s*([0-9.,]+)', text, re.IGNORECASE)
        if total_match:
            amount_str = total_match.group(1).replace(',', '.').strip()
            try:
                result['amount_total'] = float(amount_str)
            except ValueError:
                pass
                
        # Extraer IVA/impuestos
        tax_match = re.search(r'(?:IVA|VAT|Tax)[: ]\s*(?:\d{1,2}[%])?[: ]\s*(?:EUR|€|USD|\$)?\s*([0-9.,]+)', text, re.IGNORECASE)
        if tax_match:
            tax_str = tax_match.group(1).replace(',', '.').strip()
            try:
                result['amount_tax'] = float(tax_str)
            except ValueError:
                pass
                
        # Extraer base imponible
        base_match = re.search(r'(?:Base|Subtotal|Net)[: ]\s*(?:EUR|€|USD|\$)?\s*([0-9.,]+)', text, re.IGNORECASE)
        if base_match:
            base_str = base_match.group(1).replace(',', '.').strip()
            try:
                result['amount_untaxed'] = float(base_str)
            except ValueError:
                pass
        
        # Buscar proveedor por VAT si lo tenemos
        if result.get('vat'):
            partner = self.env['res.partner'].search([
                '|', 
                ('vat', '=ilike', result['vat']),
                ('vat', '=ilike', 'ES' + result['vat'])
            ], limit=1)
            
            if partner:
                result['partner_id'] = partner.id
                result['partner_name'] = partner.name
        
        # Registrar hallazgos clave
        log_message = "Datos extraídos de factura: "
        log_parts = []
        
        for key, value in result.items():
            if value:
                log_parts.append(f"{key}={value}")
                
        self.log_action('extract', log_message + ", ".join(log_parts))
        
        return result
    
    def _extract_purchase_order(self):
        """Extrae datos de un pedido de compra"""
        text = self.ocr_text
        result = {}
        
        # Extraer número de pedido
        order_number_match = re.search(r'(?:Pedido|Order|No[.:])[: ]\s*([A-Za-z0-9_\-/]+)', text, re.IGNORECASE)
        if order_number_match:
            result['order_number'] = order_number_match.group(1).strip()
            
        # Extraer fecha de pedido
        date_match = re.search(r'(?:Fecha|Date)[: ]\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}[/.-]\d{1,2}[/.-]\d{1,2})', text, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
            # Intentar varios formatos
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    result['date_order'] = parsed_date.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
        
        # Extraer proveedor
        vendor_vat_match = re.search(r'(?:NIF|CIF|VAT)[: ]\s*([A-Za-z0-9]{8,15})', text, re.IGNORECASE)
        if vendor_vat_match:
            result['vendor_vat'] = vendor_vat_match.group(1).strip().upper()
            
            # Buscar proveedor por VAT
            partner = self.env['res.partner'].search([
                '|', 
                ('vat', '=ilike', result['vendor_vat']),
                ('vat', '=ilike', 'ES' + result['vendor_vat'])
            ], limit=1)
            
            if partner:
                result['partner_id'] = partner.id
                result['partner_name'] = partner.name
        
        # Extraer líneas de pedido (más complejo, simplificado aquí)
        # Búsqueda de productos por descripción podría ser parte de una implementación avanzada
        
        self.log_action('extract', _("Datos extraídos de pedido de compra"))
        
        return result
    
    def _extract_delivery(self):
        """Extrae datos de un albarán de entrega"""
        text = self.ocr_text
        result = {}
        
        # Extraer número de albarán
        delivery_number_match = re.search(r'(?:Albarán|Delivery|Note)[: ]\s*([A-Za-z0-9_\-/]+)', text, re.IGNORECASE)
        if delivery_number_match:
            result['delivery_number'] = delivery_number_match.group(1).strip()
            
        # Extraer fecha de entrega
        date_match = re.search(r'(?:Fecha|Date)[: ]\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}[/.-]\d{1,2}[/.-]\d{1,2})', text, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
            # Intentar varios formatos
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    result['date'] = parsed_date.strftime('%Y-%m-%d')
                    break
                except ValueError:
                    continue
                    
        # Extraer proveedor/cliente
        partner_vat_match = re.search(r'(?:NIF|CIF|VAT)[: ]\s*([A-Za-z0-9]{8,15})', text, re.IGNORECASE)
        if partner_vat_match:
            result['partner_vat'] = partner_vat_match.group(1).strip().upper()
            
            # Buscar partner por VAT
            partner = self.env['res.partner'].search([
                '|', 
                ('vat', '=ilike', result['partner_vat']),
                ('vat', '=ilike', 'ES' + result['partner_vat'])
            ], limit=1)
            
            if partner:
                result['partner_id'] = partner.id
                result['partner_name'] = partner.name
                
        # Buscar referencias a pedidos relacionados
        order_ref_match = re.search(r'(?:Pedido|Order)[: ]\s*([A-Za-z0-9_\-/]+)', text, re.IGNORECASE)
        if order_ref_match:
            result['order_reference'] = order_ref_match.group(1).strip()
            
            # Intentar localizar el pedido relacionado
            order = self.env['purchase.order'].search([
                ('name', '=ilike', result['order_reference'])
            ], limit=1)
            
            if order:
                result['order_id'] = order.id
        
        # Extraer líneas de albarán (simplificado)
        
        self.log_action('extract', _("Datos extraídos de albarán de entrega"))
        
        return result
    
    def _create_odoo_document(self):
        """Crea o actualiza un documento en Odoo basado en los datos extraídos"""
        if not self.extracted_data or not self.document_type_id:
            return False
            
        try:
            data = json.loads(self.extracted_data)
        except Exception:
            self.log_action('error', _('Error al parsear datos extraídos'))
            return False
            
        # Obtener el modelo de destino y método de creación
        doc_type = self.document_type_id
        
        if not doc_type.model_id:
            self.log_action('warning', _('Tipo de documento sin modelo asociado'))
            return False
            
        model_name = doc_type.model_id.model
        create_method = f'_create_{doc_type.code}_document'
        
        if hasattr(self, create_method):
            # Usar método específico de creación
            create_func = getattr(self, create_method)
            return create_func(data)
        else:
            self.log_action('warning', _(f"No hay implementación para crear documento en {model_name}"))
            return False
    
    def _create_invoice_document(self, data):
        """Crea una factura borrador basada en los datos extraídos"""
        # Verificar datos mínimos requeridos
        if not data.get('partner_id') and not data.get('vat'):
            self.log_action('warning', _('No se identificó proveedor para la factura'))
            return False
            
        # Si no tenemos partner_id pero tenemos VAT, buscar de nuevo
        if not data.get('partner_id') and data.get('vat'):
            partner = self.env['res.partner'].search([
                '|', ('vat', '=ilike', data['vat']), ('vat', '=ilike', 'ES' + data['vat'])
            ], limit=1)
            
            if partner:
                data['partner_id'] = partner.id
            else:
                self.log_action('warning', _(f"No se encontró proveedor con NIF {data['vat']}"))
                return False
        
        # Verificar si ya existe una factura con el mismo número y proveedor
        if data.get('invoice_number') and data.get('partner_id'):
            existing_invoice = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('partner_id', '=', data['partner_id']),
                '|', 
                ('name', '=ilike', data['invoice_number']),
                ('ref', '=ilike', data['invoice_number'])
            ], limit=1)
            
            if existing_invoice:
                self.log_action('info', _(f"Factura ya existente: {existing_invoice.name}"))
                
                # Vincular a factura existente
                self.write({
                    'result_model': 'account.move',
                    'result_id': existing_invoice.id,
                    'status_message': _("Documento vinculado a factura existente")
                })
                
                # Adjuntar documento a factura existente
                attachment_vals = {
                    'name': self.filename or self.name,
                    'datas': self.document_file,
                    'res_model': 'account.move',
                    'res_id': existing_invoice.id,
                    'description': _("Documento escaneado automatizado")
                }
                self.env['ir.attachment'].create(attachment_vals)
                
                return True
        
        # Preparar valores para factura
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': data.get('partner_id'),
            'ref': data.get('invoice_number', ''),
        }
        
        # Fecha de factura
        if data.get('invoice_date'):
            try:
                invoice_vals['invoice_date'] = data['invoice_date']
            except Exception:
                pass
        
        # Crear la factura
        try:
            invoice = self.env['account.move'].create(invoice_vals)
            
            self.log_action('create', _(f"Factura creada: {invoice.name}"))
            
            # Añadir línea de factura si tenemos el importe
            if data.get('amount_total'):
                line_vals = {
                    'name': _('Importe detectado automáticamente'),
                    'quantity': 1,
                    'price_unit': float(data['amount_total']),
                }
                
                invoice.write({
                    'invoice_line_ids': [(0, 0, line_vals)]
                })
            
            # Vincular factura con documento
            self.write({
                'result_model': 'account.move',
                'result_id': invoice.id,
                'status_message': _("Documento procesado, factura creada en borrador")
            })
            
            # Adjuntar documento a factura
            attachment_vals = {
                'name': self.filename or self.name,
                'datas': self.document_file,
                'res_model': 'account.move',
                'res_id': invoice.id,
                'description': _("Documento escaneado automatizado")
            }
            self.env['ir.attachment'].create(attachment_vals)
            
            return True
            
        except Exception as e:
            self.log_action('error', _(f"Error al crear factura: {str(e)}"))
            return False
    
    def _create_purchase_order_document(self, data):
        """Crea un pedido de compra borrador basado en los datos extraídos"""
        # Verificar datos mínimos
        if not data.get('partner_id'):
            self.log_action('warning', _('No se identificó proveedor para el pedido'))
            return False
        
        # Verificar si ya existe un pedido con la misma referencia y proveedor
        if data.get('order_number') and data.get('partner_id'):
            existing_order = self.env['purchase.order'].search([
                ('partner_id', '=', data['partner_id']),
                ('name', '=ilike', data['order_number'])
            ], limit=1)
            
            if existing_order:
                self.log_action('info', _(f"Pedido ya existente: {existing_order.name}"))
                
                # Vincular a pedido existente
                self.write({
                    'result_model': 'purchase.order',
                    'result_id': existing_order.id,
                    'status_message': _("Documento vinculado a pedido existente")
                })
                
                # Adjuntar documento a pedido existente
                attachment_vals = {
                    'name': self.filename or self.name,
                    'datas': self.document_file,
                    'res_model': 'purchase.order',
                    'res_id': existing_order.id,
                }
                self.env['ir.attachment'].create(attachment_vals)
                
                return True
        
        # Preparar valores para pedido
        order_vals = {
            'partner_id': data.get('partner_id'),
        }
        
        # Fecha de pedido
        if data.get('date_order'):
            try:
                order_vals['date_order'] = data['date_order']
            except Exception:
                pass
        
        # Crear el pedido
        try:
            order = self.env['purchase.order'].create(order_vals)
            
            self.log_action('create', _(f"Pedido creado: {order.name}"))
            
            # Vincular pedido con documento
            self.write({
                'result_model': 'purchase.order',
                'result_id': order.id,
                'status_message': _("Documento procesado, pedido creado en borrador")
            })
            
            # Adjuntar documento a pedido
            attachment_vals = {
                'name': self.filename or self.name,
                'datas': self.document_file,
                'res_model': 'purchase.order',
                'res_id': order.id,
            }
            self.env['ir.attachment'].create(attachment_vals)
            
            return True
            
        except Exception as e:
            self.log_action('error', _(f"Error al crear pedido: {str(e)}"))
            return False
    
    def _create_delivery_document(self, data):
        """Crea un albarán borrador basado en los datos extraídos"""
        # Verificar datos mínimos
        if not data.get('partner_id'):
            self.log_action('warning', _('No se identificó proveedor para el albarán'))
            return False
            
        # Buscar pedido relacionado si tenemos referencia
        purchase_order = None
        if data.get('order_id'):
            purchase_order = self.env['purchase.order'].browse(data['order_id']).exists()
        elif data.get('order_reference'):
            purchase_order = self.env['purchase.order'].search([
                ('name', '=ilike', data['order_reference'])
            ], limit=1)
            
        # Si no tenemos pedido relacionado, es difícil crear un albarán correctamente
        if not purchase_order:
            self.log_action('warning', _('No se encontró pedido relacionado para crear albarán'))
            
            # Vincular solo el documento
            self.write({
                'status_message': _("No se pudo crear albarán automáticamente: falta pedido relacionado")
            })
            return False
            
        # Verificar si ya existe un albarán con la misma referencia
        if data.get('delivery_number'):
            existing_picking = self.env['stock.picking'].search([
                ('origin', '=ilike', data['delivery_number']),
                ('partner_id', '=', data['partner_id'])
            ], limit=1)
            
            if existing_picking:
                self.log_action('info', _(f"Albarán ya existente: {existing_picking.name}"))
                
                # Vincular a albarán existente
                self.write({
                    'result_model': 'stock.picking',
                    'result_id': existing_picking.id,
                    'status_message': _("Documento vinculado a albarán existente")
                })
                
                # Adjuntar documento a albarán existente
                attachment_vals = {
                    'name': self.filename or self.name,
                    'datas': self.document_file,
                    'res_model': 'stock.picking',
                    'res_id': existing_picking.id,
                }
                self.env['ir.attachment'].create(attachment_vals)
                
                return True
                
        # En este caso, lo mejor es crear una actividad en el pedido relacionado
        # para que un usuario revise manualmente el albarán
        activity_vals = {
            'summary': _('Revisar albarán recibido'),
            'note': _(f"""
                Se ha procesado un documento de albarán con referencia: {data.get('delivery_number', 'Sin referencia')}
                Fecha: {data.get('date', 'No detectada')}
                
                Este documento requiere revisión manual para validar los productos recibidos.
            """),
            'res_id': purchase_order.id,
            'res_model_id': self.env['ir.model'].search([('model', '=', 'purchase.order')], limit=1).id,
            'user_id': purchase_order.user_id.id or self.env.user.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
        }
        
        activity = self.env['mail.activity'].create(activity_vals)
        
        # Vincular documento con el pedido y registrar actividad creada
        self.write({
            'result_model': 'purchase.order',
            'result_id': purchase_order.id,
            'status_message': _("Documento procesado. Creada tarea de revisión manual en pedido relacionado.")
        })
        
        # Adjuntar documento al pedido
        attachment_vals = {
            'name': self.filename or self.name,
            'datas': self.document_file,
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
        }
        self.env['ir.attachment'].create(attachment_vals)
        
        self.log_action('create', _(f"Creada actividad {activity.id} en pedido {purchase_order.name}"))
        
        return True
    
    # Métodos de workflow
    def action_process(self):
        """Procesa el documento manualmente"""
        self.ensure_one()
        return self.with_context(document_processing=True).process_document()
    
    def action_reset(self):
        """Reinicia el documento al estado borrador para reprocesarlo"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'ocr_text': False,
            'extracted_data': False,
            'document_type_id': False,
            'detected_type_ids': [(5, 0, 0)],
            'processed_date': False,
            'validated_date': False,
            'result_model': False,
            'result_id': False,
            'status_message': _("Documento reiniciado para reprocesamiento")
        })
        self.log_action('reset', _('Documento reiniciado para reprocesamiento'))
        return True
    
    def action_validate(self):
        """Valida el documento después de revisión manual"""
        self.ensure_one()
        
        if self.state not in ['to_validate', 'error']:
            raise UserError(_("Solo documentos en estado 'Por validar' o 'Error' pueden ser validados manualmente."))
            
        if self.result_model and self.result_id:
            # Ya tiene documento vinculado, solo cambiar estado
            self.write({
                'state': 'validated',
                'validated_date': fields.Datetime.now(),
                'status_message': _("Documento validado manualmente")
            })
            self.log_action('validate', _('Documento validado manualmente'))
            
            # Notificar al usuario responsable
            if self.user_id and self.user_id != self.env.user:
                self.message_post(
                    body=_("Documento validado por %s") % self.env.user.name,
                    partner_ids=[(4, self.user_id.partner_id.id)]
                )
        else:
            return {
                'name': _('Validar Documento'),
                'type': 'ir.actions.act_window',
                'res_model': 'document.validate.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_document_id': self.id}
            }
    
    def action_cancel(self):
        """Cancela el documento"""
        self.ensure_one()
        
        if self.state in ['validated', 'linked']:
            raise UserError(_("No se puede cancelar un documento ya validado o vinculado."))
            
        self.write({
            'state': 'cancelled',
            'status_message': _("Documento cancelado manualmente")
        })
        self.log_action('cancel', _('Documento cancelado manualmente'))
        return True
    
    def action_view_result(self):
        """Muestra el documento resultante"""
        self.ensure_one()
        
        if not self.result_model or not self.result_id:
            raise UserError(_("Este documento no tiene ningún registro vinculado."))
            
        # Verificar que el registro existe
        record = self.env[self.result_model].browse(self.result_id).exists()
        if not record:
            raise UserError(_("El registro vinculado ya no existe."))
            
        # Devolver acción para ver el registro
        return {
            'name': record.display_name,
            'type': 'ir.actions.act_window',
            'res_model': self.result_model,
            'res_id': self.result_id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_errors(self):
        """Muestra los errores del documento"""
        self.ensure_one()
        
        return {
            'name': _('Errores de Procesamiento'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.automation.log',
            'view_mode': 'tree,form',
            'domain': [('document_id', '=', self.id), ('level', '=', 'error')],
            'target': 'current',
        }
    
    # Métodos utilitarios
    def log_action(self, action, message, level='info'):
    # Lista de acciones válidas
        valid_actions = ['create', 'write', 'process', 'validate', 'link', 'error', 'cancel', 'ocr', 
                     'extract', 'classify', 'notify', 'duplicate', 'merge', 'export', 'import', 'other']

    # Si la acción no es válida, usamos 'other'
        if action not in valid_actions:
            _logger.warning(f"Acción no válida: {action}. Se usará 'other'.")
            action = 'other'

        log_vals = {
            'document_id': self.id,
            'action': action,
            'message': f"{action}: {message}",
            'level': level
        }
        return self.env['document.automation.log'].create(log_vals)
    
    def notify_users(self, message, user_ids=None):
        """Notifica a usuarios específicos sobre el documento"""
        self.ensure_one()
        
        if not user_ids:
            # Notificar al responsable y posiblemente a otros usuarios configurados
            user_ids = [self.user_id.id] if self.user_id else []
            
            # Añadir usuarios configurados para recibir notificaciones de este tipo
            doc_type = self.document_type_id
            if doc_type and doc_type.notify_user_ids:
                user_ids.extend(doc_type.notify_user_ids.ids)
                
        if not user_ids:
            return False
            
        # Obtener partner_ids de los usuarios
        partners = self.env['res.users'].browse(user_ids).mapped('partner_id')
        
        if partners:
            self.message_post(
                body=message,
                partner_ids=partners.ids,
                subject=_("Notificación de documento: %s") % self.name
            )
            return True
            
        return False
    
    @api.model
    def run_document_processing_cron(self):
        """Método para el cron de procesamiento automático"""
        # Buscar documentos pendientes
        documents = self.search([
            ('state', 'in', ['draft', 'error']),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=7))  # Últimos 7 días
        ], limit=50)
        
        processed = 0
        for doc in documents:
            try:
                result = doc.with_context(document_cron=True).process_document()
                if result:
                    processed += 1
            except Exception as e:
                _logger.error("Error al procesar documento %s: %s", doc.name, str(e))
                
        _logger.info("Procesamiento automático completado: %d/%d documentos procesados", 
                     processed, len(documents))
                     
        return True
    
    @api.model
    def check_email_documents(self):
        """Método para el cron de comprobación de documentos por correo"""
        # Verificar si la función está habilitada
        param = self.env['ir.config_parameter'].sudo().get_param(
            'document_automation.scan_email_enabled', 'False'
        )
        
        if param != 'True':
            return False
            
        # Este método podría implementar una lógica para conectarse a IMAP
        # Aquí habría que implementar la lógica específica para tu caso
        # ...
        
        return True

class DocumentAutomationLog(models.Model):
    _name = 'document.automation.log'
    _description = 'Registro de actividad de documento'
    _order = 'create_date desc'

    document_id = fields.Many2one('document.automation', 'Documento', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', 'Usuario', default=lambda self: self.env.user)
    
    # Modificar esta línea para incluir 'write' y 'ocr'
    action = fields.Selection([
        ('create', 'Creación'),
        ('write', 'Modificación'),
        ('process', 'Procesamiento'),
        ('validate', 'Validación'),
        ('link', 'Vinculación'),
        ('error', 'Error'),
        ('cancel', 'Cancelación'),
        ('ocr', 'Reconocimiento de texto'),
        ('extract', 'Extracción de datos'),
        ('classify', 'Clasificación'),
        ('notify', 'Notificación'),
        ('duplicate', 'Duplicado detectado'),
        ('merge', 'Fusión'),
        ('export', 'Exportación'),
        ('import', 'Importación'),
        ('other', 'Otra acción')  # Opción genérica para casos no previstos
    ], string='Acción', required=True)    

    level = fields.Selection([
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('error', 'Error')
    ], string='Nivel', default='info')
    
    message = fields.Text('Mensaje')
    
    def name_get(self):
        return [(record.id, f"{record.create_date} - {record.action}") for record in self]
