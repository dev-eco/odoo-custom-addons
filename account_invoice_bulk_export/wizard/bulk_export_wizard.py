# -*- coding: utf-8 -*-
import base64
import io
import zipfile
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BulkExportWizard(models.TransientModel):
    """Wizard simplificado para exportación masiva de facturas"""
    _name = 'account.bulk.export.wizard'
    _description = 'Bulk Invoice Export Wizard'

    # Campos básicos
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices to Export',
        domain="[('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']), "
               "('state', '=', 'posted'), "
               "('company_id', '=', company_id)]"
    )
    
    export_file = fields.Binary(string='Export File', readonly=True)
    export_filename = fields.Char(string='Filename', readonly=True)

    def action_export(self):
        """Acción principal de exportación"""
        self.ensure_one()
        
        if not self.invoice_ids:
            raise UserError(_('Please select at least one invoice to export.'))
        
        # Crear archivo ZIP
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            exported_count = 0
            failed_invoices = []
            
            for invoice in self.invoice_ids:
                try:
                    # Usar el reporte estándar de Odoo
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    if pdf_content:
                        # Nombre simple y seguro
                        filename = f"{invoice.name or 'DRAFT'}.pdf".replace('/', '_')
                        zip_file.writestr(filename, pdf_content)
                        exported_count += 1
                        _logger.info(f"✓ Exported: {filename}")
                    else:
                        failed_invoices.append(invoice.name or 'DRAFT')
                        
                except Exception as e:
                    _logger.error(f"Error exporting invoice {invoice.name}: {str(e)}")
                    failed_invoices.append(invoice.name or 'DRAFT')
        
        # Preparar el archivo para descarga
        zip_data = zip_buffer.getvalue()
        zip_buffer.close()
        
        if exported_count == 0:
            raise UserError(_('No invoices could be exported.'))
        
        # Guardar archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'invoices_{timestamp}.zip'
        
        self.write({
            'export_file': base64.b64encode(zip_data),
            'export_filename': filename,
        })
        
        # Mostrar resumen
        message = f"Exported {exported_count} invoices successfully."
        if failed_invoices:
            message += f"\nFailed: {', '.join(failed_invoices[:5])}"
            if len(failed_invoices) > 5:
                message += f" and {len(failed_invoices) - 5} more..."
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_message': message}
        }
    
    def _get_invoice_pdf(self, invoice):
        """Obtiene el PDF de una factura usando el método estándar"""
        try:
            # Buscar el reporte estándar de factura
            report = self.env.ref('account.account_invoices', raise_if_not_found=False)
            
            if not report:
                # Buscar cualquier reporte de facturas
                report = self.env['ir.actions.report'].search([
                    ('model', '=', 'account.move'),
                    ('report_type', '=', 'qweb-pdf')
                ], limit=1)
            
            if report:
                pdf_content, _ = report._render_qweb_pdf(invoice.ids)
                return pdf_content
            
        except Exception as e:
            _logger.error(f"Error generating PDF for {invoice.name}: {str(e)}")
        
        return None
    
    def action_download(self):
        """Descargar el archivo generado"""
        self.ensure_one()
        
        if not self.export_file:
            raise UserError(_('No file available for download.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=export_file&filename_field=export_filename&download=true',
            'target': 'self',
        }
