# models/res_config_settings.py
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Configuración general
    document_automation_enabled = fields.Boolean(
        "Activar automatización documental",
        help="Activa el procesamiento automático de documentos"
    )
    
    # Configuración de correo electrónico
    document_scan_email_enabled = fields.Boolean(
        "Procesar correos",
        help="Procesa automáticamente documentos recibidos por correo"
    )
    
    document_email_whitelist = fields.Text(
        "Lista blanca de correos",
        help="Direcciones de correo separadas por comas"
    )
    
    document_allowed_domains = fields.Text(
        "Dominios permitidos",
        help="Dominios de correo separados por comas"
    )
    
    # Configuración de OCR
    document_ocr_enabled = fields.Boolean(
        "Activar OCR",
        help="Utiliza OCR para extraer texto de documentos escaneados"
    )
    
    document_ocr_languages = fields.Char(
        "Idiomas OCR",
        help="Códigos de idioma para OCR (ej: spa+eng)",
        default="spa+eng"
    )
    
    # Configuración de carpeta vigilada
    document_watch_folder_enabled = fields.Boolean(
        "Vigilar carpeta",
        help="Monitoriza una carpeta para procesar documentos automáticamente"
    )
    
    document_watch_folder_path = fields.Char(
        "Ruta de carpeta vigilada",
        help="Ruta absoluta a la carpeta que será monitoreada"
    )
    
     document_automation_enabled = fields.Boolean(
        "Activar automatización documental",
        config_parameter='document_automation.enabled'
    )
    
    document_ocr_enabled = fields.Boolean(
        "Activar OCR",
        config_parameter='document_automation.ocr_enabled',
        default=True
    )
    
    document_ocr_languages = fields.Char(
        "Idiomas OCR",
        config_parameter='document_automation.ocr_languages',
        default="spa+eng"
    )
    
    # Nuevos campos para Gemini
    gemini_api_key = fields.Char(
        'Gemini API Key', 
        config_parameter='document_automation.gemini_api_key'
    )
    
    default_extraction_method = fields.Selection([
        ('tesseract_only', 'Solo Tesseract'),
        ('tesseract_gemini', 'Tesseract + Gemini AI'),
        ('gemini_direct', 'Gemini AI directo')
    ], string="Método de extracción predeterminado", 
       default='tesseract_gemini',
       config_parameter='document_automation.default_extraction_method')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        # Recuperar valores almacenados
        res.update(
            document_automation_enabled=ICPSudo.get_param('document_automation.enabled', 'False') == 'True',
            document_scan_email_enabled=ICPSudo.get_param('document_automation.scan_email_enabled', 'False') == 'True',
            document_email_whitelist=ICPSudo.get_param('document_automation.email_whitelist', ''),
            document_allowed_domains=ICPSudo.get_param('document_automation.allowed_domains', ''),
            document_ocr_enabled=ICPSudo.get_param('document_automation.ocr_enabled', 'True') == 'True',
            document_ocr_languages=ICPSudo.get_param('document_automation.ocr_languages', 'spa+eng'),
            document_watch_folder_enabled=ICPSudo.get_param('document_automation.watch_folder_enabled', 'False') == 'True',
            document_watch_folder_path=ICPSudo.get_param('document_automation.watch_folder_path', ''),
        )
        
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        
        # Almacenar valores
        ICPSudo.set_param('document_automation.enabled', str(self.document_automation_enabled))
        ICPSudo.set_param('document_automation.scan_email_enabled', str(self.document_scan_email_enabled))
        ICPSudo.set_param('document_automation.email_whitelist', self.document_email_whitelist or '')
        ICPSudo.set_param('document_automation.allowed_domains', self.document_allowed_domains or '')
        ICPSudo.set_param('document_automation.ocr_enabled', str(self.document_ocr_enabled))
        ICPSudo.set_param('document_automation.ocr_languages', self.document_ocr_languages or 'spa+eng')
        ICPSudo.set_param('document_automation.watch_folder_enabled', str(self.document_watch_folder_enabled))
        ICPSudo.set_param('document_automation.watch_folder_path', self.document_watch_folder_path or '')
