# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class BulkExportWizard(models.TransientModel):
    """Wizard para exportación masiva de facturas - CORREGIDO"""
    _name = 'account.bulk.export.wizard'
    _description = 'Bulk Invoice Export Wizard'

    # ==========================================
    # FIELDS
    # ==========================================
    
    state = fields.Selection([
        ('draft', 'Configuration'),
        ('processing', 'Processing'),
        ('done', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # Facturas seleccionadas
    invoice_ids = fields.Many2many(
        'account.move',
        string='Selected Invoices',
        help='Pre-selected invoices from list view'
    )

    # Filtros básicos
    include_out_invoice = fields.Boolean(string='Customer Invoices', default=True)
    include_in_invoice = fields.Boolean(string='Vendor Bills', default=True)
    include_out_refund = fields.Boolean(string='Customer Credit Notes', default=False)
    include_in_refund = fields.Boolean(string='Vendor Credit Notes', default=False)

    state_filter = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('all', 'All States'),
    ], string='Invoice State', default='posted')

    # Resultados
    export_file = fields.Binary(string='Export File', readonly=True)
    export_filename = fields.Char(string='Export Filename', readonly=True)
    export_count = fields.Integer(string='Exported Count', readonly=True)
    failed_count = fields.Integer(string='Failed Count', readonly=True)
    processing_time = fields.Float(string='Processing Time (s)', readonly=True)
    error_message = fields.Text(string='Error Details', readonly=True)

    # ==========================================
    # MÉTODOS PRINCIPALES - CORREGIDOS
    # ==========================================

    def action_start_export(self):
        """Inicia el proceso de exportación - MÉTODO REQUERIDO POR XML"""
        self.ensure_one()
        
        try:
            self.write({'state': 'processing', 'error_message': False})
            
            start_time = datetime.now()
            
            # Obtener facturas
            invoices = self._get_invoices_to_export()
            
            if not invoices:
                raise UserError(_('No invoices found matching the criteria.'))

            # Generar archivo
            zip_buffer = io.BytesIO()
            exported_count = 0
            failed_count = 0

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for invoice in invoices:
                    try:
                        pdf_content = self._get_invoice_pdf_safe(invoice)
                        if pdf_content:
                            filename = f"{self._sanitize_filename(invoice.name or 'DRAFT')}.pdf"
                            zip_file.writestr(filename, pdf_content)
                            exported_count += 1
                            _logger.info(f"✓ Exported: {filename}")
                        else:
                            failed_count += 1
                            _logger.warning(f"✗ Failed to export: {invoice.name}")
                            
                    except Exception as e:
                        _logger.error(f"Error exporting {invoice.name}: {str(e)}")
                        failed_count += 1

            # Guardar resultado
            zip_data = zip_buffer.getvalue()
            zip_buffer.close()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            self.write({
                'state': 'done',
                'export_file': base64.b64encode(zip_data),
                'export_filename': f'invoices_{timestamp}.zip',
                'export_count': exported_count,
                'failed_count': failed_count,
                'processing_time': round(processing_time, 2),
            })

        except Exception as e:
            _logger.error(f"Export failed: {str(e)}", exc_info=True)
            self.write({
                'state': 'error',
                'error_message': str(e),
            })

        return self._reload_wizard()

    def action_download(self):
        """Descarga el archivo generado - MÉTODO REQUERIDO POR XML"""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_('No file available for download.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=export_file&filename_field=export_filename&download=true',
            'target': 'self',
        }

    def action_restart(self):
        """Reinicia el wizard para nueva exportación - MÉTODO REQUERIDO POR XML"""
        self.ensure_one()
        
        self.write({
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'failed_count': 0,
            'processing_time': 0,
            'error_message': False,
        })
        
        return self._reload_wizard()

    # ==========================================
    # MÉTODOS AUXILIARES - CORREGIDOS
    # ==========================================

    def _get_invoices_to_export(self):
        """Obtiene facturas basado en criterios"""
        self.ensure_one()

        # Si hay facturas pre-seleccionadas, usarlas
        if self.invoice_ids:
            return self.invoice_ids

        # Construir domain
        domain = [('company_id', '=', self.company_id.id)]

        # Tipos de movimiento - CORREGIDO: usar 'in' en lugar de '='
        move_types = []
        if self.include_out_invoice:
            move_types.append('out_invoice')
        if self.include_in_invoice:
            move_types.append('in_invoice')
        if self.include_out_refund:
            move_types.append('out_refund')
        if self.include_in_refund:
            move_types.append('in_refund')
        
        if move_types:
            domain.append(('move_type', 'in', move_types))  # CORREGIDO

        # Estado
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        return self.env['account.move'].search(domain)

<<<<<<< HEAD
    def _get_invoice_pdf_safe(self, invoice):
        """Genera PDF de forma segura - CORREGIDO"""
=======
    def _generate_export_file(self, invoices):
        """
        Genera el archivo comprimido con PDFs de facturas.
        
        Args:
            invoices: recordset de facturas a exportar
            
        Returns:
            tuple: (datos_archivo, cantidad_fallidas, cantidad_adjuntos)
        """
        self.ensure_one()

        if self.compression_format in ['zip', 'zip_password']:
            return self._generate_zip_file(invoices)
        elif self.compression_format == 'tar_gz':
            return self._generate_tar_file(invoices, 'gz')
        elif self.compression_format == 'tar_bz2':
            return self._generate_tar_file(invoices, 'bz2')

    def _generate_zip_file(self, invoices):
        """
        Genera archivo ZIP con facturas usando procesamiento por lotes.
        
        Args:
            invoices: recordset de facturas
            
        Returns:
            tuple: (datos_zip, cantidad_fallidas, cantidad_adjuntos)
        """
        # Validar límites antes de procesar
        self._validate_export_limits(invoices)
        
        buffer = io.BytesIO()
        failed_count = 0
        attachments_count = 0
        total = len(invoices)
        processed = 0

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            
            # Configurar contraseña si es necesario
            if self.compression_format == 'zip_password' and self.archive_password:
                zip_file.setpassword(self.archive_password.encode('utf-8'))

            # Procesar en lotes para optimizar memoria
            batch_size = min(self.batch_size, 50)  # Máximo 50 por lote
            
            for batch_start in range(0, total, batch_size):
                batch_end = min(batch_start + batch_size, total)
                batch_invoices = invoices[batch_start:batch_end]
                
                # Procesar lote actual
                for invoice in batch_invoices:
                    processed += 1
                    try:
                        # Actualizar progreso
                        progress = 20 + (processed / total) * 60  # 20-80%
                        self._update_progress(
                            progress,
                            _('Procesando factura %d de %d: %s') % (processed, total, invoice.name)
                        )
                        
                        # Determinar carpeta según organización
                        folder = ''
                        if self.organize_by_type:
                            folder = self._get_folder_name(invoice) + '/'
                        
                        # Generar archivo
                        filename = folder + self._generate_filename(invoice)
                        pdf_content = self._get_invoice_pdf_enhanced(invoice)
                        
                        if not self._validate_pdf_content(pdf_content):
                            _logger.warning(f"PDF inválido para factura {invoice.name}")
                            failed_count += 1
                            continue
                        
                        # Agregar PDF al ZIP
                        if self.compression_format == 'zip_password':
                            zip_file.writestr(
                                filename,
                                pdf_content,
                                pwd=self.archive_password.encode('utf-8') if self.archive_password else None
                            )
                        else:
                            zip_file.writestr(filename, pdf_content)
                        
                        # Liberar memoria del PDF
                        del pdf_content
                        
                        # Agregar adjuntos si está habilitado
                        if self.include_attachments:
                            attachments = self._get_invoice_attachments(invoice)
                            attachments_count += len(attachments)
                            
                            for att_filename, att_content in attachments:
                                att_path = folder + 'adjuntos/' + invoice.name + '/'
                                full_path = att_path + att_filename
                                
                                if self.compression_format == 'zip_password':
                                    zip_file.writestr(
                                        full_path,
                                        att_content,
                                        pwd=self.archive_password.encode('utf-8')
                                    )
                                else:
                                    zip_file.writestr(full_path, att_content)
                                
                                # Liberar memoria del adjunto
                                del att_content
                            
                    except Exception as e:
                        _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                        failed_count += 1
                        continue
                
                # Commit intermedio para liberar memoria
                if batch_start > 0 and batch_start % (batch_size * 5) == 0:
                    self.env.cr.commit()

        # Actualizar progreso final
        self._update_progress(90, _('Finalizando archivo...'))
        
        buffer.seek(0)
        return buffer.getvalue(), failed_count, attachments_count

    def _generate_tar_file(self, invoices, compression):
        """
        Genera archivo TAR con compresión.
        
        Args:
            invoices: recordset de facturas
            compression: tipo de compresión ('gz' o 'bz2')
            
        Returns:
            tuple: (datos_tar, cantidad_fallidas, cantidad_adjuntos)
        """
        buffer = io.BytesIO()
        failed_count = 0
        attachments_count = 0
        total = len(invoices)

        mode = f'w:{compression}'
        with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
            
            for idx, invoice in enumerate(invoices, 1):
                try:
                    # Actualizar progreso
                    progress = 20 + (idx / total) * 60
                    self._update_progress(
                        progress,
                        _('Procesando factura %d de %d: %s') % (idx, total, invoice.name)
                    )
                    
                    # Determinar carpeta
                    folder = ''
                    if self.organize_by_type:
                        folder = self._get_folder_name(invoice) + '/'
                    
                    # Generar archivo - MÉTODO SIMPLIFICADO
                    filename = folder + self._generate_filename(invoice)
                    pdf_content = self._get_invoice_pdf_enhanced(invoice)  # Ahora es más robusto
                    
                    if not pdf_content or len(pdf_content) < 50:
                        _logger.warning(f"PDF inválido para factura {invoice.name}")
                        failed_count += 1
                        continue
                        
                    # Asegurar que pdf_content sea bytes
                    if isinstance(pdf_content, str):
                        pdf_content = pdf_content.encode('utf-8')
                    
                    # Crear tarinfo y agregar al TAR
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(pdf_content)
                    tarinfo.mtime = datetime.now().timestamp()
                    tar_file.addfile(tarinfo, io.BytesIO(pdf_content))
                    
                    # Agregar adjuntos si está habilitado
                    if self.include_attachments:
                        attachments = self._get_invoice_attachments(invoice)
                        attachments_count += len(attachments)
                        
                        for att_filename, att_content in attachments:
                            # Crear subcarpeta de adjuntos
                            att_path = folder + 'adjuntos/' + invoice.name + '/'
                            full_path = att_path + att_filename
                            
                            # Crear tarinfo para el adjunto
                            att_tarinfo = tarfile.TarInfo(name=full_path)
                            att_tarinfo.size = len(att_content)
                            att_tarinfo.mtime = datetime.now().timestamp()
                            tar_file.addfile(att_tarinfo, io.BytesIO(att_content))
                    
                except Exception as e:
                    _logger.error(f"Error procesando factura {invoice.name}: {str(e)}")
                    failed_count += 1
                    continue  # Continuar con la siguiente factura

        self._update_progress(90, _('Finalizando archivo...'))
        
        buffer.seek(0)
        return buffer.getvalue(), failed_count, attachments_count

    def _get_folder_name(self, invoice):
        """
        Obtiene el nombre de carpeta para organización por tipo.
        
        Args:
            invoice: registro de factura
            
        Returns:
            str: nombre de carpeta
        """
        folder_names = {
            'out_invoice': '01_Facturas_Cliente',
            'in_invoice': '02_Facturas_Proveedor',
            'out_refund': '03_Notas_Credito_Cliente',
            'in_refund': '04_Notas_Credito_Proveedor',
        }
        return folder_names.get(invoice.move_type, '05_Otros')

    def _generate_filename(self, invoice):
        """Genera nombre de archivo basado en el patrón configurado."""
        # Mapeo de tipos de documento
        move_type_names = {
            'out_invoice': 'FAC_CLI',
            'in_invoice': 'FAC_PROV', 
            'out_refund': 'NC_CLI',
            'in_refund': 'NC_PROV',
        }
        
        # Sanitizar componentes
        move_type = move_type_names.get(invoice.move_type, 'DOC')
        number = self._sanitize_filename_enhanced(invoice.name or 'BORRADOR')
        partner = self._sanitize_filename_enhanced(invoice.partner_id.name or 'DESCONOCIDO')[:40]
        
        if invoice.invoice_date:
            date_str = invoice.invoice_date.strftime('%Y%m%d')
        else:
            date_str = fields.Date.today().strftime('%Y%m%d')

        # Patrones de nombres
        patterns = {
            'standard': f'{move_type}_{number}_{partner}_{date_str}.pdf',
            'date_first': f'{date_str}_{move_type}_{number}_{partner}.pdf', 
            'partner_first': f'{partner}_{move_type}_{number}_{date_str}.pdf',
            'simple': f'{move_type}_{number}_{date_str}.pdf',
        }
        
        return patterns.get(self.filename_pattern, patterns['standard'])

    def _sanitize_filename_enhanced(self, name):
        """
        Sanitización avanzada de nombres de archivo.
        Maneja acentos, caracteres especiales y longitud.
        """
        if not name:
            return 'Sin_Nombre'
        
        # Normalizar caracteres Unicode y eliminar acentos
        normalized = unicodedata.normalize('NFKD', name)
        ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Reemplazar caracteres problemáticos
        ascii_name = re.sub(r'[<>:"/\\|?*¿¡]', '_', ascii_name)
        ascii_name = re.sub(r'[áéíóúàèìòùâêîôûäëïöüñç]', lambda m: {
            'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u',
            'à':'a', 'è':'e', 'ì':'i', 'ò':'o', 'ù':'u',
            'â':'a', 'ê':'e', 'î':'i', 'ô':'o', 'û':'u',
            'ä':'a', 'ë':'e', 'ï':'i', 'ö':'o', 'ü':'u',
            'ñ':'n', 'ç':'c'
        }.get(m.group().lower(), m.group()), ascii_name, flags=re.IGNORECASE)
        
        # Limpiar espacios y caracteres repetidos
        ascii_name = re.sub(r'\s+', '_', ascii_name)
        ascii_name = re.sub(r'_+', '_', ascii_name)
        ascii_name = ascii_name.strip('_')
        
        # Prevenir path traversal
        ascii_name = ascii_name.replace('..', '')
        
        # Limitar longitud
        if len(ascii_name) > 180:
            ascii_name = ascii_name[:180]
        
        return ascii_name or 'Archivo_Sin_Nombre'

    def _get_invoice_pdf_enhanced(self, invoice):
        """
        Genera PDF de factura con estrategia simplificada y robusta.
        """
        try:
            # 1. Buscar PDF adjunto existente
            pdf_attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('mimetype', '=', 'application/pdf'),
                ('name', 'ilike', '%.pdf')
            ], limit=1)
            
            if pdf_attachment and pdf_attachment.datas:
                try:
                    pdf_content = base64.b64decode(pdf_attachment.datas)
                    if self._validate_pdf_content(pdf_content):
                        return pdf_content
                except Exception:
                    pass
            
            # 2. Generar usando reporte estándar de facturas
            try:
                report = self.env.ref('account.account_invoices', raise_if_not_found=False)
                if report:
                    pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                    if self._validate_pdf_content(pdf_content):
                        return pdf_content
            except Exception as e:
                _logger.warning(f"Error generando PDF estándar para {invoice.name}: {e}")
            
            # 3. Fallback: buscar cualquier reporte disponible
            reports = self.env['ir.actions.report'].search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ], limit=3)
            
            for report in reports:
                try:
                    pdf_content, _ = report.sudo()._render_qweb_pdf([invoice.id])
                    if self._validate_pdf_content(pdf_content):
                        return pdf_content
                except Exception:
                    continue
            
            # 4. Último recurso: PDF básico
            return self._generate_emergency_pdf_content(invoice)
            
        except Exception as e:
            _logger.error(f"Error crítico generando PDF para {invoice.name}: {e}")
            return self._generate_emergency_pdf_content(invoice)







    def _generate_pdf_via_print_action(self, invoice):
        """Genera PDF usando la acción de impresión estándar de Odoo con validación mejorada."""
