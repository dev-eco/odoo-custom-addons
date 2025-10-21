# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import re
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ExportTemplate(models.Model):
    """
    Plantillas de Nomenclatura para Exportación de Facturas
    
    Este modelo permite definir patrones personalizables para generar
    nombres de archivo durante la exportación masiva. Cada empresa puede
    tener múltiples plantillas para diferentes propósitos.
    
    Variables disponibles en las plantillas:
    - {type}: Tipo de documento (CLIENTE, PROVEEDOR, NC_CLIENTE, NC_PROVEEDOR)
    - {number}: Número de la factura
    - {partner}: Nombre del partner sanitizado
    - {date}: Fecha de la factura (YYYY-MM-DD)
    - {year}: Año de la factura (YYYY)
    - {month}: Mes de la factura (MM)
    - {company}: Nombre de la empresa
    - {reference}: Referencia del partner (si existe)
    """
    
    _name = 'export.template'
    _description = 'Plantilla de Nomenclatura para Exportación'
    _order = 'company_id, sequence, name'
    _check_company_auto = True
    
    # CAMPOS BÁSICOS
    # ==============
    name = fields.Char(
        string='Nombre de la Plantilla',
        required=True,
        help='Nombre descriptivo para identificar esta plantilla'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Desmarcar para deshabilitar esta plantilla sin eliminarla'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        help='Empresa a la que pertenece esta plantilla'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aparición en las listas de selección'
    )
    
    # CONFIGURACIÓN DE LA PLANTILLA
    # =============================
    pattern = fields.Char(
        string='Patrón de Nomenclatura',
        required=True,
        default='{type}_{number}_{partner}_{date}.pdf',
        help='Patrón para generar nombres de archivo. '
             'Variables disponibles: {type}, {number}, {partner}, {date}, '
             '{year}, {month}, {company}, {reference}'
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción detallada del propósito de esta plantilla'
    )
    
    # EJEMPLOS Y VALIDACIONES
    # ======================
    example_output = fields.Char(
        string='Ejemplo de Salida',
        compute='_compute_example_output',
        help='Ejemplo de cómo se vería un archivo generado con esta plantilla'
    )
    
    is_default = fields.Boolean(
        string='Plantilla por Defecto',
        help='Marca esta plantilla como la predeterminada para la empresa'
    )
    
    # ESTADÍSTICAS DE USO
    # ==================
    usage_count = fields.Integer(
        string='Veces Utilizada',
        default=0,
        readonly=True,
        help='Número de veces que se ha usado esta plantilla'
    )
    
    last_used = fields.Datetime(
        string='Último Uso',
        readonly=True,
        help='Última vez que se utilizó esta plantilla'
    )

    # CONSTRAINTS Y VALIDACIONES
    # ==========================
    @api.constrains('pattern')
    def _check_pattern_validity(self):
        """Validar que el patrón contenga variables válidas"""
        valid_variables = {
            'type', 'number', 'partner', 'date', 
            'year', 'month', 'company', 'reference'
        }
        
        for record in self:
            if not record.pattern:
                continue
                
            # Extraer variables del patrón usando regex
            variables_in_pattern = set(re.findall(r'\{(\w+)\}', record.pattern))
            
            # Verificar variables inválidas
            invalid_variables = variables_in_pattern - valid_variables
            if invalid_variables:
                raise ValidationError(_(
                    "Variables inválidas en el patrón: %s\n"
                    "Variables válidas: %s"
                ) % (
                    ', '.join(invalid_variables),
                    ', '.join(sorted(valid_variables))
                ))
            
            # Verificar que contenga al menos {number}
            if 'number' not in variables_in_pattern:
                raise ValidationError(_(
                    "El patrón debe incluir al menos la variable {number} "
                    "para asegurar nombres únicos"
                ))

    @api.constrains('is_default', 'company_id')
    def _check_single_default_per_company(self):
        """Asegurar que solo hay una plantilla por defecto por empresa"""
        for record in self:
            if record.is_default:
                existing_default = self.search([
                    ('company_id', '=', record.company_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', record.id)
                ])
                if existing_default:
                    raise ValidationError(_(
                        "Ya existe una plantilla por defecto para la empresa %s: %s"
                    ) % (record.company_id.name, existing_default.name))

    # MÉTODOS COMPUTADOS
    # ==================
    @api.depends('pattern')
    def _compute_example_output(self):
        """Generar ejemplo de salida basado en el patrón"""
        for record in self:
            if not record.pattern:
                record.example_output = ''
                continue
            
            # Datos de ejemplo
            example_data = {
                'type': 'CLIENTE',
                'number': 'INV-2024-001',
                'partner': 'ACME_CORP',
                'date': '2024-01-15',
                'year': '2024',
                'month': '01',
                'company': 'MI_EMPRESA',
                'reference': 'REF-123'
            }
            
            try:
                record.example_output = record.pattern.format(**example_data)
            except KeyError as e:
                record.example_output = f"Error: Variable {e} no válida"
            except Exception:
                record.example_output = "Error en el patrón"

    # MÉTODOS DE ACCIÓN
    # ================
    def generate_filename(self, invoice):
        """
        Generar nombre de archivo para una factura específica
        
        Args:
            invoice (account.move): Registro de factura
            
        Returns:
            str: Nombre de archivo generado
        """
        self.ensure_one()
        
        # Preparar datos para la plantilla
        template_data = self._prepare_template_data(invoice)
        
        try:
            # Generar nombre usando la plantilla
            filename = self.pattern.format(**template_data)
            
            # Sanitizar caracteres problemáticos
            filename = self._sanitize_filename(filename)
            
            # Actualizar estadísticas de uso
            self._update_usage_stats()
            
            return filename
            
        except Exception as e:
            _logger.error(f"Error generando nombre de archivo: {str(e)}")
            # Fallback a patrón básico
            return f"{template_data['type']}_{template_data['number']}.pdf"

    def _prepare_template_data(self, invoice):
        """Preparar datos para usar en la plantilla"""
        # Determinar tipo de documento
        doc_type = self._get_document_type(invoice)
        
        # Sanitizar nombre del partner
        partner_name = self._sanitize_filename(
            invoice.partner_id.name or 'SIN_NOMBRE'
        )
        
        # Formatear fecha
        invoice_date = invoice.invoice_date or fields.Date.today()
        
        return {
            'type': doc_type,
            'number': self._sanitize_filename(invoice.name or 'SIN_NUMERO'),
            'partner': partner_name,
            'date': invoice_date.strftime('%Y-%m-%d'),
            'year': invoice_date.strftime('%Y'),
            'month': invoice_date.strftime('%m'),
            'company': self._sanitize_filename(invoice.company_id.name),
            'reference': self._sanitize_filename(
                invoice.partner_id.ref or 'SIN_REF'
            ),
        }

    def _get_document_type(self, invoice):
        """Determinar tipo de documento"""
        if invoice.move_type == 'out_invoice':
            return 'CLIENTE'
        elif invoice.move_type == 'out_refund':
            return 'NC_CLIENTE'
        elif invoice.move_type == 'in_invoice':
            return 'PROVEEDOR'
        elif invoice.move_type == 'in_refund':
            return 'NC_PROVEEDOR'
        else:
            return 'DOCUMENTO'

    def _sanitize_filename(self, filename):
        """Sanitizar nombre de archivo eliminando caracteres problemáticos"""
        if not filename:
            return 'VACIO'
        
        # Reemplazar caracteres problemáticos
        filename = re.sub(r'[/\\:*?"<>|]', '_', str(filename))
        
        # Reemplazar espacios múltiples con uno solo
        filename = re.sub(r'\s+', '_', filename)
        
        # Remover guiones bajos múltiples
        filename = re.sub(r'_+', '_', filename)
        
        # Remover guiones bajos al inicio y final
        filename = filename.strip('_')
        
        # Limitar longitud (Windows tiene límite de 255 caracteres)
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename or 'ARCHIVO'

    def _update_usage_stats(self):
        """Actualizar estadísticas de uso"""
        self.sudo().write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now(),
        })

    # MÉTODOS DE ACCIÓN PARA LA INTERFAZ
    # =================================
    def action_test_template(self):
        """Acción para probar la plantilla con una factura real"""
        self.ensure_one()
        
        # Buscar una factura de ejemplo
        example_invoice = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted')
        ], limit=1)
        
        if not example_invoice:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin facturas'),
                    'message': _('No se encontraron facturas para probar la plantilla'),
                    'type': 'warning',
                }
            }
        
        # Generar nombre de ejemplo
        example_filename = self.generate_filename(example_invoice)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Plantilla probada'),
                'message': _(
                    'Ejemplo con factura %s:\n%s'
                ) % (example_invoice.name, example_filename),
                'type': 'success',
            }
        }

    @api.model
    def get_default_template(self, company_id=None):
        """Obtener plantilla por defecto para una empresa"""
        company_id = company_id or self.env.company.id
        
        default_template = self.search([
            ('company_id', '=', company_id),
            ('is_default', '=', True),
            ('active', '=', True)
        ], limit=1)
        
        if not default_template:
            # Crear plantilla por defecto si no existe
            default_template = self.create({
                'name': 'Plantilla Estándar',
                'pattern': '{type}_{number}_{partner}_{date}.pdf',
                'description': 'Plantilla por defecto del sistema',
                'company_id': company_id,
                'is_default': True,
            })
        
        return default_template
