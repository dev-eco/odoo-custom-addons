# -*- coding: utf-8 -*-
"""
Wizard de Exportación Masiva de Facturas

Este archivo contiene el núcleo de nuestro sistema de exportación masiva.
Es donde convergen todos los conceptos que hemos desarrollado: plantillas,
configuraciones de empresa, validaciones, y procesamiento por lotes.

Arquitectura del Wizard
=======================
El wizard implementa el patrón "Collect-Validate-Process-Present":

1. **Collect**: Recopilar criterios de filtrado y opciones del usuario
2. **Validate**: Validar que los criterios sean coherentes y factibles
3. **Process**: Ejecutar la exportación con manejo robusto de errores
4. **Present**: Mostrar resultados y proporcionar descarga

Este patrón es común en software empresarial porque proporciona una
experiencia predecible y confiable para operaciones complejas.

Conceptos Avanzados de Odoo Aplicados
====================================
En este wizard aplicamos muchos conceptos avanzados de Odoo:

- **TransientModel**: Para datos temporales auto-limpiables
- **Computed Fields**: Para información derivada en tiempo real
- **Constrains**: Para validaciones automáticas de integridad
- **Batch Processing**: Para manejar grandes volúmenes eficientemente
- **Context Management**: Para configuración automática
- **Error Handling**: Para operaciones robustas en producción
- **Multi-Company**: Para seguridad en entornos empresariales

Cada uno de estos conceptos se explicará en detalle donde se aplique.
"""

import io
import base64
import zipfile
import tarfile
import tempfile
import os
import re
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config
import logging

_logger = logging.getLogger(__name__)

# Importar py7zr de forma opcional para evitar dependencias rígidas
# Este patrón permite que el módulo funcione aunque py7zr no esté instalado
try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False
    _logger.warning("py7zr no disponible. La compresión 7-Zip no estará disponible.")


