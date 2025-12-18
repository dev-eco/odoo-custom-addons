# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError
from datetime import timedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # ==========================================
    # CONFIGURACIONES DE EXPORTACIÓN
    # ==========================================
    
    bulk_export_default_format = fields.Selection([
        ('zip', '📦 ZIP Estándar'),
        ('zip_password', '🔒 ZIP con Contraseña'),
        ('tar_gz', '🗜️ TAR.GZ (Compresión Alta)'),
        ('tar_bz2', '📚 TAR.BZ2 (Máxima Compresión)'),
    ], string='Formato de Compresión por Defecto', 
       default='zip',
       config_parameter='account_invoice_bulk_export.default_format',
       help='Formato predeterminado para nuevas exportaciones')
    
    bulk_export_default_pattern = fields.Selection([
        ('standard', 'Estándar: TIPO_NUMERO_CLIENTE_FECHA'),
        ('date_first', 'Por Fecha: FECHA_TIPO_NUMERO_CLIENTE'),
        ('partner_first', 'Por Cliente: CLIENTE_TIPO_NUMERO_FECHA'),
        ('simple', 'Simplificado: TIPO_NUMERO_FECHA'),
    ], string='Patrón de Nombres por Defecto', 
       default='standard',
       config_parameter='account_invoice_bulk_export.default_pattern',
       help='Esquema predeterminado para nombrar archivos PDF')
    
    bulk_export_default_batch_size = fields.Integer(
        string='Tamaño de Lote por Defecto',
        default=50,
        config_parameter='account_invoice_bulk_export.default_batch_size',
        help='Número de facturas a procesar simultáneamente (1-500)'
    )
    
    bulk_export_include_xml = fields.Boolean(
        string='Incluir XML por Defecto',
        default=False,
        config_parameter='account_invoice_bulk_export.include_xml',
        help='Incluir archivos XML de facturación electrónica automáticamente'
    )
    
    bulk_export_include_attachments = fields.Boolean(
        string='Incluir Adjuntos por Defecto',
        default=False,
        config_parameter='account_invoice_bulk_export.include_attachments',
        help='Incluir archivos adjuntos a las facturas automáticamente'
    )
    
    bulk_export_group_by_type = fields.Boolean(
        string='Organizar por Tipo por Defecto',
        default=True,
        config_parameter='account_invoice_bulk_export.group_by_type',
        help='Crear carpetas separadas por tipo de documento automáticamente'
    )
    
    bulk_export_max_invoices = fields.Integer(
        string='Máximo de Facturas por Exportación',
        default=1000,
        config_parameter='account_invoice_bulk_export.max_invoices',
        help='Límite máximo de facturas que se pueden exportar de una vez'
    )
    
    bulk_export_auto_cleanup_days = fields.Integer(
        string='Días para Limpieza Automática del Historial',
        default=90,
        config_parameter='account_invoice_bulk_export.auto_cleanup_days',
        help='Días después de los cuales se eliminan automáticamente los registros del historial (0 = nunca)'
    )
    
    # ==========================================
    # CONFIGURACIONES DE RENDIMIENTO
    # ==========================================
    
    bulk_export_enable_background = fields.Boolean(
        string='Habilitar Procesamiento en Segundo Plano',
        default=False,
        config_parameter='account_invoice_bulk_export.enable_background',
        help='Permitir procesamiento en background para exportaciones grandes (requiere queue_job)'
    )
    
    bulk_export_background_threshold = fields.Integer(
        string='Umbral para Procesamiento en Background',
        default=100,
        config_parameter='account_invoice_bulk_export.background_threshold',
        help='Número mínimo de facturas para sugerir procesamiento en background'
    )
    
    # ==========================================
    # VALIDACIONES
    # ==========================================
    
    @api.constrains('bulk_export_default_batch_size')
    def _check_batch_size(self):
        for record in self:
            if not (1 <= record.bulk_export_default_batch_size <= 500):
                raise ValidationError(_(
                    'El tamaño de lote debe estar entre 1 y 500. '
                    'Valor actual: %d'
                ) % record.bulk_export_default_batch_size)
    
    @api.constrains('bulk_export_max_invoices')
    def _check_max_invoices(self):
        for record in self:
            if not (1 <= record.bulk_export_max_invoices <= 10000):
                raise ValidationError(_(
                    'El máximo de facturas debe estar entre 1 y 10,000. '
                    'Valor actual: %d'
                ) % record.bulk_export_max_invoices)
    
    @api.constrains('bulk_export_auto_cleanup_days')
    def _check_cleanup_days(self):
        for record in self:
            if record.bulk_export_auto_cleanup_days < 0:
                raise ValidationError(_(
                    'Los días de limpieza automática no pueden ser negativos. '
                    'Use 0 para deshabilitar la limpieza automática.'
                ))
    
    @api.constrains('bulk_export_background_threshold')
    def _check_background_threshold(self):
        for record in self:
            if not (10 <= record.bulk_export_background_threshold <= 1000):
                raise ValidationError(_(
                    'El umbral para procesamiento en background debe estar entre 10 y 1,000. '
                    'Valor actual: %d'
                ) % record.bulk_export_background_threshold)
    
    # ==========================================
    # MÉTODOS DE UTILIDAD
    # ==========================================
    
    def action_test_pdf_generation(self):
        """Prueba la generación de PDF con una factura de ejemplo."""
        self.ensure_one()
        
        # Buscar una factura de prueba
        test_invoice = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not test_invoice:
            raise exceptions.UserError(_(
                'No se encontró ninguna factura confirmada para realizar la prueba. '
                'Cree y confirme al menos una factura antes de ejecutar esta prueba.'
            ))
        
        try:
            # Intentar generar PDF usando el wizard
            wizard = self.env['account.bulk.export.wizard'].create({
                'company_id': self.env.company.id,
                'invoice_ids': [(6, 0, [test_invoice.id])],
            })
            
            pdf_content = wizard._get_invoice_pdf(test_invoice)
            
            if pdf_content and len(pdf_content) > 100:
                message = _(
                    '✅ Prueba de generación PDF exitosa!\n\n'
                    'Factura de prueba: %s\n'
                    'Tamaño del PDF: %d bytes\n'
                    'El sistema está funcionando correctamente.'
                ) % (test_invoice.name, len(pdf_content))
                message_type = 'success'
            else:
                message = _(
                    '⚠️ Prueba de generación PDF falló!\n\n'
                    'Factura de prueba: %s\n'
                    'El PDF generado está vacío o es inválido.\n'
                    'Revise la configuración de reportes.'
                ) % test_invoice.name
                message_type = 'warning'
                
        except Exception as e:
            message = _(
                '❌ Error en la prueba de generación PDF!\n\n'
                'Factura de prueba: %s\n'
                'Error: %s\n\n'
                'Revise los logs del sistema para más detalles.'
            ) % (test_invoice.name, str(e))
            message_type = 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Resultado de Prueba PDF'),
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }
    
    def action_cleanup_history(self):
        """Limpia manualmente el historial de exportaciones antiguas."""
        self.ensure_one()
        
        if self.bulk_export_auto_cleanup_days <= 0:
            raise exceptions.UserError(_(
                'La limpieza automática está deshabilitada. '
                'Configure un número de días mayor a 0 para habilitar esta función.'
            ))
        
        cutoff_date = fields.Datetime.now() - timedelta(days=self.bulk_export_auto_cleanup_days)
        
        old_records = self.env['account.invoice.export.history'].search([
            ('export_date', '<', cutoff_date)
        ])
        
        count = len(old_records)
        old_records.unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Limpieza de Historial Completada'),
                'message': _('Se eliminaron %d registros de historial anteriores a %s.') % (
                    count, cutoff_date.strftime('%d/%m/%Y')
                ),
                'type': 'success',
            }
        }