>>>>>>> parent of 406da11 ([fix] few bugs)
        try:
            # Validar invoice
            if not invoice or not invoice.exists():
                return None

            # Buscar reporte de facturas - CORREGIDO
            report_model = self.env['ir.actions.report']
            
            # Buscar por nombre específico primero
            reports = report_model.search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf')
            ])
            
            # Filtrar el reporte correcto
            target_report = None
            for report in reports:
                if hasattr(report, 'report_name') and report.report_name:
                    # CORREGIDO: validar tipo antes de operaciones string
                    if isinstance(report.report_name, str) and 'account_invoices' in report.report_name:
                        target_report = report
                        break

            # Si no encontramos específico, usar el primero
            if not target_report and reports:
                target_report = reports[0]

            if not target_report:
                _logger.warning(f"No PDF report found for {invoice.name}")
                return None

            # Generar PDF - CORREGIDO: usar IDs seguros
            pdf_content, _ = target_report._render_qweb_pdf([invoice.id])
            
            return pdf_content if pdf_content else None

        except Exception as e:
            _logger.error(f"Error generating PDF for {invoice.name}: {str(e)}")
            return None

    def _sanitize_filename(self, name):
        """Sanitiza nombres de archivo - CORREGIDO"""
        try:
            # CORREGIDO: validar tipo antes de operaciones
            if isinstance(name, list):
                name = name[0] if name else 'unknown'
                
            if not isinstance(name, str):
                name = str(name) if name else 'unknown'

            # Limpiar caracteres problemáticos
            import re
            safe_name = re.sub(r'[^\w\-_\.]', '_', name)
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')
            
            return safe_name or 'unknown_file'
            
        except Exception as e:
            _logger.error(f"Error sanitizing filename: {str(e)}")
            return 'unknown_file'

    def _reload_wizard(self):
        """Recarga wizard manteniendo contexto"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    # ==========================================
    # MÉTODO LEGACY PARA COMPATIBILIDAD
    # ==========================================
    
    def action_export(self):
        """Método legacy - redirige a action_start_export"""
        return self.action_start_export()
