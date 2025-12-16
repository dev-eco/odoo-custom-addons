# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_round


class InvoiceExportHistory(models.Model):
    """Historial de exportaciones de facturas para auditoría."""
    
    _name = 'account.invoice.export.history'
    _description = 'Historial de Exportaciones de Facturas'
    _order = 'create_date desc'
    _rec_name = 'export_filename'

    # Información básica
    export_filename = fields.Char(
        string='Nombre de Archivo',
        required=True,
        index=True,
    )
    
    export_date = fields.Datetime(
        string='Fecha de Exportación',
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        index=True,
    )
    
    # Detalles de la exportación
    compression_format = fields.Selection([
        ('zip', 'ZIP'),
        ('zip_password', 'ZIP con Contraseña'),
        ('tar_gz', 'TAR.GZ'),
        ('tar_bz2', 'TAR.BZ2'),
    ], string='Formato de Compresión', required=True)
    
    filename_pattern = fields.Selection([
        ('standard', 'Tipo_Número_Partner_Fecha'),
        ('date_first', 'Fecha_Tipo_Número_Partner'),
        ('partner_first', 'Partner_Tipo_Número_Fecha'),
        ('simple', 'Tipo_Número_Fecha'),
    ], string='Patrón de Nombres')
    
    # Estadísticas
    total_invoices = fields.Integer(
        string='Total Facturas',
        required=True,
    )
    
    exported_count = fields.Integer(
        string='Exportadas Exitosamente',
        required=True,
    )
    
    failed_count = fields.Integer(
        string='Fallidas',
        default=0,
    )
    
    processing_time = fields.Float(
        string='Tiempo de Procesamiento (s)',
    )
    
    file_size = fields.Float(
        string='Tamaño del Archivo (MB)',
        help='Tamaño del archivo comprimido en megabytes',
    )
    
    # Detalles adicionales
    include_attachments = fields.Boolean(
        string='Incluyó Adjuntos',
        default=False,
    )
    
    organized_by_type = fields.Boolean(
        string='Organizado por Tipo',
        default=False,
        help='Si los archivos se organizaron en carpetas por tipo de documento',
    )
    
    # Filtros aplicados
    date_from = fields.Date(string='Fecha Desde')
    date_to = fields.Date(string='Fecha Hasta')
    
    move_types = fields.Char(
        string='Tipos de Documento',
        help='Tipos de documento incluidos en la exportación',
    )
    
    state_filter = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicada'),
        ('all', 'Todos los Estados'),
    ], string='Filtro de Estado')
    
    # Notas
    notes = fields.Text(string='Notas')
    
    # Relación con facturas exportadas
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Exportadas',
        help='Facturas incluidas en esta exportación',
    )
    
    # Campos computados mejorados
    success_rate = fields.Float(
        string='Tasa de Éxito (%)',
        compute='_compute_success_rate',
        store=True,
        help='Porcentaje de facturas exportadas exitosamente'
    )
    
    average_processing_time = fields.Float(
        string='Tiempo Promedio por Factura (s)',
        compute='_compute_average_processing_time',
        store=True,
        help='Tiempo promedio de procesamiento por factura'
    )
    
    compression_ratio = fields.Float(
        string='Ratio de Compresión',
        compute='_compute_compression_ratio',
        store=True,
        help='Ratio de compresión del archivo (estimado)'
    )
    
    @api.depends('exported_count', 'total_invoices')
    def _compute_success_rate(self):
        """Calcula la tasa de éxito de la exportación."""
        for record in self:
            if record.total_invoices > 0:
                record.success_rate = float_round(
                    (record.exported_count / record.total_invoices) * 100, 
                    precision_digits=2
                )
            else:
                record.success_rate = 0.0
    
    @api.depends('processing_time', 'exported_count')
    def _compute_average_processing_time(self):
        """Calcula el tiempo promedio de procesamiento por factura."""
        for record in self:
            if record.exported_count > 0 and record.processing_time > 0:
                record.average_processing_time = float_round(
                    record.processing_time / record.exported_count,
                    precision_digits=2
                )
            else:
                record.average_processing_time = 0.0
    
    @api.depends('file_size', 'exported_count')
    def _compute_compression_ratio(self):
        """Estima el ratio de compresión basado en el tamaño del archivo."""
        for record in self:
            if record.exported_count > 0 and record.file_size > 0:
                # Estimación: PDF promedio ~200KB, compresión típica 60-80%
                estimated_uncompressed = record.exported_count * 0.2  # MB
                if estimated_uncompressed > 0:
                    record.compression_ratio = float_round(
                        record.file_size / estimated_uncompressed,
                        precision_digits=2
                    )
                else:
                    record.compression_ratio = 1.0
            else:
                record.compression_ratio = 1.0
    
    def name_get(self):
        """Personaliza el nombre mostrado del registro."""
        result = []
        for record in self:
            date_str = record.export_date.strftime('%d/%m/%Y %H:%M')
            success_indicator = "✅" if record.success_rate >= 95 else "⚠️" if record.success_rate >= 80 else "❌"
            name = f"{success_indicator} {record.export_filename} ({date_str})"
            result.append((record.id, name))
        return result
    
    @api.model
    def create_from_wizard(self, wizard):
        """Crea registro de historial desde wizard de exportación."""
        move_types_map = {
            'out_invoice': 'Facturas Cliente',
            'in_invoice': 'Facturas Proveedor', 
            'out_refund': 'NC Cliente',
            'in_refund': 'NC Proveedor'
        }
        
        # Determinar tipos de movimiento incluidos
        included_types = []
        if wizard.include_out_invoice:
            included_types.append(move_types_map['out_invoice'])
        if wizard.include_in_invoice:
            included_types.append(move_types_map['in_invoice'])
        if wizard.include_out_refund:
            included_types.append(move_types_map['out_refund'])
        if wizard.include_in_refund:
            included_types.append(move_types_map['in_refund'])
        
        return self.create({
            'export_filename': wizard.export_filename,
            'export_date': fields.Datetime.now(),
            'user_id': wizard.env.user.id,
            'company_id': wizard.company_id.id,
            'compression_format': wizard.compression_format,
            'filename_pattern': wizard.filename_pattern,
            'total_invoices': wizard.export_count + wizard.failed_count,
            'exported_count': wizard.export_count,
            'failed_count': wizard.failed_count,
            'processing_time': wizard.processing_time,
            'file_size': wizard.file_size_mb,
            'include_attachments': wizard.include_attachments,
            'organized_by_type': wizard.group_by_type,
            'date_from': wizard.date_from,
            'date_to': wizard.date_to,
            'move_types': ', '.join(included_types),
            'state_filter': wizard.state_filter,
            'invoice_ids': [(6, 0, wizard.invoice_ids.ids)] if wizard.invoice_ids else False,
        })
