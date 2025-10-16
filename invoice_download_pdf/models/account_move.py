from odoo import models, api, fields
import base64
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def action_prepare_individual_downloads(self):
        """Prepara los PDFs individuales para las facturas seleccionadas"""
        # Verificar que hay facturas seleccionadas
        if not self:
            return
            
        # Filtrar solo facturas válidas (publicadas)
        valid_invoices = self.filtered(lambda inv: inv.state == 'posted' and 
                                inv.move_type in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'))
        
        if not valid_invoices:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Aviso',
                    'message': 'No hay facturas contabilizadas seleccionadas para descargar',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Crear un asistente con las facturas seleccionadas
        wizard = self.env['account.invoice.download.wizard'].create({
            'invoice_ids': [(6, 0, valid_invoices.ids)]
        })
        
        # Abrir el wizard
        return {
            'name': 'Descargar Facturas Individuales',
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice.download.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
    
    def ensure_invoice_pdf(self):
        """Asegura que la factura tiene un PDF adjunto, generándolo si es necesario"""
        self.ensure_one()
        
        # Buscar un adjunto PDF existente
        pdf_attachment = self.attachment_ids.filtered(
            lambda a: a.mimetype == 'application/pdf' and 
            (a.name.endswith('.pdf') or 'factura' in a.name.lower() or (self.name and self.name in a.name))
        )
        
        if pdf_attachment:
            return pdf_attachment[0]
        
        # Generar PDF si no existe
        try:
            # Obtener el reporte correcto según el tipo de factura
            if self.move_type in ('out_invoice', 'out_refund'):
                report_xml_id = 'account.account_invoices'
            else:
                report_xml_id = 'account.account_invoices_without_payment'
            
            # Usar la API correcta de Odoo 17 para generar PDFs
            report_action = self.env.ref(report_xml_id)
            report = self.env['ir.actions.report']._get_report_from_name(report_action.report_name)
            pdf_content, _ = report._render_qweb_pdf(self.id)
            
            # Crear el adjunto
            attachment_vals = {
                'name': f"{self.name or 'Factura'}.pdf",
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.move',
                'res_id': self.id,
                'mimetype': 'application/pdf',
            }
            return self.env['ir.attachment'].create(attachment_vals)
        except Exception as e:
            _logger.error(f"Error al generar PDF para factura {self.id}: {str(e)}")
            return False
