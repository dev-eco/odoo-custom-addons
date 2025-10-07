import base64
import json
import logging
import re
import tempfile
import os
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

class DocumentScan(models.Model):
    _name = 'document.scan'
    _description = 'Documento Escaneado'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(
        string='Nombre',
        required=True,
        tracking=True
    )
    
    document_type_code = fields.Char(
        string='Tipo de Documento',
        tracking=True,
        help='Código del tipo de documento'
    )
    
    document_type_id = fields.Many2one(
        'document.type',
        string='Tipo de Documento',
        compute='_compute_document_type',
        store=True,
        tracking=True
    )
    
    @api.depends('document_type_code')
    def _compute_document_type(self):
        """Calcula el tipo de documento basado en el código"""
        for record in self:
            if record.document_type_code:
                doc_type = self.env['document.type'].search([
                    ('code', '=', record.document_type_code),
                    ('active', '=', True)
                ], limit=1)
                
                record.document_type_id = doc_type.id if doc_type else False
            else:
                record.document_type_id = False
    
    source = fields.Selection([
        ('email', 'Email'),
        ('scanner', 'Escáner'),
        ('upload', 'Subida Manual'),
        ('api', 'API'),
    ], string='Origen', default='scanner', required=True, tracking=True)
    
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('processed', 'Procesado'),
        ('error', 'Error'),
        ('manual', 'Revisión Manual'),
    ], string='Estado', default='pending', required=True, tracking=True)
    
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Archivo Adjunto',
        ondelete='restrict',
        tracking=True
    )
    
    # Datos de clasificación y procesamiento
    confidence_score = fields.Float(
        string='Confianza OCR',
        help='Puntuación de confianza en el reconocimiento (0-100%)',
        default=0.0,
        tracking=True
    )
    
    ocr_data = fields.Text(
        string='Datos OCR',
        help='Datos extraídos del documento en formato JSON',
    )
    
    ocr_text = fields.Text(
        string='Texto Extraído',
        help='Texto completo extraído del documento',
    )
    
    metadata = fields.Text(
        string='Metadatos',
        help='Metadatos adicionales en formato JSON'
    )
    
    # Relación con documento resultado
    result_model = fields.Char(
        string='Modelo Destino',
        help='Modelo Odoo donde se ha creado el documento final',
        readonly=True
    )
    
    result_record_id = fields.Integer(
        string='ID Registro Destino',
        help='ID del registro creado en el modelo destino',
        readonly=True
    )
    
    # Campos para seguimiento y auditoría
    processed_date = fields.Datetime(
        string='Fecha Procesamiento',
        readonly=True
    )
    
    processing_time = fields.Float(
        string='Tiempo Procesamiento (s)',
        help='Tiempo en segundos que tomó procesar el documento',
        readonly=True
    )
    
    user_id = fields.Many2one(
        'res.users', 
        string='Responsable',
        default=lambda self: self.env.user.id,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        tracking=True
    )
    
    notes = fields.Text(
        string='Notas',
        tracking=True
    )
    
    log_ids = fields.One2many(
        'document.scan.log',
        'document_id',
        string='Historial'
    )
    
    # Campos computados para la interfaz
    document_preview = fields.Binary(
        string='Vista Previa',
        compute='_compute_document_preview'
    )
    
    result_url = fields.Char(
        string='URL Resultado',
        compute='_compute_result_url'
    )
    
    # Campos técnicos
    is_auto_validated = fields.Boolean(
        string='Validación Automática',
        default=False,
        readonly=True,
        help='Indica si el documento fue validado automáticamente'
    )
    
    has_error = fields.Boolean(
        string='Tiene Error',
        compute='_compute_has_error',
        store=True
    )
    
    @api.depends('status')
    def _compute_has_error(self):
        for record in self:
            record.has_error = record.status == 'error'
    
    @api.model
    def create(self, vals):
        """Añade secuencia al crear un nuevo documento"""
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('document.scan') or _('Nuevo Documento')
            
        # Crear el registro
        record = super(DocumentScan, self).create(vals)
        
        # Añadir entrada en el log
        self.env['document.scan.log'].create({
            'document_id': record.id,
            'user_id': self.env.user.id,
            'action': 'create',
            'description': _('Documento creado')
        })
        
        return record
    
    def write(self, vals):
        """Sobrescribe el método write para registrar cambios importantes"""
        # Registrar cambio de estado
        if 'status' in vals:
            old_status = {rec.id: rec.status for rec in self}
            for record in self:
                self.env['document.scan.log'].create({
                    'document_id': record.id,
                    'user_id': self.env.user.id,
                    'action': 'status_change',
                    'description': _('Estado cambiado: %s → %s') % (
                        dict(self._fields['status'].selection).get(old_status[record.id]),
                        dict(self._fields['status'].selection).get(vals['status'])
                    )
                })
        
        return super(DocumentScan, self).write(vals)
    
    def _compute_document_preview(self):
        """Genera una vista previa del documento"""
        for record in self:
            if record.attachment_id:
                record.document_preview = record.attachment_id.datas
            else:
                record.document_preview = False
    
    def _compute_result_url(self):
        """Genera la URL para acceder al documento resultante"""
        for record in self:
            if record.result_model and record.result_record_id:
                action = self.env['ir.model.data'].search([
                    ('model', '=', 'ir.actions.act_window'),
                    ('res_id.res_model', '=', record.result_model)
                ], limit=1)
                
                if action:
                    record.result_url = '/web#id=%s&model=%s&view_type=form&action=%s' % (
                        record.result_record_id, record.result_model, action.res_id
                    )
                else:
                    record.result_url = '/web#id=%s&model=%s&view_type=form' % (
                        record.result_record_id, record.result_model
                    )
            else:
                record.result_url = False
    
    def action_process(self):
        """Inicia el procesamiento del documento"""
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError(_("No hay archivo adjunto para procesar"))
        
        # Comprobar si es un PDF
        if not self.attachment_id.mimetype == 'application/pdf':
            raise UserError(_("Solo se pueden procesar archivos PDF"))
        
        # Actualizar estado
        self.write({
            'status': 'processing',
        })
        
        # Registrar inicio del procesamiento
        start_time = datetime.now()
        
        try:
            # 1. Extraer texto con OCR si está disponible account_invoice_extract
            if self.env.user.has_group('account.group_account_invoice') and hasattr(self.env, 'account.invoice.extract.words'):
                self._process_with_invoice_extract()
            else:
                self._process_with_alternative_ocr()
                
            # 2. Clasificar documento si no tiene tipo
            if not self.document_type_id:
                self._classify_document()
                
            # 3. Extraer datos según el tipo de documento
            self._extract_document_data()
                
            # 4. Crear documento en modelo destino
            self._create_target_document()
            
            # Actualizar tiempo de procesamiento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Actualizar estado final
            self.write({
                'status': 'processed',
                'processed_date': fields.Datetime.now(),
                'processing_time': processing_time,
            })
            
            return True
            
        except Exception as e:
            # Registrar error
            self.env['document.scan.log'].create({
                'document_id': self.id,
                'user_id': self.env.user.id,
                'action': 'error',
                'description': _('Error: %s') % str(e)
            })
            
            # Actualizar estado
            self.write({
                'status': 'error',
                'notes': f"{self.notes or ''}\n\nError: {str(e)}",
            })
            
            _logger.error(f"Error procesando documento {self.id}: {str(e)}")
            return False
    
    def _process_with_invoice_extract(self):
        """Procesa usando el OCR nativo de Odoo"""
        self.ensure_one()
        
        # Aquí implementaríamos la integración con el módulo account_invoice_extract
        # Por ahora, usamos un método alternativo simulado
        
        # Simulamos una integración
        self._process_with_alternative_ocr()
    
    def _process_with_alternative_ocr(self):
        """Implementación alternativa de OCR"""
        self.ensure_one()
        
        try:
            # Obtener el contenido del PDF
            pdf_data = base64.b64decode(self.attachment_id.datas)
            
            # Aquí implementaríamos un OCR real
            # Por ahora simulamos una extracción
            
            # Simulamos extracción de texto
            extracted_text = "Este es un texto simulado extraído por OCR.\n"
            extracted_text += "Factura #12345\n"
            extracted_text += "Fecha: 01/01/2025\n"
            extracted_text += "Proveedor: Ejemplo, S.L.\n"
            extracted_text += "NIF: B12345678\n"
            extracted_text += "Total: 1,234.56€\n"
            
            # Simulamos datos estructurados extraídos
            ocr_data = {
                "document_type": self.document_type_code or "invoice",
                "invoice_number": "12345",
                "invoice_date": "2025-01-01",
                "partner_name": "Ejemplo, S.L.",
                "partner_vat": "B12345678",
                "total_amount": 1234.56,
                "currency_code": "EUR",
                "tax_amount": 214.56,
                "confidence": 85.5
            }
            
            # Actualizamos el documento con los datos extraídos
            self.write({
                'ocr_text': extracted_text,
                'ocr_data': json.dumps(ocr_data),
                'confidence_score': ocr_data['confidence'],
            })
            
            # Registramos la acción en el log
            self.env['document.scan.log'].create({
                'document_id': self.id,
                'user_id': self.env.user.id,
                'action': 'ocr_processing',
                'description': _('OCR procesado con puntuación de confianza: %s%%') % ocr_data['confidence']
            })
            
            return True
            
        except Exception as e:
            _logger.error(f"Error en el procesamiento OCR: {str(e)}")
            raise ValidationError(_("Error en el procesamiento OCR: %s") % str(e))
    
    def _classify_document(self):
        """Clasifica el documento basado en el contenido extraído"""
        self.ensure_one()
        
        if not self.ocr_text:
            return False
            
        # Obtener todos los tipos de documento activos
        doc_types = self.env['document.type'].search([('active', '=', True)])
        
        # Preparar sistema de puntuaciones para cada tipo
        scores = {}
        
        # Si tenemos datos OCR estructurados
        if self.ocr_data:
            try:
                ocr_data = json.loads(self.ocr_data)
                # Si el OCR ya detectó el tipo, usamos ese
                if ocr_data.get('document_type'):
                    doc_type = self.env['document.type'].search([
                        ('code', '=', ocr_data['document_type']),
                        ('active', '=', True)
                    ], limit=1)
                    
                    if doc_type:
                        self.document_type_code = doc_type.code
                        return True
            except (json.JSONDecodeError, TypeError):
                pass
                
        # Algoritmo de clasificación basado en patrones de texto
        # Aquí implementaríamos un algoritmo real de clasificación
        # Por ahora, usamos un método simple basado en palabras clave
        
        for doc_type in doc_types:
            score = 0
            
            # Palabras clave específicas para cada tipo
            keywords = {
                'invoice': ['factura', 'invoice', 'importe', 'total', 'base imponible', 'iva'],
                'credit_note': ['abono', 'credit', 'nota de crédito', 'devolución'],
                'delivery_note': ['albarán', 'entrega', 'delivery note', 'bultos', 'cantidad'],
                'purchase_order': ['pedido', 'orden de compra', 'purchase order'],
                'ticket': ['ticket', 'recibo', 'caja', 'tienda'],
            }
            
            # Verificar palabras clave
            if doc_type.code in keywords:
                for keyword in keywords[doc_type.code]:
                    if keyword.lower() in self.ocr_text.lower():
                        score += 1
            
            scores[doc_type.code] = score
        
        # Determinar el tipo con mayor puntuación
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])
            
            # Si hay una puntuación mínima (al menos 1 coincidencia)
            if best_type[1] > 0:
                self.document_type_code = best_type[0]
                
                # Registramos la clasificación en el log
                self.env['document.scan.log'].create({
                    'document_id': self.id,
                    'user_id': self.env.user.id,
                    'action': 'classification',
                    'description': _('Documento clasificado como: %s (puntuación: %s)') % (
                        self.document_type_id.name, best_type[1]
                    )
                })
                
                return True
        
        # Si no pudimos clasificarlo, usamos el tipo genérico
        self.document_type_code = 'generic'
        
        # Registramos en el log
        self.env['document.scan.log'].create({
            'document_id': self.id,
            'user_id': self.env.user.id,
            'action': 'classification',
            'description': _('No se pudo clasificar automáticamente. Asignado tipo genérico.')
        })
        
        return False
    
    def _extract_document_data(self):
        """Extrae datos específicos según el tipo de documento"""
        self.ensure_one()
        
        if not self.document_type_id or not self.ocr_data:
            return False
            
        try:
            # Obtenemos los datos extraídos por OCR
            ocr_data = json.loads(self.ocr_data)
            
            # Verificamos si hay un template específico de extracción
            template = self.document_type_id.ocr_template
            
            # Aquí implementaríamos la extracción según el template
            # Por ahora, simplemente mejoramos los datos de confianza
            
            # Actualizamos la confianza basados en los campos encontrados
            field_mappings = json.loads(self.document_type_id.field_mappings or '{}')
            
            # Contar campos encontrados
            fields_found = 0
            total_fields = len(field_mappings)
            
            for _, ocr_field in field_mappings.items():
                if ocr_field in ocr_data and ocr_data[ocr_field]:
                    fields_found += 1
            
            # Actualizar puntuación de confianza si tenemos campos
            if total_fields > 0:
                confidence = (fields_found / total_fields) * 100
                # Promediamos con la confianza original
                new_confidence = (confidence + self.confidence_score) / 2
                
                self.write({
                    'confidence_score': new_confidence
                })
            
            return True
            
        except Exception as e:
            _logger.error(f"Error en extracción de datos: {str(e)}")
            # No lanzamos excepción para no detener el proceso
            return False
    
    def _create_target_document(self):
        """Crea el documento en el modelo destino según el tipo"""
        self.ensure_one()
        
        if not self.document_type_id:
            return False
            
        try:
            # Obtenemos el modelo destino y valores por defecto
            target_model = self.document_type_id.target_model
            defaults = safe_eval(self.document_type_id.target_model_defaults or '{}')
            
            if not target_model:
                raise ValidationError(_("El tipo de documento no tiene modelo destino configurado"))
                
            # Verificamos que el modelo exista
            if not self.env.get(target_model):
                raise ValidationError(_("El modelo %s no existe en el sistema") % target_model)
                
            # Preparamos los valores para crear el registro
            values = dict(defaults)
            
            # Si tenemos datos OCR, los usamos para mapear campos
            if self.ocr_data:
                try:
                    ocr_data = json.loads(self.ocr_data)
                    field_mappings = json.loads(self.document_type_id.field_mappings or '{}')
                    
                    # Mapear campos según configuración
                    for target_field, ocr_field in field_mappings.items():
                        if ocr_field in ocr_data and ocr_data[ocr_field]:
                            # Casos especiales
                            if target_field == 'partner_id' and ocr_field == 'partner_vat':
                                # Buscar partner por VAT
                                partner = self.env['res.partner'].search([
                                    '|', ('vat', '=', ocr_data[ocr_field]),
                                    ('vat', 'ilike', ocr_data[ocr_field])
                                ], limit=1)
                                
                                if partner:
                                    values[target_field] = partner.id
                            elif target_field == 'currency_id' and ocr_field == 'currency_code':
                                # Buscar moneda por código
                                currency = self.env['res.currency'].search([
                                    ('name', '=', ocr_data[ocr_field])
                                ], limit=1)
                                
                                if currency:
                                    values[target_field] = currency.id
                            else:
                                # Mapeo directo
                                values[target_field] = ocr_data[ocr_field]
                except Exception as e:
                    _logger.error(f"Error mapeando campos: {str(e)}")
            
            # Añadir referencia al documento original
            # Algunos modelos tienen campos específicos para esto
            if target_model == 'account.move':
                values['narration'] = _("Documento procesado automáticamente: %s") % self.name
                values['ref'] = values.get('ref', '') or self.name
            
            # Crear el registro en el modelo destino
            target_record = self.env[target_model].create(values)
            
            # Vincular el adjunto original al nuevo registro
            if self.attachment_id:
                # Copiamos el adjunto para el nuevo modelo
                new_attachment = self.attachment_id.copy({
                    'res_model': target_model,
                    'res_id': target_record.id,
                    'res_field': False,
                })
            
            # Actualizar referencia al documento creado
            self.write({
                'result_model': target_model,
                'result_record_id': target_record.id,
            })
            
            # Registramos la creación en el log
            self.env['document.scan.log'].create({
                'document_id': self.id,
                'user_id': self.env.user.id,
                'action': 'create_target',
                'description': _('Documento creado en %s: %s (ID: %s)') % (
                    target_model, target_record.display_name, target_record.id
                )
            })
            
            # Verificar si se debe validar automáticamente
            self._auto_validate_document(target_record)
            
            return True
            
        except Exception as e:
            _logger.error(f"Error creando documento destino: {str(e)}")
            raise ValidationError(_("Error creando documento en sistema: %s") % str(e))
    
    def _auto_validate_document(self, target_record):
        """Valida automáticamente el documento si cumple los criterios"""
        self.ensure_one()
        
        # Verificar configuración
        config_param = self.env['ir.config_parameter'].sudo()
        auto_validate = config_param.get_param('document_automation.auto_validate', 'false').lower() == 'true'
        
        if not auto_validate:
            return False
            
        # Verificar umbral de confianza
        threshold = float(config_param.get_param('document_automation.validation_threshold', '90.0'))
        
        if self.confidence_score < threshold:
            return False
            
        try:
            # Solo validamos facturas por ahora
            if self.document_type_id.target_model == 'account.move' and hasattr(target_record, 'action_post'):
                # Validar factura
                target_record.action_post()
                
                # Marcar como auto-validado
                self.write({
                    'is_auto_validated': True
                })
                
                # Registramos la validación en el log
                self.env['document.scan.log'].create({
                    'document_id': self.id,
                    'user_id': self.env.user.id,
                    'action': 'auto_validate',
                    'description': _('Documento validado automáticamente con confianza: %s%%') % self.confidence_score
                })
                
                return True
                
        except Exception as e:
            _logger.error(f"Error en validación automática: {str(e)}")
            # No lanzamos excepción para no interrumpir el flujo
            return False
    
    def action_reset(self):
        """Reinicia el proceso de un documento"""
        self.ensure_one()
        
        # Verificamos que no esté ya procesado y validado
        if self.status == 'processed' and self.result_model == 'account.move' and self.is_auto_validated:
            raise UserError(_("No se puede reiniciar un documento que ya ha sido validado"))
        
        # Reiniciamos el documento
        self.write({
            'status': 'pending',
            'processed_date': False,
            'processing_time': 0,
            'ocr_data': False,
            'ocr_text': False,
            'confidence_score': 0,
            'result_model': False,
            'result_record_id': False,
            'is_auto_validated': False,
        })
        
        # Registramos el reinicio en el log
        self.env['document.scan.log'].create({
            'document_id': self.id,
            'user_id': self.env.user.id,
            'action': 'reset',
            'description': _('Documento reiniciado para reprocesamiento')
        })
        
        return True
    
    def action_force_manual(self):
        """Marca un documento para revisión manual"""
        self.ensure_one()
        
        self.write({
            'status': 'manual'
        })
        
        # Registramos en el log
        self.env['document.scan.log'].create({
            'document_id': self.id,
            'user_id': self.env.user.id,
            'action': 'manual',
            'description': _('Documento marcado para revisión manual')
        })
        
        return True
    
    def action_process_batch(self):
        """Procesa un lote de documentos"""
        if not self:
            return False
            
        success_count = 0
        error_count = 0
        
        for document in self:
            try:
                if document.status in ['pending', 'error']:
                    if document.action_process():
                        success_count += 1
                    else:
                        error_count += 1
            except Exception as e:
                error_count += 1
                _logger.error(f"Error procesando documento {document.id}: {str(e)}")
        
        # Mostrar resumen
        message = _(
            "Procesamiento completado:\n"
            "- Documentos procesados correctamente: %s\n"
            "- Documentos con errores: %s"
        ) % (success_count, error_count)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Procesamiento por lotes'),
                'message': message,
                'sticky': False,
                'type': 'info' if error_count == 0 else 'warning',
            }
        }
    
    @api.model
    def _cron_process_ocr_queue(self):
        """Cron para procesar la cola de documentos pendientes"""
        # Buscamos documentos pendientes
        documents = self.search([
            ('status', '=', 'pending'),
        ], limit=10)
        
        if not documents:
            return True
            
        _logger.info(f"Cron de OCR: Procesando {len(documents)} documentos pendientes")
        
        for document in documents:
            try:
                document.action_process()
            except Exception as e:
                _logger.error(f"Error en cron OCR para documento {document.id}: {str(e)}")
        
        return True
    
    @api.model
    def _cron_check_email_documents(self):
        """Cron para verificar documentos recibidos por email"""
        # Este método sería implementado según la integración de email específica
        # Por ahora dejamos un placeholder
        _logger.info("Verificación de documentos por email ejecutada")
        return True
    
    @api.model
    def _cron_classify_documents(self):
        """Cron para clasificar documentos pendientes"""
        # Buscamos documentos sin tipo definido
        documents = self.search([
            ('document_type_code', '=', False),
            ('status', 'in', ['pending', 'processing']),
            ('ocr_text', '!=', False),
        ], limit=10)
        
        if not documents:
            return True
            
        _logger.info(f"Clasificando {len(documents)} documentos")
        
        for document in documents:
            try:
                document._classify_document()
            except Exception as e:
                _logger.error(f"Error clasificando documento {document.id}: {str(e)}")
        
        return True
    
    @api.model
    def _cron_cleanup_temp_documents(self):
        """Cron para limpiar documentos temporales"""
        # Buscamos documentos temporales antiguos (más de 30 días)
        cutoff_date = fields.Datetime.now() - timedelta(days=30)
        
        old_docs = self.search([
            ('create_date', '<', cutoff_date),
            ('status', 'in', ['error']),
        ])
        
        if old_docs:
            _logger.info(f"Limpiando {len(old_docs)} documentos temporales antiguos")
            old_docs.unlink()
        
        return True


class DocumentScanLog(models.Model):
    _name = 'document.scan.log'
    _description = 'Log de Procesamiento de Documentos'
    _order = 'create_date desc'
    
    document_id = fields.Many2one(
        'document.scan',
        string='Documento',
        required=True,
        ondelete='cascade'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        default=lambda self: self.env.user.id,
    )
    
    create_date = fields.Datetime(
        string='Fecha',
        readonly=True,
        default=fields.Datetime.now
    )
    
    action = fields.Selection([
        ('create', 'Creación'),
        ('ocr_processing', 'Procesamiento OCR'),
        ('classification', 'Clasificación'),
        ('create_target', 'Creación Documento Final'),
        ('auto_validate', 'Validación Automática'),
        ('reset', 'Reinicio'),
        ('manual', 'Revisión Manual'),
        ('status_change', 'Cambio Estado'),
        ('error', 'Error'),
    ], string='Acción', required=True)
    
    description = fields.Text(
        string='Descripción',
        required=True
    )