class BatchExportWizard(models.TransientModel):
    """
    Wizard Principal para Exportación Masiva de Facturas
    
    Este wizard guía al usuario a través del proceso completo de exportación
    masiva, desde la selección de criterios hasta la descarga del archivo final.
    
    Como TransientModel, los registros de este wizard se eliminan automáticamente
    después de un tiempo, evitando acumulación de datos temporales en la BD.
    """
    
    # DEFINICIÓN DEL MODELO TRANSITORIO
    # =================================
    _name = 'batch.export.wizard'
    _description = 'Asistente de Exportación Masiva de Facturas'
    _check_company_auto = True  # Seguridad automática multi-empresa
    
    # CAMPOS DE CONFIGURACIÓN PRINCIPAL
    # =================================
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        help='Empresa para la cual se realizará la exportación'
    )
    
    export_template_id = fields.Many2one(
        'export.template',
        string='Plantilla de Nomenclatura',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        help='Plantilla para generar nombres de archivo. '
             'Si no se selecciona, se usará el patrón por defecto de la empresa.'
    )
    
    # CAMPOS DE SELECCIÓN DE FACTURAS
    # ===============================
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Preseleccionadas',
        help='Facturas específicas seleccionadas desde la vista de lista. '
             'Si está vacío, se aplicarán los filtros configurados abajo.'
    )
    
    # FILTROS DE TIPO DE DOCUMENTO
    # ============================
    include_customer_invoices = fields.Boolean(
        string='Facturas de Cliente',
        default=True,
        help='Incluir facturas de venta (out_invoice) en la exportación'
    )
    
    include_vendor_bills = fields.Boolean(
        string='Facturas de Proveedor',
        default=True,
        help='Incluir facturas de compra (in_invoice) en la exportación'
    )
    
    include_credit_notes = fields.Boolean(
        string='Notas de Crédito',
        default=False,
        help='Incluir notas de crédito de cliente y proveedor en la exportación'
    )
    
    # FILTROS DE FECHA
    # ===============
    date_from = fields.Date(
        string='Fecha Desde',
        help='Filtrar facturas con fecha igual o posterior a esta fecha'
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        help='Filtrar facturas con fecha igual o anterior a esta fecha'
    )
    
    # FILTROS DE ESTADO
    # ================
    state_filter = fields.Selection([
        ('draft', 'Solo Borradores'),
        ('posted', 'Solo Confirmadas'),
        ('all', 'Todos los Estados')
    ], string='Filtro de Estado',
       default='posted',
       help='Filtrar facturas según su estado de confirmación')
    
    # OPCIONES DE COMPRESIÓN
    # =====================
    compression_format = fields.Selection(
        selection='_get_available_compression_formats',
        string='Formato de Compresión',
        default='zip_best',
        required=True,
        help='Algoritmo de compresión a utilizar. Cada formato tiene diferentes '
             'características de velocidad vs tamaño de archivo final.'
    )
    
    # OPCIONES DE PROCESAMIENTO
    # ========================
    batch_size = fields.Integer(
        string='Tamaño de Lote',
        default=100,
        help='Número de facturas a procesar en cada lote. '
             'Valores más altos son más rápidos pero usan más memoria.'
    )
    
    # CAMPOS DE RESULTADO
    # ==================
    export_file = fields.Binary(
        string='Archivo de Exportación',
        readonly=True,
        help='Archivo comprimido generado con todas las facturas'
    )
    
    export_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
        help='Nombre sugerido para el archivo de descarga'
    )
    
    # MÉTRICAS Y ESTADÍSTICAS
    # ======================
    export_count = fields.Integer(
        string='Facturas Exportadas',
        readonly=True,
        help='Número total de facturas incluidas en el archivo'
    )
    
    failed_count = fields.Integer(
        string='Facturas con Error',
        readonly=True,
        help='Número de facturas que no pudieron ser exportadas'
    )
    
    compression_ratio = fields.Float(
        string='Ratio de Compresión',
        readonly=True,
        help='Porcentaje de reducción de tamaño logrado con la compresión'
    )
    
    processing_time = fields.Float(
        string='Tiempo de Procesamiento',
        readonly=True,
        help='Tiempo total empleado en la exportación (en segundos)'
    )
    
    # CAMPO COMPUTED PARA VISTA PREVIA
    # ================================
    estimated_invoice_count = fields.Integer(
        string='Facturas Estimadas',
        compute='_compute_estimated_invoice_count',
        help='Estimación de cuántas facturas se exportarán con los filtros actuales'
    )
    
    # MÉTODOS PARA OPCIONES DINÁMICAS
    # ===============================
    @api.model
    def _get_available_compression_formats(self):
        """
        Obtener formatos de compresión disponibles según dependencias instaladas.
        
        Este método dinámico permite mostrar solo las opciones que realmente
        funcionarán en el servidor actual, evitando confusión al usuario.
        
        ¿Por qué hacer esto dinámico?
        Diferente servidores pueden tener diferentes bibliotecas instaladas.
        En lugar de mostrar opciones que fallarán, adaptamos la interfaz
        a las capacidades reales del sistema.
        """
        formats = [
            ('zip', _('ZIP Estándar (Rápido, compresión moderada)')),
            ('zip_best', _('ZIP Óptimo (Lento, mejor compresión)')),
            ('tar_gz', _('TAR.GZ (Estándar Unix, buena compresión)')),
        ]
        
        # Añadir 7-Zip solo si la biblioteca está disponible
        if HAS_PY7ZR:
            formats.append((
                '7z', _('7-Zip (Muy lento, compresión máxima)')
            ))
        
        return formats
    
    # CAMPOS COMPUTED
    # ==============
    @api.depends('invoice_ids', 'include_customer_invoices', 'include_vendor_bills', 
                 'include_credit_notes', 'date_from', 'date_to', 'state_filter', 'company_id')
    def _compute_estimated_invoice_count(self):
        """
        Calcular estimación de facturas que se exportarán.
        
        Este campo computed proporciona feedback inmediato al usuario sobre
        cuántas facturas se procesarán, ayudándole a validar sus filtros
        antes de ejecutar la exportación.
        
        ¿Por qué usar @api.depends?
        El decorador @api.depends le dice a Odoo que recalcule este campo
        automáticamente cuando cambien los campos especificados. Esto
        proporciona una experiencia interactiva sin necesidad de botones
        adicionales o recargas de página.
        """
        for wizard in self:
            if wizard.invoice_ids:
                # Si hay facturas preseleccionadas, usar esa cantidad
                wizard.estimated_invoice_count = len(wizard.invoice_ids)
            else:
                # Calcular según los filtros configurados
                domain = wizard._build_invoice_domain()
                count = self.env['account.move'].search_count(domain)
                wizard.estimated_invoice_count = count
    
    # VALIDACIONES Y CONSTRAINS
    # =========================
    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        """
        Validar coherencia del rango de fechas.
        
        Esta validación se ejecuta automáticamente cuando el usuario
        modifica las fechas, proporcionando feedback inmediato.
        """
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                if wizard.date_from > wizard.date_to:
                    raise ValidationError(_(
                        'La fecha inicial (%s) no puede ser posterior '
                        'a la fecha final (%s).'
                    ) % (wizard.date_from, wizard.date_to))
    
    @api.constrains('batch_size')
    def _check_batch_size(self):
        """
        Validar que el tamaño de lote esté en rango aceptable.
        
        Esta validación previene configuraciones que podrían causar
        problemas de rendimiento o agotamiento de memoria.
        """
        for wizard in self:
            if wizard.batch_size < 1:
                raise ValidationError(_('El tamaño de lote debe ser al menos 1.'))
            
            if wizard.batch_size > 1000:
                raise ValidationError(_(
                    'El tamaño de lote no puede exceder 1000 facturas para '
                    'evitar problemas de memoria en el servidor.'
                ))
    
    @api.constrains('include_customer_invoices', 'include_vendor_bills', 'include_credit_notes')
    def _check_document_types(self):
        """
        Validar que al menos un tipo de documento esté seleccionado.
        
        Sin esta validación, el usuario podría deseleccionar todos los tipos
        y obtener una exportación vacía, lo cual sería confuso.
        """
        for wizard in self:
            if not any([
                wizard.include_customer_invoices,
                wizard.include_vendor_bills,
                wizard.include_credit_notes
            ]):
                raise ValidationError(_(
                    'Debe seleccionar al menos un tipo de documento para exportar.'
                ))
    
    # MÉTODOS AUXILIARES PRIVADOS
    # ===========================
    def _build_invoice_domain(self):
        """
        Construir domain de Odoo para filtrar facturas según criterios.
        
        Este método centraliza la lógica de filtrado, construyendo
        dinámicamente un domain que refleje exactamente los criterios
        configurados por el usuario.
        
        Returns:
            list: Domain de Odoo listo para usar en search()
        """
        domain = []
        
        # Si hay facturas preseleccionadas, usar solo esas
        if self.invoice_ids:
            domain.append(('id', 'in', self.invoice_ids.ids))
            # Si hay preselección, ignorar otros filtros para evitar confusión
            return domain
        
        # Filtro por empresa (seguridad multi-empresa)
        domain.append(('company_id', '=', self.company_id.id))
        
        # Construir filtro de tipos de documento
        move_types = []
        if self.include_customer_invoices:
            move_types.append('out_invoice')
        if self.include_vendor_bills:
            move_types.append('in_invoice')
        if self.include_credit_notes:
            move_types.extend(['out_refund', 'in_refund'])
        
        if move_types:
            domain.append(('move_type', 'in', move_types))
        
        # Filtros de fecha
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        
        # Filtro de estado
        if self.state_filter == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.state_filter == 'posted':
            domain.append(('state', '=', 'posted'))
        # Si es 'all', no añadir filtro de estado
        
        return domain
    
    def _sanitize_filename(self, name):
        """
        Limpiar string para uso seguro como nombre de archivo.
        
        Esta función es crítica para la seguridad porque previene
        ataques de path traversal y problemas de compatibilidad
        entre diferentes sistemas operativos.
        """
        if not name:
            return _('sin_nombre')
        
        # Eliminar o reemplazar caracteres problemáticos
        name = re.sub(r'[/\\:*?"<>|]', '_', name)
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_')
        
        # Limitar longitud para evitar problemas del sistema de archivos
        if len(name) > 50:
            name = name[:50]
        
        return name or _('sin_nombre')
    
    def _get_document_type_label(self, invoice):
        """
        Obtener etiqueta descriptiva para el tipo de documento.
        
        Esta función traduce los tipos internos de Odoo a nombres
        que serán comprensibles en los archivos exportados.
        """
        type_mapping = {
            'out_invoice': _('CLIENTE'),
            'out_refund': _('NC_CLIENTE'),
            'in_invoice': _('PROVEEDOR'), 
            'in_refund': _('NC_PROVEEDOR'),
        }
        return type_mapping.get(invoice.move_type, _('DOCUMENTO'))
    
    def _generate_filename_for_invoice(self, invoice):
        """
        Generar nombre de archivo para una factura específica.
        
        Este método decide si usar una plantilla específica, el patrón
        personalizado de la empresa, o el formato por defecto del sistema.
        
        La jerarquía de decisión es:
        1. Plantilla seleccionada en el wizard
        2. Patrón personalizado de la empresa (si está activado)
        3. Formato por defecto del sistema
        """
        # Si hay plantilla seleccionada, usarla
        if self.export_template_id:
            return self._generate_filename_from_template(invoice)
        
        # Si la empresa tiene patrón personalizado activado, usarlo
        if (self.company_id.use_custom_filename_pattern and 
            self.company_id.custom_filename_pattern):
            return self._generate_filename_from_pattern(
                invoice, self.company_id.custom_filename_pattern
            )
        
        # Usar formato por defecto
        return self._generate_default_filename(invoice)
    
    def _generate_filename_from_template(self, invoice):
        """
        Generar nombre usando la plantilla seleccionada.
        """
        pattern = self.export_template_id.filename_pattern
        return self._generate_filename_from_pattern(invoice, pattern)
    
    def _generate_filename_from_pattern(self, invoice, pattern):
        """
        Generar nombre usando un patrón específico.
        
        Este método centraliza la lógica de generación de nombres,
        permitiendo reutilización desde diferentes contextos.
        """
        variables = {
            'company_code': self.company_id.code or 'COMP',
            'doc_type': self._get_document_type_label(invoice),
            'number': self._sanitize_filename(invoice.name or _('SIN_NUMERO')),
            'partner': self._sanitize_filename(
                invoice.partner_id.name or _('SIN_PARTNER')
            ),
            'date': (invoice.invoice_date or fields.Date.today()).strftime('%Y%m%d'),
            'year': (invoice.invoice_date or fields.Date.today()).strftime('%Y'),
            'month': (invoice.invoice_date or fields.Date.today()).strftime('%m'),
            'currency': invoice.currency_id.name or 'EUR',
            'amount': str(int(invoice.amount_total)),
        }
        
        try:
            filename = pattern.format(**variables)
            return f"{filename}.pdf"
        except (KeyError, ValueError) as e:
            _logger.warning(_(
                'Error en patrón de nomenclatura para factura %s: %s. '
                'Usando formato por defecto.'
            ) % (invoice.name, str(e)))
            return self._generate_default_filename(invoice)
    
    def _generate_default_filename(self, invoice):
        """
        Generar nombre con formato por defecto del sistema.
        
        Este es el formato de respaldo que siempre funciona,
        independientemente de configuraciones o plantillas.
        """
        doc_type = self._get_document_type_label(invoice)
        number = self._sanitize_filename(invoice.name or _('SIN_NUMERO'))
        partner = self._sanitize_filename(invoice.partner_id.name or _('SIN_PARTNER'))
        date_str = (invoice.invoice_date or fields.Date.today()).strftime('%Y%m%d')
        
        return f"{doc_type}_{number}_{partner}_{date_str}.pdf"
    
    def _get_invoice_pdf_content(self, invoice):
        """
        Obtener contenido PDF de una factura con estrategia de caché.
        
        Este método implementa una estrategia inteligente:
        1. Buscar PDF ya generado en adjuntos (rápido)
        2. Generar nuevo PDF si no existe (más lento)
        
        ¿Por qué esta estrategia?
        Generar PDFs es una operación costosa. Si ya existe un PDF
        para la factura, es mucho más eficiente reutilizarlo que
        regenerarlo desde cero.
        """
        # Buscar PDF existente en adjuntos
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1, order='create_date desc')
        
        if attachment and attachment.datas:
            try:
                return base64.b64decode(attachment.datas)
            except Exception as e:
                _logger.warning(_(
                    'Error decodificando PDF adjunto para factura %s: %s. '
                    'Generando nuevo PDF.'
                ) % (invoice.name, str(e)))
        
        # Generar PDF nuevo usando el motor de reportes de Odoo
        try:
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                'account.account_invoices',  # ID del reporte de facturas
                invoice.ids
            )
            return pdf_content
        except Exception as e:
            _logger.error(_(
                'Error generando PDF para factura %s: %s'
            ) % (invoice.name, str(e)))
            raise UserError(_(
                'No se pudo generar el PDF para la factura "%s".\n'
                'Error técnico: %s\n\n'
                'Verifique que la factura esté correctamente configurada '
                'y que tenga al menos una línea de factura.'
            ) % (invoice.name, str(e)))
    
    def _get_compression_engine(self, file_path):
        """
        Factory method para crear el motor de compresión apropiado.
        
        Este patrón Factory permite añadir fácilmente nuevos formatos
        de compresión sin modificar el código principal del wizard.
        
        Args:
            file_path (str): Ruta del archivo temporal a crear
            
        Returns:
            object: Motor de compresión apropiado para usar con context manager
        """
        if self.compression_format == 'zip':
            return zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
        elif self.compression_format == 'zip_best':
            return zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
        elif self.compression_format == 'tar_gz':
            return tarfile.open(file_path, 'w:gz', compresslevel=9)
        elif self.compression_format == '7z' and HAS_PY7ZR:
            return py7zr.SevenZipFile(file_path, 'w', filters=[
                {"id": py7zr.FILTER_LZMA2, "preset": 9}
            ])
        else:
            # Fallback a ZIP estándar si hay problemas
            _logger.warning(_(
                'Formato de compresión %s no disponible. Usando ZIP estándar.'
            ) % self.compression_format)
            return zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6)
    
    def _add_file_to_archive(self, archive, filename, content):
        """
        Añadir archivo al archivo comprimido según el formato.
        
        Cada formato de compresión tiene su propia API, así que
        necesitamos adaptar la operación según el tipo de archivo.
        """
        if isinstance(archive, zipfile.ZipFile):
            archive.writestr(filename, content)
        elif isinstance(archive, tarfile.TarFile):
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(content)
            archive.addfile(tarinfo, io.BytesIO(content))
        elif HAS_PY7ZR and hasattr(archive, 'writestr'):
            archive.writestr(filename, content)
        else:
            raise UserError(_(
                'Formato de compresión no soportado: %s'
            ) % type(archive).__name__)
    
    # MÉTODO PRINCIPAL DE EXPORTACIÓN
    # ===============================
    def action_export_invoices(self):
        """
        Ejecutar el proceso completo de exportación masiva.
        
        Este método implementa el algoritmo principal de exportación,
        coordinando todos los componentes del sistema para proporcionar
        una experiencia robusta y eficiente al usuario.
        
        Fases del Proceso:
        1. Validación inicial y obtención de facturas
        2. Verificación de límites de empresa
        3. Procesamiento por lotes con manejo de errores
        4. Generación de métricas y archivo final
        5. Presentación de resultados al usuario
        """
        self.ensure_one()  # Asegurar operación en un solo registro
        start_time = datetime.now()
        
        _logger.info(_('Iniciando exportación masiva para empresa %s') % self.company_id.name)
        
        # FASE 1: VALIDACIÓN Y OBTENCIÓN DE FACTURAS
        # ==========================================
        invoices = self._get_filtered_invoices()
        
        if not invoices:
            raise UserError(_(
                'No se encontraron facturas que cumplan los criterios especificados.\n\n'
                'Sugerencias:\n'
                '• Verifique que las fechas de filtro sean correctas\n'
                '• Asegúrese de haber seleccionado al menos un tipo de documento\n'
                '• Confirme que existen facturas en el estado seleccionado'
            ))
        
        # FASE 2: VERIFICACIÓN DE LÍMITES EMPRESARIALES
        # =============================================
        max_allowed = self.company_id.max_export_invoices
        if len(invoices) > max_allowed:
            raise UserError(_(
                'La exportación excede el límite configurado para esta empresa.\n\n'
                'Facturas a exportar: %d\n'
                'Límite máximo: %d\n\n'
                'Reduzca el rango de fechas o use filtros más específicos.'
            ) % (len(invoices), max_allowed))
        
        # FASE 3: PREPARACIÓN DEL PROCESAMIENTO
        # =====================================
        total_invoices = len(invoices)
        batch_size = min(self.batch_size, 1000)  # Límite de seguridad
        
        _logger.info(_(
            'Procesando %d facturas en lotes de %d'
        ) % (total_invoices, batch_size))
        
        # Usar archivo temporal para manejar archivos grandes de forma segura
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
            temp_path = temp_file.name
        
        # Variables para métricas
        successful_exports = 0
        failed_exports = []
        original_size = 0
        
        try:
            # FASE 4: PROCESAMIENTO POR LOTES
            # ===============================
            with self._get_compression_engine(temp_path) as archive:
                
                # Procesar en lotes para optimizar memoria
                for batch_start in range(0, total_invoices, batch_size):
                    batch_end = min(batch_start + batch_size, total_invoices)
                    batch_invoices = invoices[batch_start:batch_end]
                    
                    _logger.info(_(
                        'Procesando lote %d-%d de %d facturas'
                    ) % (batch_start + 1, batch_end, total_invoices))
                    
                    # Procesar cada factura del lote
                    for invoice in batch_invoices:
                        try:
                            # Generar nombre de archivo
                            filename = self._generate_filename_for_invoice(invoice)
                            
                            # Obtener contenido PDF
                            pdf_content = self._get_invoice_pdf_content(invoice)
                            original_size += len(pdf_content)
                            
                            # Añadir al archivo comprimido
                            self._add_file_to_archive(archive, filename, pdf_content)
                            
                            successful_exports += 1
                            
                        except Exception as e:
                            error_msg = str(e)
                            failed_exports.append((invoice.name, error_msg))
                            _logger.error(_(
                                'Error procesando factura %s: %s'
                            ) % (invoice.name, error_msg))
                            continue
                    
                    # Commit intermedio para evitar timeouts en transacciones largas
                    self.env.cr.commit()
            
            # FASE 5: FINALIZACIÓN Y MÉTRICAS
            # ===============================
            
            # Verificar que al menos algunas facturas se exportaron exitosamente
            if successful_exports == 0:
                error_details = '\n'.join([
                    f'• {name}: {error}' for name, error in failed_exports[:5]
                ])
                if len(failed_exports) > 5:
                    error_details += f'\n... y {len(failed_exports) - 5} errores más'
                
                raise UserError(_(
                    'No se pudo exportar ninguna factura.\n\n'
                    'Errores encontrados:\n%s\n\n'
                    'Verifique que las facturas estén correctamente configuradas '
                    'y que tenga permisos para acceder a ellas.'
                ) % error_details)
            
            # Leer archivo comprimido final
            with open(temp_path, 'rb') as f:
                compressed_content = f.read()
                compressed_size = len(compressed_content)
            
            # Calcular métricas finales
            processing_time = (datetime.now() - start_time).total_seconds()
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            # Generar nombre de archivo final
            export_filename = self._generate_export_filename(
                successful_exports, compression_ratio
            )
            
            # FASE 6: ACTUALIZACIÓN DEL WIZARD CON RESULTADOS
            # ===============================================
            self.write({
                'export_file': base64.b64encode(compressed_content),
                'export_filename': export_filename,
                'export_count': successful_exports,
                'failed_count': len(failed_exports),
                'compression_ratio': compression_ratio,
                'processing_time': processing_time,
            })
            
            # Logging final
            _logger.info(_(
                'Exportación completada: %d éxitos, %d errores, %.1f%% compresión, %.2fs'
            ) % (successful_exports, len(failed_exports), compression_ratio, processing_time))
            
        finally:
            # LIMPIEZA: Eliminar archivo temporal
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    _logger.warning(_(
                        'No se pudo eliminar archivo temporal %s: %s'
                    ) % (temp_path, str(e)))
        
        # FASE 7: MANEJO DE RESULTADOS PARCIALES
        # =====================================
        if failed_exports:
            # Si hubo errores parciales, mostrar notificación específica
            return self._show_partial_success_notification(
                successful_exports, total_invoices, failed_exports
            )
        
        # FASE 8: RETORNO DE VISTA DE ÉXITO
        # =================================
        return {
            'type': 'ir.actions.act_window',
            'name': _('Exportación Completada'),
            'res_model': 'batch.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': dict(self.env.context, export_completed=True),
        }
    
    # MÉTODOS AUXILIARES PARA LA EXPORTACIÓN
    # ======================================
    def _get_filtered_invoices(self):
        """
        Obtener facturas filtradas según criterios del wizard.
        
        Este método aplica todas las validaciones necesarias y
        construye el recordset final de facturas a procesar.
        """
        domain = self._build_invoice_domain()
        
        # Verificar permisos de la empresa si no hay facturas preseleccionadas
        if not self.invoice_ids:
            # Añadir verificación de que el usuario puede acceder a esta empresa
            if self.company_id not in self.env.companies:
                raise UserError(_(
                    'No tiene permisos para exportar facturas de la empresa "%s".'
                ) % self.company_id.name)
        
        # Buscar facturas
        invoices = self.env['account.move'].search(domain)
        
        # Verificar permisos de borrador si aplica
        if not self.company_id.allow_draft_export:
            draft_invoices = invoices.filtered(lambda inv: inv.state == 'draft')
            if draft_invoices:
                raise UserError(_(
                    'La empresa "%s" no permite exportar facturas en borrador.\n\n'
                    'Facturas en borrador encontradas: %d\n\n'
                    'Configure la empresa para permitir exportar borradores '
                    'o cambie el filtro de estado a "Solo Confirmadas".'
                ) % (self.company_id.name, len(draft_invoices)))
        
        return invoices
    
    def _generate_export_filename(self, invoice_count, compression_ratio):
        """
        Generar nombre descriptivo para el archivo de exportación final.
        
        El nombre incluye información útil para identificar el contenido
        y las características del archivo exportado.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        company_code = self.company_id.code or 'COMP'
        
        # Determinar extensión según formato
        format_extensions = {
            'zip': 'zip',
            'zip_best': 'zip', 
            'tar_gz': 'tar.gz',
            '7z': '7z'
        }
        extension = format_extensions.get(self.compression_format, 'zip')
        
        # Incluir información de compresión si es significativa
        compression_info = ''
        if compression_ratio > 10:  # Solo mostrar si la compresión es notable
            compression_info = f'_{int(compression_ratio)}pct'
        
        return _(
            'facturas_{company}_{timestamp}_{count}docs{compression}.{ext}'
        ).format(
            company=company_code,
            timestamp=timestamp,
            count=invoice_count,
            compression=compression_info,
            ext=extension
        )
    
    def _show_partial_success_notification(self, successful, total, failed_exports):
        """
        Mostrar notificación específica para éxitos parciales.
        
        Cuando algunas facturas fallan pero otras se exportan exitosamente,
        es importante comunicar claramente qué pasó y qué opciones tiene
        el usuario para proceder.
        """
        # Preparar lista de errores (máximo 5 para no saturar la interfaz)
        error_list = []
        for i, (invoice_name, error) in enumerate(failed_exports[:5]):
            error_list.append(f'• {invoice_name}: {error}')
        
        if len(failed_exports) > 5:
            error_list.append(f'... y {len(failed_exports) - 5} errores adicionales')
        
        error_details = '\n'.join(error_list)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exportación Parcialmente Exitosa'),
                'message': _(
                    'Se exportaron {successful} de {total} facturas.\n\n'
                    'Facturas con errores:\n{errors}\n\n'
                    'El archivo descargable contiene las facturas que '
                    'se exportaron exitosamente.'
                ).format(
                    successful=successful,
                    total=total, 
                    errors=error_details
                ),
                'type': 'warning',
                'sticky': True,
            }
        }
    
    # MÉTODO DE INICIALIZACIÓN AUTOMÁTICA
    # ===================================
    @api.model
    def default_get(self, fields_list):
        """
        Configuración automática del wizard al abrirlo.
        
        Este método se ejecuta automáticamente cuando se abre el wizard,
        configurándolo inteligentemente basado en el contexto desde el
        cual fue invocado.
        
        Configuración Automática Incluye:
        1. Facturas preseleccionadas desde la vista de lista
        2. Empresa apropiada basada en las facturas seleccionadas
        3. Plantilla por defecto de la empresa
        4. Configuraciones predeterminadas de la empresa
        """
        res = super().default_get(fields_list)
        
        # Obtener facturas seleccionadas del contexto
        active_ids = self.env.context.get('active_ids', [])
        
        if active_ids and 'invoice_ids' in fields_list:
            # Filtrar solo facturas válidas y accesibles
            invoices = self.env['account.move'].browse(active_ids)
            valid_invoices = invoices.filtered(
                lambda inv: inv.move_type in [
                    'out_invoice', 'out_refund', 'in_invoice', 'in_refund'
                ] and inv.company_id in self.env.companies
            )
            
            if valid_invoices:
                res['invoice_ids'] = [(6, 0, valid_invoices.ids)]
                
                # Usar empresa de la primera factura
                company = valid_invoices[0].company_id
                res['company_id'] = company.id
                
                # Aplicar configuraciones predeterminadas de la empresa
                defaults = company.get_export_defaults()
                for field, value in defaults.items():
                    if field in fields_list and value is not None:
                        res[field] = value
                
                # Buscar plantilla por defecto
                if 'export_template_id' in fields_list and defaults['default_template_id']:
                    res['export_template_id'] = defaults['default_template_id']
                
                _logger.info(_(
                    'Wizard inicializado con %d facturas de %s'
                ) % (len(valid_invoices), company.name))
        
        # Si no hay facturas preseleccionadas, usar configuraciones de empresa actual
        elif 'company_id' in fields_list:
            company = self.env.company
            res['company_id'] = company.id
            
            # Aplicar configuraciones predeterminadas
            defaults = company.get_export_defaults()
            for field, value in defaults.items():
                if field in fields_list and value is not None:
                    res[field] = value
        
        return res


"""
ARQUITECTURA Y PATRONES AVANZADOS EXPLICADOS
============================================

