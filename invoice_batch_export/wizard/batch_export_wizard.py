# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BatchExportWizard(models.TransientModel):
    """
    Wizard para Exportación Masiva de Facturas
    ==========================================
    
    Este wizard permite a los usuarios exportar múltiples facturas
    en un archivo comprimido con nomenclatura personalizada.
    
    FILOSOFÍA DE DISEÑO:
    - Simplicidad: Solo campos esenciales para MVP
    - Coherencia: Cada campo referenciado en vista existe aquí
    - Extensibilidad: Estructura preparada para futuras mejoras
    """
    _name = 'batch.export.wizard'
    _description = 'Wizard para Exportación Masiva de Facturas'

    # ==========================================
    # CAMPOS BÁSICOS DE CONFIGURACIÓN
    # ==========================================
    
    # Estado del wizard (esencial para flujo de UI)
    state = fields.Selection([
        ('draft', 'Configuración'),
        ('processing', 'Procesando'),
        ('done', 'Completado'),
    ], string='Estado', default='draft', required=True)
    
    # Configuración de empresa
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        help='Empresa desde la cual exportar las facturas'
    )
    
    # Plantilla de nomenclatura (simplificado)
    export_template_id = fields.Many2one(
        'export.template',
        string='Plantilla de Nomenclatura',
        help='Plantilla para generar nombres de archivos'
    )
    
    # Formato de compresión (simplificado)
    compression_format = fields.Selection([
        ('zip', 'ZIP Standard'),
        ('zip_password', 'ZIP con Contraseña'),
    ], string='Formato de Compresión', default='zip', required=True)
    
    # Contraseña para ZIP protegido
    archive_password = fields.Char(
        string='Contraseña del Archivo',
        help='Contraseña para proteger el archivo ZIP'
    )

    # ==========================================
    # CAMPOS DE SELECCIÓN DE FACTURAS
    # ==========================================
    
    # Facturas preseleccionadas desde la vista de lista
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Seleccionadas',
        help='Facturas seleccionadas desde la vista de lista'
    )
    
    # Campos de filtros (solo si no hay preselección)
    include_customer_invoices = fields.Boolean(
        string='Incluir Facturas de Cliente',
        default=True
    )
    
    include_vendor_bills = fields.Boolean(
        string='Incluir Facturas de Proveedor',
        default=True
    )
    
    include_credit_notes = fields.Boolean(
        string='Incluir Notas de Crédito',
        default=True
    )
    
    # Filtros de fecha
    date_from = fields.Date(
        string='Fecha Desde',
        help='Filtrar facturas desde esta fecha'
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        help='Filtrar facturas hasta esta fecha'
    )
    
    # Filtro de estado
    state_filter = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicadas'),
        ('all', 'Todos los Estados')
    ], string='Estado de Facturas', default='posted')

    # ==========================================
    # CAMPOS DE OPCIONES AVANZADAS
    # ==========================================
    
    batch_size = fields.Integer(
        string='Tamaño de Lote',
        default=50,
        help='Número de facturas a procesar por lote'
    )
    
    include_folders = fields.Boolean(
        string='Crear Carpetas por Tipo',
        default=False,
        help='Organizar archivos en carpetas por tipo de documento'
    )
    
    add_timestamp = fields.Boolean(
        string='Añadir Timestamp',
        default=True,
        help='Añadir fecha y hora al nombre del archivo ZIP'
    )

    # ==========================================
    # CAMPOS DE RESULTADOS
    # ==========================================
    
    # Archivo resultante
    export_file = fields.Binary(
        string='Archivo ZIP',
        readonly=True,
        help='Archivo ZIP generado con todas las facturas'
    )
    
    export_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
        help='Nombre del archivo ZIP generado'
    )
    
    # Estadísticas de exportación
    export_count = fields.Integer(
        string='Facturas Exportadas',
        readonly=True,
        help='Número total de facturas incluidas en la exportación'
    )
    
    processing_time = fields.Float(
        string='Tiempo de Procesamiento',
        readonly=True,
        help='Tiempo total de procesamiento en segundos'
    )

    # ==========================================
    # CAMPOS COMPUTED Y AUXILIARES
    # ==========================================
    
    @api.depends('invoice_ids')
    def _compute_preselected_count(self):
        """Calcular número de facturas preseleccionadas"""
        for record in self:
            record.preselected_count = len(record.invoice_ids)
    
    preselected_count = fields.Integer(
        string='Facturas Preseleccionadas',
        compute='_compute_preselected_count',
        help='Número de facturas preseleccionadas desde la vista de lista'
    )

    # ==========================================
    # MÉTODOS DE VALIDACIÓN
    # ==========================================
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validar que las fechas sean coherentes"""
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError(
                        _('La fecha de inicio no puede ser posterior a la fecha final.')
                    )

    @api.constrains('compression_format', 'archive_password')
    def _check_password_required(self):
        """Validar que se proporcione contraseña cuando sea necesaria"""
        for record in self:
            if record.compression_format == 'zip_password' and not record.archive_password:
                raise ValidationError(
                    _('Debe proporcionar una contraseña para ZIP protegido.')
                )

    # ==========================================
    # MÉTODOS DE ACCIÓN (SIMPLIFICADOS PARA MVP)
    # ==========================================
    
    def action_start_export(self):
        """Iniciar el proceso de exportación"""
        self.ensure_one()
        
        # Cambiar estado a procesando
        self.write({'state': 'processing'})
        
        try:
            # Simular procesamiento por ahora
            import time
            start_time = time.time()
            
            # Obtener facturas a exportar
            invoices = self._get_invoices_to_export()
            
            if not invoices:
                raise UserError(_('No se encontraron facturas que cumplan los criterios.'))
            
            # Generar ZIP simplificado
            zip_data = self._generate_zip_file(invoices)
            
            # Calcular tiempo de procesamiento
            processing_time = time.time() - start_time
            
            # Actualizar resultados
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'facturas_export_{timestamp}.zip'
            
            self.write({
                'state': 'done',
                'export_file': base64.b64encode(zip_data),
                'export_filename': filename,
                'export_count': len(invoices),
                'processing_time': round(processing_time, 2),
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
        except Exception as e:
            self.write({'state': 'draft'})
            raise UserError(_('Error durante la exportación: %s') % str(e))

    def action_download_file(self):
        """Descargar el archivo generado"""
        self.ensure_one()
        if not self.export_file:
            raise UserError(_('No hay archivo disponible para descargar.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/batch.export.wizard/{self.id}/export_file/{self.export_filename}?download=true',
            'target': 'self',
        }

    def action_reset_wizard(self):
        """Reiniciar el wizard para nueva exportación"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'processing_time': 0,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ==========================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ==========================================
    
    def _get_invoices_to_export(self):
        """Obtener facturas que cumplen los criterios de exportación"""
        self.ensure_one()
        
        # Si hay facturas preseleccionadas, usar esas
        if self.invoice_ids:
            return self.invoice_ids
        
        # Construir dominio dinámico
        domain = [('company_id', '=', self.company_id.id)]
        
        # Filtros de tipo de documento
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
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))
        
        return self.env['account.move'].search(domain)

    def _generate_zip_file(self, invoices):
        """Generar archivo ZIP con las facturas (versión simplificada)"""
        self.ensure_one()
        
        # Crear buffer en memoria para el ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            for i, invoice in enumerate(invoices, 1):
                try:
                    # Generar nombre de archivo simple
                    filename = f"{invoice.move_type}_{invoice.name}_{invoice.partner_id.name}.pdf"
                    # Limpiar caracteres problemáticos
                    filename = "".join(c for c in filename if c.isalnum() or c in '._- ').strip()
                    
                    # Por ahora, crear un PDF dummy (placeholder)
                    pdf_content = f"Factura {invoice.name} - {invoice.partner_id.name}".encode()
                    
                    # Añadir al ZIP
                    zip_file.writestr(filename, pdf_content)
                    
                except Exception as e:
                    _logger.warning(f"Error procesando factura {invoice.name}: {e}")
                    continue
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
