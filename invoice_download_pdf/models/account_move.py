from odoo import SUPERUSER_ID
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
            lambda a: a.mimetype == 'application/pdf'
        )
        
        if pdf_attachment:
            return pdf_attachment[0]
        
        # Generar PDF si no existe
        try:
            # Usar una impresión directa con el usuario administrador para evitar problemas de autenticación
            # Esto garantiza que tengamos los permisos necesarios para acceder a todos los recursos
            return self.sudo().with_context(force_report_rendering=True)._generate_pdf_and_attach()
        except Exception as e:
            _logger.error(f"Error al generar PDF para factura {self.id}: {str(e)}")
            return False

    def _generate_pdf_and_attach(self):
        """Método auxiliar para generar el PDF y adjuntarlo a la factura"""
        self.ensure_one()
        
        # Determinar el nombre correcto del reporte según el tipo de factura
        if self.move_type in ('out_invoice', 'out_refund'):
            report_name = 'account.report_invoice'
        else:
            report_name = 'account.report_invoice'  # Usar el mismo para facturas de proveedor
        
        # Preparar el contexto adecuado para la generación del PDF
        context = dict(self.env.context)
        context.update({
            'active_model': 'account.move',
            'active_id': self.id,
            'active_ids': [self.id],
            'default_model': 'account.move',
            'default_res_id': self.id,
            'model': 'account.move',
            'res_id': self.id,
            'force_web_access': True,  # Forzar acceso web para evitar problemas de autenticación
            'uid': SUPERUSER_ID,  # Usar el superusuario para evitar problemas de permisos
        })
        
        # Obtener la acción de reporte
        report_action = self.env.ref(report_name).with_context(context).report_action(self)
        report_action['close_on_report_download'] = False
        
        # Generar el PDF
        pdf_content = self.env['ir.actions.report'].with_context(context)._render_qweb_pdf(report_name, [self.id])[0]
        
        # Crear el adjunto
        attachment_vals = {
            'name': f"{self.name or 'Factura'}.pdf",
            'datas': base64.b64encode(pdf_content),
            'res_model': 'account.move',
            'res_id': self.id,
            'mimetype': 'application/pdf',
            # Asegurar que el adjunto está vinculado correctamente
            'type': 'binary',
        }
        attachment = self.env['ir.attachment'].create(attachment_vals)
        
        return attachment