Patrón Collect-Validate-Process-Present
--------------------------------------
Este wizard implementa un patrón muy común en software empresarial:

1. **Collect**: Recopilar información del usuario (campos del wizard)
2. **Validate**: Validar consistencia y factibilidad (constrains)
3. **Process**: Ejecutar la operación compleja (action_export_invoices)
4. **Present**: Mostrar resultados y opciones (vista de resultado)

Cada fase tiene responsabilidades claras y puede evolucionar independientemente.

Manejo Robusto de Errores
-------------------------
El wizard implementa una estrategia de manejo de errores en capas:

**Nivel 1 - Validación Preventiva**: Constrains que previenen configuraciones inválidas
**Nivel 2 - Validación de Negocio**: Verificaciones antes de procesamiento
**Nivel 3 - Manejo de Errores de Ejecución**: Try/catch en operaciones críticas
**Nivel 4 - Recuperación Parcial**: Continuar procesando cuando algunas facturas fallan

Esta estrategia proporciona la mejor experiencia posible: previene errores
cuando es posible, pero maneja graciosamente errores inesperados.

Procesamiento por Lotes (Batch Processing)
------------------------------------------
El procesamiento por lotes es crucial para operaciones que manejan grandes
volúmenes de datos. Beneficios:

**Memoria**: Procesar 1000 facturas de una vez podría agotar la RAM
**Timeouts**: Transacciones muy largas pueden exceder límites del servidor
**Experiencia**: Commits intermedios muestran progreso al usuario
**Recuperación**: Más fácil recuperarse de errores en lotes pequeños

