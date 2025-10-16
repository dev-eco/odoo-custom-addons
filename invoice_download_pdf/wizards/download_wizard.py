from odoo import models, api, fields
from odoo.exceptions import UserError
import base64
import logging
import io
import zipfile

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
                    # Asegurar que la factura tenga un PDF adjunto
                    pdf_attachment = invoice.ensure_invoice_pdf()
                    
                    if pdf_attachment:
                        # Crear línea de descarga
                        self.env['account.invoice.download.line'].create({
                            'wizard_id': wizard.id,
                            'invoice_id': invoice.id,
                            'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                            'attachment_id': pdf_attachment.id,
                        })
                    else:
                        # Crear línea sin adjunto para informar al usuario
                        self.env['account.invoice.download.line'].create({
                            'wizard_id': wizard.id,
                            'invoice_id': invoice.id,
                            'name': f"{invoice.name or f'Factura-{invoice.id}'}.pdf",
                            'attachment_id': False,
                            'state': 'error',
                            'notes': 'No se pudo generar el PDF',
                        })
        
        return records
    
    def action_download_all(self):
        """Permite descargar todas las facturas como archivos individuales"""
        # Verificar que hay líneas válidas para descargar
        valid_lines = self.download_line_ids.filtered(lambda l: l.attachment_id)
        
        if not valid_lines:
            raise UserError('No hay facturas con PDF disponible para descargar')
        
        if len(valid_lines) == 1:
            # Si solo hay una factura, la descargamos directamente
            return valid_lines[0].action_download()
            
        # Para múltiples facturas, creamos una página HTML con enlaces
        html_content = """
        <html>
        <head>
            <title>Descarga de Facturas</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #4c4c4c; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .download-link { color: #1a73e8; text-decoration: none; }
                .download-link:hover { text-decoration: underline; }
            </style>
            <script>
                // Esta función descarga automáticamente todas las facturas
                function downloadAll() {
                    var links = document.querySelectorAll('.download-link');
                    var delay = 1000; // 1 segundo entre descargas
                    
                    links.forEach(function(link, index) {
                        setTimeout(function() {
                            link.click();
                        }, delay * index);
                    });
                }
                
                // Iniciar la descarga automáticamente después de cargar la página
                window.onload = function() {
                    downloadAll();
                }
            </script>
        </head>
        <body>
            <h1>Descarga de Facturas</h1>
            <p>Se iniciarán las descargas automáticamente. Si algún archivo no se descarga, haga clic en el enlace correspondiente.</p>
            <table>
                <tr>
                    <th>Nombre</th>
                    <th>Cliente/Proveedor</th>
                    <th>Fecha</th>
                    <th>Importe</th>
                    <th>Descargar</th>
                </tr>
        """
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        for line in valid_lines:
            download_url = f"{base_url}/web/content/{line.attachment_id.id}?download=true"
            html_content += f"""
                <tr>
                    <td>{line.name}</td>
                    <td>{line.invoice_id.partner_id.name}</td>
                    <td>{line.invoice_id.invoice_date or ''}</td>
                    <td>{line.invoice_id.amount_total} {line.invoice_id.currency_id.name}</td>
                    <td><a href="{download_url}" class="download-link" target="_blank">Descargar</a></td>
                </tr>
            """
            
        html_content += """
            </table>
        </body>
        </html>
        """
        
        # Crear un adjunto con la página HTML
        attachment_vals = {
            'name': 'descargar_facturas.html',
            'datas': base64.b64encode(html_content.encode('utf-8')),
            'mimetype': 'text/html',
        }
        
        attachment = self.env['ir.attachment'].create(attachment_vals)
        
        # Devolver acción para abrir la página HTML
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=true",
            'target': 'self',
        }

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
            # Si no tiene adjunto, intentar generarlo nuevamente
            pdf_attachment = self.invoice_id.ensure_invoice_pdf()
            if pdf_attachment:
                self.attachment_id = pdf_attachment
            else:
                raise UserError('No se pudo generar el PDF para esta factura')
        
        # Devolvemos una acción para descargar el archivo
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }
