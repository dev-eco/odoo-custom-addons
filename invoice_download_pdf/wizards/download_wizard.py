from odoo import models, api, fields
from odoo import SUPERUSER_ID  # Añadir esta importación
from odoo.exceptions import UserError
import subprocess
import tempfile
import os
import base64
import logging
import io
import zipfile
import requests

_logger = logging.getLogger(__name__)

class AccountInvoiceDownloadWizard(models.TransientModel):
    _name = 'account.invoice.download.wizard'
    _description = 'Asistente para descargar facturas individuales'
    
    invoice_ids = fields.Many2many('account.move', string='Facturas')
    download_line_ids = fields.One2many(
        'account.invoice.download.line', 
        'wizard_id', 
        string='Facturas para descargar'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribe el método create para generar las líneas de descarga"""
        records = super(AccountInvoiceDownloadWizard, self).create(vals_list)
        
        # Procesamos cada registro creado
        for wizard in records:
            if wizard.invoice_ids:
                # Generar líneas para cada factura seleccionada
                for invoice in wizard.invoice_ids:
                    # Intentamos encontrar el PDF adjunto o generarlo
                    pdf_data = None
                    
                    # 1. Buscar un adjunto PDF existente
                    pdf_attachment = invoice.attachment_ids.filtered(
                        lambda a: a.mimetype == 'application/pdf'
                    )
                    
                    if pdf_attachment:
                        pdf_data = pdf_attachment[0]
                    else:
                        # 2. Si no existe, intentar generarlo
                        try:
                            # Usar el método estándar de impresión de facturas
                            pdf_data = self._generate_invoice_pdf(invoice)
                        except Exception as e:
                            _logger.error(f"Error generando PDF para factura {invoice.id}: {str(e)}")
                    
                    # Crear la línea de descarga
                    line_vals = {
                        'wizard_id': wizard.id,
                        'invoice_id': invoice.id,
                        'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                        'state': 'valid' if pdf_data else 'error',
                    }
                    
                    if pdf_data:
                        line_vals['attachment_id'] = pdf_data.id
                    else:
                        line_vals['notes'] = 'No se pudo generar el PDF'
                    
                    self.env['account.invoice.download.line'].create(line_vals)
        
        return records

    def _find_matching_pdf_attachment(self, invoice):
        """Encuentra un adjunto PDF que coincida con la factura, considerando variaciones en el nombre"""
        # 1. Buscar primero por MIME type
        pdf_attachments = invoice.attachment_ids.filtered(
            lambda a: a.mimetype == 'application/pdf'
        )
        
        if not pdf_attachments:
            return False
        
        # Si solo hay un PDF, lo usamos directamente
        if len(pdf_attachments) == 1:
            return pdf_attachments[0]
        
        # 2. Si hay varios PDFs, intentamos encontrar uno que coincida con el nombre de la factura
        if invoice.name:
            # Normalizar el nombre de la factura (quitar caracteres especiales)
            normalized_name = invoice.name.replace('/', '_').replace('\\', '_').replace(' ', '_')
            
            for attachment in pdf_attachments:
                # Normalizar el nombre del adjunto
                normalized_attachment_name = attachment.name.replace('/', '_').replace('\\', '_').replace(' ', '_')
                
                # Verificar si el nombre normalizado de la factura está en el nombre normalizado del adjunto
                if normalized_name in normalized_attachment_name:
                    return attachment
        
        # 3. Si no encontramos una coincidencia específica, devolvemos el primer PDF
        return pdf_attachments[0]

    def _generate_invoice_pdf(self, invoice):
        """Genera o recupera el PDF para una factura priorizando adjuntos existentes"""
        try:
            # 1. BUSCAR PRIMERO SI YA EXISTE UN PDF ADJUNTO
            existing_pdf = self._find_matching_pdf_attachment(invoice)
            
            if existing_pdf:
                _logger.info(f"Usando PDF existente para factura {invoice.id}: {existing_pdf.name}")
                return existing_pdf
            
            # 2. USAR EL MÉTODO DIRECTO CON EL INFORME IDENTIFICADO
            try:
                _logger.info(f"Intentando usar método directo con informe para factura {invoice.id}")
                
                # Buscar informes disponibles
                reports = self.env['ir.actions.report'].sudo().search([
                    ('model', '=', 'account.move'),
                    ('report_type', '=', 'qweb-pdf'),
                ], limit=5)
                
                if reports:
                    # Registrar los informes disponibles para diagnóstico
                    for report in reports:
                        _logger.info(f"Informe disponible: {report.name} (ID: {report.id})")
                    
                    # Seleccionar el informe correcto según el tipo de factura
                    selected_report = None
                    for report in reports:
                        if invoice.move_type in ('out_invoice', 'out_refund') and ('factura' in report.name.lower() or 'invoice' in report.name.lower()):
                            selected_report = report
                            break
                    
                    # Si no encontramos un informe específico, usamos el primero
                    if not selected_report:
                        selected_report = reports[0]
                    
                    _logger.info(f"Usando informe: {selected_report.name}")
                    
                    # Generar el PDF - NOTA: Aquí hay que tener cuidado con el formato de los IDs
                    ctx = self.env.context.copy()
                    ctx.update({
                        'active_model': 'account.move',
                        'active_ids': [invoice.id],
                        'active_id': invoice.id
                    })
                    
                    # Intentar diferentes métodos de generación
                    try:
                        # Método 1: Usando _render con lista de IDs
                        _logger.info("Intentando método _render con lista de IDs")
                        pdf_content = selected_report.with_context(ctx)._render([invoice.id])[0]
                    except Exception as e:
                        _logger.warning(f"Error con método _render: {str(e)}")
                        
                        try:
                            # Método 2: Usando _render_qweb_pdf
                            _logger.info("Intentando método _render_qweb_pdf")
                            pdf_content = selected_report.with_context(ctx)._render_qweb_pdf([invoice.id])[0]
                        except Exception as e2:
                            _logger.warning(f"Error con método _render_qweb_pdf: {str(e2)}")
                            
                            # Método 3: Generación directa - último intento
                            _logger.info("Intentando método de generación directa")
                            report_service = self.env['ir.actions.report']
                            pdf_content = report_service._get_report_from_name('account.report_invoice').render_qweb_pdf([invoice.id])[0]
                    
                    # Si llegamos aquí, tenemos contenido PDF
                    _logger.info(f"PDF generado correctamente para factura {invoice.id}")
                    
                    # Crear adjunto
                    attachment_vals = {
                        'name': f"{invoice.name or 'Factura'}.pdf",
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'mimetype': 'application/pdf',
                    }
                    return self.env['ir.attachment'].create(attachment_vals)
            except Exception as e:
                _logger.error(f"Error con método directo: {str(e)}")
            
            # 3. SI TODO LO ANTERIOR FALLA, CREAR UN PDF BÁSICO
            _logger.info(f"Generando PDF básico para factura {invoice.id}")
            return self._create_basic_pdf(invoice)
            
        except Exception as e:
            _logger.error(f"Error general en _generate_invoice_pdf: {str(e)}")
            return self._create_basic_pdf(invoice)

    def _create_basic_pdf(self, invoice):
        """Crea un PDF básico con información de la factura cuando todo lo demás falla"""
        # Crear un contenido HTML básico
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #1a73e8; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .total {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>FACTURA {invoice.name or ''}</h1>
            <p><strong>Cliente:</strong> {invoice.partner_id.name or 'N/A'}</p>
            <p><strong>Fecha:</strong> {invoice.invoice_date or 'N/A'}</p>
            <p><strong>Referencia:</strong> {invoice.ref or 'N/A'}</p>
            
            <table>
                <tr>
                    <th>Descripción</th>
                    <th>Cantidad</th>
                    <th>Precio</th>
                    <th>Subtotal</th>
                </tr>
        """
        
        # Añadir líneas de factura
        for line in invoice.invoice_line_ids:
            html_content += f"""
                <tr>
                    <td>{line.name or 'N/A'}</td>
                    <td>{line.quantity or 0}</td>
                    <td>{line.price_unit or 0} {invoice.currency_id.name or ''}</td>
                    <td>{line.price_subtotal or 0} {invoice.currency_id.name or ''}</td>
                </tr>
            """
        
        # Añadir totales
        html_content += f"""
                <tr class="total">
                    <td colspan="3">Total</td>
                    <td>{invoice.amount_total or 0} {invoice.currency_id.name or ''}</td>
                </tr>
            </table>
            
            <p>Este documento es una representación básica de la factura. Para obtener la versión oficial, contacte con la empresa.</p>
        </body>
        </html>
        """
        
        # Convertir HTML a PDF
        try:
            pdf_content = self.html_to_pdf(html_content)
            
            # Crear el adjunto
            attachment_vals = {
                'name': f"{invoice.name or 'Factura'}.pdf",
                'datas': base64.b64encode(pdf_content),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'application/pdf',
            }
            return self.env['ir.attachment'].create(attachment_vals)
        except:
            # Si no podemos generar el PDF, al menos creamos un adjunto con el HTML
            attachment_vals = {
                'name': f"{invoice.name or 'Factura'}.html",
                'datas': base64.b64encode(html_content.encode('utf-8')),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'mimetype': 'text/html',
            }
            return self.env['ir.attachment'].create(attachment_vals)

    def html_to_pdf(self, html_content):
        """Convierte contenido HTML a PDF usando wkhtmltopdf"""
        # Importaciones necesarias
        import subprocess
        import tempfile
        import os
        
        # Crear archivos temporales
        html_fd, html_path = tempfile.mkstemp(suffix='.html')
        pdf_fd, pdf_path = tempfile.mkstemp(suffix='.pdf')
        
        try:
            # Escribir el contenido HTML en el archivo temporal
            with os.fdopen(html_fd, 'w') as f:
                f.write(html_content)
            
            # Convertir HTML a PDF usando wkhtmltopdf
            process = subprocess.Popen(
                ['wkhtmltopdf', '--quiet', html_path, pdf_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            out, err = process.communicate()
            
            # Leer el contenido del PDF generado
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
                
            return pdf_content
        finally:
            # Eliminar archivos temporales
            try:
                os.unlink(html_path)
                os.unlink(pdf_path)
            except:
                pass
    
    def action_download_all(self):
        """Descarga todas las facturas en un archivo ZIP"""
        # Verificar que hay líneas válidas para descargar
        valid_lines = self.download_line_ids.filtered(lambda l: l.attachment_id and l.state == 'valid')
        
        if not valid_lines:
            raise UserError('No hay facturas con PDF disponible para descargar')
        
        if len(valid_lines) == 1:
            # Si solo hay una factura, la descargamos directamente
            return valid_lines[0].action_download()
        
        # Para múltiples facturas, crear un archivo ZIP
        zip_buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for line in valid_lines:
                    try:
                        # Obtener el contenido del PDF
                        pdf_content = base64.b64decode(line.attachment_id.datas)
                        
                        # Crear un nombre de archivo limpio
                        clean_name = line.name.replace('/', '_').replace('\\', '_')
                        if not clean_name.lower().endswith('.pdf'):
                            clean_name += '.pdf'
                            
                        # Añadir el PDF al archivo ZIP
                        zip_file.writestr(clean_name, pdf_content)
                    except Exception as e:
                        _logger.error(f"Error al procesar factura {line.invoice_id.id} para ZIP: {str(e)}")
                        continue
            
            # Crear un nombre para el archivo ZIP
            company_name = self.env.user.company_id.name or 'company'
            today = fields.Date.today().strftime('%Y%m%d')
            zip_name = f"facturas_{company_name}_{today}.zip"
            zip_name = zip_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            
            # Crear un adjunto con el archivo ZIP
            attachment_vals = {
                'name': zip_name,
                'datas': base64.b64encode(zip_buffer.getvalue()),
                'mimetype': 'application/zip',
            }
            
            attachment = self.env['ir.attachment'].create(attachment_vals)
            
            # Devolver acción para descargar el archivo ZIP
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{attachment.id}?download=true",
                'target': 'self',
            }
        except Exception as e:
            _logger.error(f"Error al crear archivo ZIP: {str(e)}")
            raise UserError(f"Error al crear archivo ZIP: {str(e)}")


class AccountInvoiceDownloadLine(models.TransientModel):
    _name = 'account.invoice.download.line'
    _description = 'Línea de descarga de factura individual'
    
    wizard_id = fields.Many2one('account.invoice.download.wizard', string='Wizard')
    invoice_id = fields.Many2one('account.move', string='Factura', required=True)
    name = fields.Char('Nombre del archivo', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Adjunto PDF')
    company_id = fields.Many2one(related='invoice_id.company_id')
    partner_id = fields.Many2one(related='invoice_id.partner_id')
    invoice_date = fields.Date(related='invoice_id.invoice_date')
    amount_total = fields.Monetary(related='invoice_id.amount_total')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    state = fields.Selection([
        ('valid', 'Válido'),
        ('error', 'Error'),
    ], string='Estado', default='valid')
    notes = fields.Text('Notas')
    
    def action_download(self):
        """Descargar el PDF individualmente"""
        self.ensure_one()
        
        if not self.attachment_id:
            raise UserError('No se pudo generar el PDF para esta factura')
        
        # Devolvemos una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
