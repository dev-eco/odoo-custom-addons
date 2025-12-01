# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    bulk_export_default_format = fields.Selection([
        ('zip', 'ZIP'),
        ('zip_password', 'ZIP con Contraseña'),
        ('tar_gz', 'TAR.GZ'),
        ('tar_bz2', 'TAR.BZ2'),
    ], string='Formato por Defecto', default='zip',
       config_parameter='account_invoice_bulk_export.default_format')
    
    bulk_export_default_pattern = fields.Selection([
        ('standard', 'Tipo_Número_Partner_Fecha'),
        ('date_first', 'Fecha_Tipo_Número_Partner'),
        ('partner_first', 'Partner_Tipo_Número_Fecha'),
        ('simple', 'Tipo_Número_Fecha'),
    ], string='Patrón de Nombres por Defecto', default='standard',
       config_parameter='account_invoice_bulk_export.default_pattern')
    
    bulk_export_default_batch_size = fields.Integer(
        string='Tamaño de Lote por Defecto',
        default=50,
        config_parameter='account_invoice_bulk_export.default_batch_size'
    )
    
    bulk_export_include_xml = fields.Boolean(
        string='Incluir XML por Defecto',
        default=False,
        config_parameter='account_invoice_bulk_export.include_xml'
    )
