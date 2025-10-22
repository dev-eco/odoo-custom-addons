# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


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
    
    # Campo computado para tasa de éxito
    success_rate = fields.Float(
        string='Tasa de Éxito (%)',
        compute='_compute_success_rate',
        store=True,
    )
    
    @api.depends('exported_count', 'total_invoices')
    def _compute_success_rate(self):
        """Calcula la tasa de éxito de la exportación."""
        for record in self:
            if record.total_invoices > 0:
                record.success_rate = (record.exported_count / record.total_invoices) * 100
            else:
                record.success_rate = 0.0
    
    def name_get(self):
        """Personaliza el nombre mostrado del registro."""
        result = []
        for record in self:
            name = f"{record.export_filename} ({record.export_date.strftime('%d/%m/%Y %H:%M')})"
            result.append((record.id, name))
        return result