Factory Pattern para Compresión
------------------------------
El método _get_compression_engine() implementa el patrón Factory, que
permite añadir nuevos formatos de compresión sin modificar el código
principal. Para añadir un nuevo formato:

1. Añadir opción en _get_available_compression_formats()
2. Añadir caso en _get_compression_engine()
3. Añadir lógica en _add_file_to_archive() si es necesario

Context Managers para Recursos
------------------------------
El uso de `with` statements para archivos temporales y archivos comprimidos
garantiza que los recursos se liberen automáticamente, incluso si hay errores.
Esto previene leaks de memoria y archivos huérfanos.

Configuración Automática Inteligente
------------------------------------
El método default_get() implementa configuración automática que mejora
significativamente la experiencia del usuario:

- Si seleccionas facturas y abres el wizard, se preconfiguran automáticamente
- La empresa se detecta de las facturas seleccionadas
- Las configuraciones predeterminadas se aplican automáticamente
- La plantilla por defecto se selecciona si existe

Esto elimina trabajo repetitivo y reduce errores de configuración.

Logging Estratégico
------------------
El logging en este wizard está diseñado para facilitar:

**Debugging**: Información detallada sobre el procesamiento
**Auditoría**: Registro de quién exportó qué y cuándo
**Monitoreo**: Métricas de rendimiento y estadísticas de uso
**Soporte**: Información para resolver problemas del usuario

El logging usa diferentes niveles (info, warning, error) para facilitar
el filtrado según las necesidades específicas.

Métricas de Rendimiento
----------------------
El wizard calcula y almacena métricas importantes:

- Tiempo de procesamiento total
- Ratio de compresión logrado
- Número de éxitos vs errores
- Tamaño original vs comprimido

Estas métricas son útiles para:
- Optimizar configuraciones de servidor
- Detectar problemas de rendimiento
- Justificar inversiones en infraestructura
- Proporcionar feedback valioso al usuario
"""
