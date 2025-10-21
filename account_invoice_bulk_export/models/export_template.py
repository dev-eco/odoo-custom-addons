# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import re
import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class ExportTemplate(models.Model):
    """
    Plantillas de Nomenclatura para Exportación de Facturas
    
    Este modelo permite a las empresas definir patrones personalizables para generar
    nombres de archivo durante la exportación masiva. Cada empresa puede tener múltiples
    plantillas para diferentes propósitos (contadores, auditores, clientes, etc.).
    
    Conceptos clave:
    ===============
    
    Variables de Plantilla:
    ----------------------
    Las plantillas usan un sistema de variables entre llaves {} que se reemplazan
    automáticamente con datos reales de cada factura:
    
    • {type}     - Tipo de documento (CLIENTE, PROVEEDOR, NC_CLIENTE, NC_PROVEEDOR)
    • {number}   - Número de la factura (sanitizado para nombres de archivo)
    • {partner}  - Nombre del partner (limpio, sin caracteres especiales)
    • {date}     - Fecha de la factura en formato YYYY-MM-DD
    • {year}     - Año de la factura (YYYY)
    • {month}    - Mes de la factura (MM)
    • {company}  - Nombre de la empresa (sanitizado)
    • {reference}- Referencia del partner (si existe)
    
    Ejemplos de patrones:
    • '{type}_{number}_{partner}_{date}.pdf'
    • 'facturas_{year}/{month}/{type}_{number}.pdf'
    • '{company}_{date}_{type}_{number}_{partner}.pdf'
    
    Lógica de Negocio:
    =================
    
    • Cada empresa puede tener múltiples plantillas activas
    • Solo una plantilla por empresa puede estar marcada como "por defecto"
    • Las plantillas inactivas se conservan pero no aparecen en listas
    • La validación del patrón ocurre al guardar para detectar errores temprano
    """
    
    # DEFINICIÓN DEL MODELO
    # ====================
    _name = 'export.template'
    _description = 'Plantilla de Nomenclatura para Exportación de Facturas'
    _order = 'company_id, sequence, name'
    _check_company_auto = True  # Seguridad automática multi-empresa
    _rec_name = 'name'          # Campo que aparece en las relaciones Many2one
    
    # CAMPOS BÁSICOS
    # ==============
    name = fields.Char(
        string='Nombre de la Plantilla',
        required=True,
        size=100,  # Limitar tamaño para evitar nombres excesivamente largos
        help='Nombre descriptivo para identificar esta plantilla en listas de selección'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Desmarcar para deshabilitar esta plantilla sin eliminarla. '
             'Las plantillas inactivas no aparecen en las listas de selección.'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',  # Si se elimina la empresa, eliminar sus plantillas
        help='Empresa a la que pertenece esta plantilla'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Controla el orden de aparición en las listas de selección. '
             'Números menores aparecen primero.'
    )
    
    # CONFIGURACIÓN DE LA PLANTILLA
    # =============================
    pattern = fields.Char(
        string='Patrón de Nomenclatura',
        required=True,
        default='{type}_{number}_{partner}_{date}.pdf',
        size=200,
        help='Patrón para generar nombres de archivo. Variables disponibles: '
             '{type}, {number}, {partner}, {date}, {year}, {month}, {company}, {reference}'
    )
    
    is_default = fields.Boolean(
        string='Plantilla Predeterminada',
        default=False,
        help='Marcar como plantilla por defecto para esta empresa. '
             'Solo puede haber una plantilla por defecto por empresa.'
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción opcional del propósito de esta plantilla '
             '(ej: "Para envío a contador", "Para archivo interno")'
    )
    
    # CAMPOS COMPUTADOS Y ESTADÍSTICAS
    # ================================
    usage_count = fields.Integer(
        string='Veces Utilizada',
        default=0,
        readonly=True,
        help='Número de veces que esta plantilla ha sido utilizada en exportaciones'
    )
    
    preview_example = fields.Char(
        string='Ejemplo de Nombre',
        compute='_compute_preview_example',
        store=False,  # No almacenar en BD, siempre recalcular
        help='Ejemplo de cómo se vería un nombre de archivo con esta plantilla'
    )
    
    @api.depends('pattern')
    def _compute_preview_example(self):
        """
        Generar un ejemplo de nombre de archivo usando datos ficticios.
        
        Este campo computed ayuda a los usuarios a visualizar cómo se verá
        el resultado final antes de usar la plantilla en una exportación real.
        
        Técnica utilizada:
        - Datos de ejemplo realistas pero ficticios
        - Sanitización aplicada igual que en exportación real  
        - Manejo de errores para patrones inválidos
        """
        for template in self:
            try:
                # Datos de ejemplo para la preview
                example_data = {
                    'type': 'CLIENTE',
                    'number': 'FACT-2025-0001',
                    'partner': 'Empresa_Ejemplo_SL',
                    'date': '2025-01-20',
                    'year': '2025',
                    'month': '01',
                    'company': template.company_id.name or 'Mi_Empresa',
                    'reference': 'REF001'
                }
                
                # Sanitizar datos igual que en exportación real
                for key, value in example_data.items():
                    if isinstance(value, str):
                        example_data[key] = self._sanitize_filename(value)
                
                # Generar ejemplo
                preview = template.pattern.format(**example_data)
                template.preview_example = preview
                
            except (KeyError, ValueError) as e:
                # Si el patrón tiene errores, mostrar mensaje descriptivo
                template.preview_example = f'Error en patrón: {str(e)}'
    
    # VALIDACIONES Y CONSTRAINS
    # =========================
    @api.constrains('pattern')
    def _check_pattern_validity(self):
        """
        Validar que el patrón de nomenclatura sea válido y seguro.
        
        Esta validación previene:
        1. Patrones con variables inexistentes
        2. Patrones que generarían nombres de archivo inválidos
        3. Patrones vacíos o solo con espacios
        4. Patrones con caracteres problemáticos para sistemas de archivos
        
        La validación ocurre en el momento del guardado, no durante la exportación,
        para detectar problemas temprano y dar feedback inmediato al usuario.
        """
        # Variables válidas que pueden usar las plantillas
        valid_variables = {
            'type', 'number', 'partner', 'date', 'year', 'month', 'company', 'reference'
        }
        
        for template in self:
            pattern = template.pattern.strip()
            
            # Verificar que el patrón no esté vacío
            if not pattern:
                raise ValidationError(_(
                    'El patrón de nomenclatura no puede estar vacío.'
                ))
            
            # Encontrar todas las variables en el patrón
            try:
                # Usar regex para encontrar todas las variables {variable}
                variables_found = set(re.findall(r'\{(\w+)\}', pattern))
            except re.error:
                raise ValidationError(_(
                    'El patrón contiene una expresión regular inválida.'
                ))
            
            # Verificar que todas las variables sean válidas
            invalid_variables = variables_found - valid_variables
            if invalid_variables:
                raise ValidationError(_(
                    'Variables inválidas en el patrón: %s. '
                    'Variables válidas: %s'
                ) % (', '.join(invalid_variables), ', '.join(valid_variables)))
            
            # Verificar que contenga al menos una variable
            if not variables_found:
                raise ValidationError(_(
                    'El patrón debe contener al menos una variable. '
                    'Variables disponibles: {type}, {number}, {partner}, {date}, {year}, {month}, {company}, {reference}'
                ))
            
            # Verificar caracteres problemáticos para nombres de archivo
            problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
            for char in problematic_chars:
                if char in pattern:
                    raise ValidationError(_(
                        'El patrón contiene el carácter problemático "%s" que no es válido '
                        'para nombres de archivo en algunos sistemas operativos.'
                    ) % char)
            
            # Probar el patrón con datos de ejemplo
            try:
                test_data = {var: 'test' for var in valid_variables}
                test_result = pattern.format(**test_data)
                
                # Verificar que el resultado no sea solo espacios
                if not test_result.strip():
                    raise ValidationError(_(
                        'El patrón genera nombres de archivo vacíos.'
                    ))
                    
            except (KeyError, ValueError) as e:
                raise ValidationError(_(
                    'Error al probar el patrón: %s'
                ) % str(e))
    
    @api.constrains('is_default', 'company_id', 'active')
    def _check_single_default_per_company(self):
        """
        Asegurar que solo haya una plantilla marcada como predeterminada por empresa.
        
        Esta validación mantiene la integridad de los datos y evita confusión
        sobre cuál plantilla usar cuando no se especifica una explícitamente.
        
        La validación se ejecuta a nivel de base de datos para prevenir condiciones
        de carrera en entornos multi-usuario.
        """
        for template in self.filtered('is_default'):
            # Buscar otras plantillas por defecto en la misma empresa
            other_defaults = self.search([
                ('company_id', '=', template.company_id.id),
                ('is_default', '=', True),
                ('active', '=', True),
                ('id', '!=', template.id)
            ])
            
            if other_defaults:
                raise ValidationError(_(
                    'Solo puede haber una plantilla predeterminada por empresa. '
                    'La empresa %s ya tiene la plantilla "%s" marcada como predeterminada.'
                ) % (template.company_id.name, other_defaults[0].name))
    
    # MÉTODOS DE CREACIÓN Y ESCRITURA
    # ===============================
    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir creación para manejar plantillas por defecto automáticamente.
        
        Este método implementa lógica de negocio que:
        1. Desmarca automáticamente otras plantillas por defecto si se crea una nueva
        2. Marca automáticamente como por defecto si es la primera plantilla de la empresa
        3. Registra la creación en logs para auditoria
        
        La lógica aquí evita que el usuario tenga que hacer pasos manuales adicionales
        y reduce la posibilidad de estados inconsistentes.
        """
        for vals in vals_list:
            company_id = vals.get('company_id')
            
            # Si se marca como por defecto, desmarcar otras de la misma empresa
            if vals.get('is_default') and company_id:
                existing_defaults = self.search([
                    ('company_id', '=', company_id),
                    ('is_default', '=', True),
                    ('active', '=', True)
                ])
                existing_defaults.write({'is_default': False})
                
                _logger.info(
                    'Desmarcando %d plantillas por defecto existentes para empresa %d',
                    len(existing_defaults), company_id
                )
            
            # Si es la primera plantilla de la empresa, marcarla como por defecto
            elif company_id and not vals.get('is_default'):
                existing_templates = self.search([
                    ('company_id', '=', company_id),
                    ('active', '=', True)
                ])
                
                if not existing_templates:
                    vals['is_default'] = True
                    _logger.info(
                        'Marcando primera plantilla como por defecto para empresa %d',
                        company_id
                    )
        
        templates = super().create(vals_list)
        
        # Log de auditoría
        for template in templates:
            _logger.info(
                'Plantilla de exportación creada: %s (ID: %d) para empresa %s',
                template.name, template.id, template.company_id.name
            )
        
        return templates
    
    def write(self, vals):
        """
        Sobrescribir escritura para manejar cambios en plantillas por defecto.
        
        Similar a create(), este método maneja automáticamente la lógica de
        plantillas por defecto cuando se actualizan registros existentes.
        """
        # Si se está marcando como por defecto
        if vals.get('is_default'):
            for template in self:
                # Desmarcar otras plantillas por defecto de la misma empresa
                other_defaults = self.search([
                    ('company_id', '=', template.company_id.id),
                    ('is_default', '=', True),
                    ('active', '=', True),
                    ('id', '!=', template.id)
                ])
                other_defaults.write({'is_default': False})
        
        # Si se está desactivando la plantilla por defecto, buscar otra para marcar
        if vals.get('active') == False:
            for template in self.filtered('is_default'):
                alternative = self.search([
                    ('company_id', '=', template.company_id.id),
                    ('active', '=', True),
                    ('id', '!=', template.id)
                ], limit=1)
                
                if alternative:
                    alternative.is_default = True
                    _logger.info(
                        'Marcando plantilla alternativa %s como por defecto '
                        'porque se desactivó la anterior', alternative.name
                    )
        
        return super().write(vals)
    
    # MÉTODOS DE UTILIDAD Y API PÚBLICA
    # =================================
    def generate_filename(self, invoice):
        """
        Generar nombre de archivo para una factura específica usando esta plantilla.
        
        Este es el método principal que convierte el patrón abstracto en un nombre
        de archivo concreto para una factura específica.
        
        Args:
            invoice (account.move): Registro de factura de Odoo
            
        Returns:
            str: Nombre de archivo sanitizado y listo para usar
            
        Raises:
            UserError: Si hay problemas con los datos de la factura o el patrón
        """
        self.ensure_one()
        
        try:
            # Determinar el tipo de documento de forma legible
            type_mapping = {
                'out_invoice': 'CLIENTE',
                'out_refund': 'NC_CLIENTE',
                'in_invoice': 'PROVEEDOR', 
                'in_refund': 'NC_PROVEEDOR'
            }
            
            doc_type = type_mapping.get(invoice.move_type, 'DESCONOCIDO')
            
            # Preparar datos para el patrón
            template_data = {
                'type': doc_type,
                'number': invoice.name or 'SIN_NUMERO',
                'partner': invoice.partner_id.name or 'SIN_PARTNER',
                'date': invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else 'SIN_FECHA',
                'year': invoice.invoice_date.strftime('%Y') if invoice.invoice_date else 'XXXX',
                'month': invoice.invoice_date.strftime('%m') if invoice.invoice_date else 'XX',
                'company': invoice.company_id.name or 'SIN_EMPRESA',
                'reference': invoice.ref or invoice.partner_id.ref or ''
            }
            
            # Sanitizar todos los valores para nombres de archivo seguros
            sanitized_data = {}
            for key, value in template_data.items():
                sanitized_data[key] = self._sanitize_filename(str(value))
            
            # Generar nombre usando el patrón
            filename = self.pattern.format(**sanitized_data)
            
            # Sanitización final y validación
            filename = self._sanitize_filename(filename)
            
            if not filename.strip():
                raise UserError(_(
                    'La plantilla "%s" generó un nombre de archivo vacío para la factura %s'
                ) % (self.name, invoice.name))
            
            # Incrementar contador de uso (sin commit automático)
            self.sudo().write({'usage_count': self.usage_count + 1})
            
            return filename
            
        except Exception as e:
            _logger.error(
                'Error generando nombre de archivo con plantilla %s para factura %s: %s',
                self.name, invoice.name, str(e)
            )
            raise UserError(_(
                'No se pudo generar el nombre de archivo para la factura %s '
                'usando la plantilla "%s". Error: %s'
            ) % (invoice.name, self.name, str(e)))
    
    @staticmethod
    def _sanitize_filename(filename):
        """
        Sanitizar cadenas para uso seguro en nombres de archivo.
        
        Este método estático puede ser usado desde cualquier parte del código
        para asegurar que las cadenas sean seguras como nombres de archivo
        en diferentes sistemas operativos.
        
        Args:
            filename (str): Cadena a sanitizar
            
        Returns:
            str: Cadena sanitizada segura para nombres de archivo
        """
        if not filename:
            return ''
        
        # Reemplazar caracteres problemáticos
        replacements = {
            '/': '_', '\\': '_', ':': '_', '*': '_', '?': '_',
            '"': '_', '<': '_', '>': '_', '|': '_', '\n': '_',
            '\r': '_', '\t': '_'
        }
        
        result = str(filename)
        for old, new in replacements.items():
            result = result.replace(old, new)
        
        # Eliminar espacios múltiples y caracteres de control
        result = re.sub(r'\s+', '_', result)
        result = re.sub(r'[^\w\-_\.]', '_', result)
        
        # Eliminar guiones bajos múltiples
        result = re.sub(r'_+', '_', result)
        
        # Limpiar inicio y final
        result = result.strip('_.')
        
        # Asegurar que no esté vacío después de la limpieza
        if not result:
            result = 'archivo'
        
        return result
    
    @api.model
    def get_default_for_company(self, company_id=None):
        """
        Obtener la plantilla por defecto para una empresa.
        
        Args:
            company_id (int, optional): ID de la empresa. Si no se especifica,
                                      usa la empresa actual del usuario.
        
        Returns:
            export.template: Plantilla por defecto o False si no existe
        """
        if not company_id:
            company_id = self.env.company.id
        
        template = self.search([
            ('company_id', '=', company_id),
            ('is_default', '=', True),
            ('active', '=', True)
        ], limit=1)
        
        return template
    
    # MÉTODOS DE INTERFAZ DE USUARIO
    # ==============================
    def action_test_pattern(self):
        """
        Acción para probar el patrón con datos de ejemplo.
        
        Este método puede ser llamado desde un botón en la vista para que
        el usuario vea inmediatamente cómo funcionará su patrón.
        """
        self.ensure_one()
        
        # Buscar una factura de ejemplo de la empresa
        sample_invoice = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('state', '=', 'posted')
        ], limit=1)
        
        if sample_invoice:
            try:
                example_filename = self.generate_filename(sample_invoice)
                message = _('Ejemplo con factura real %s:\n%s') % (
                    sample_invoice.name, example_filename
                )
            except Exception as e:
                message = _('Error probando con factura real: %s') % str(e)
        else:
            message = _('Ejemplo con datos ficticios:\n%s') % self.preview_example
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Prueba de Plantilla'),
                'message': message,
                'type': 'success' if not message.startswith('Error') else 'warning',
                'sticky': False,
            }
        }
    
    def name_get(self):
        """
        Personalizar cómo se muestra el nombre en relaciones Many2one.
        
        Esto hace que las plantillas se muestren de forma más informativa
        en los campos de selección, incluyendo si es la plantilla por defecto.
        """
        result = []
        for template in self:
            name = template.name
            if template.is_default:
                name = f"⭐ {name} (Por defecto)"
            if not template.active:
                name = f"🚫 {name} (Inactiva)"
            result.append((template.id, name))
        return result


# EXTENSIÓN DEL MODELO DE EMPRESA
# ===============================
class ResCompany(models.Model):
    """
    Extensión del modelo de empresa para integrar las plantillas de exportación.
    
    Esta extensión agrega campos y métodos relacionados con las plantillas
    directamente al modelo de empresa, facilitando la configuración desde
    la vista de empresa.
    """
    _inherit = 'res.company'
    
    # Relación inversa con las plantillas
    export_template_ids = fields.One2many(
        'export.template',
        'company_id',
        string='Plantillas de Exportación',
        help='Plantillas de nomenclatura configuradas para esta empresa'
    )
    
    # Campo computed para mostrar la plantilla por defecto
    default_export_template_id = fields.Many2one(
        'export.template',
        string='Plantilla por Defecto',
        compute='_compute_default_export_template',
        help='Plantilla de nomenclatura usada por defecto en las exportaciones'
    )
    
    # Contador de plantillas para smart buttons
    export_template_count = fields.Integer(
        string='Cantidad de Plantillas',
        compute='_compute_export_template_count'
    )
    
    @api.depends('export_template_ids.active')
    def _compute_export_template_count(self):
        """Calcular la cantidad de plantillas activas."""
        for company in self:
            company.export_template_count = len(
                company.export_template_ids.filtered('active')
            )
    
    @api.depends('export_template_ids.is_default', 'export_template_ids.active')
    def _compute_default_export_template(self):
        """Encontrar la plantilla marcada como por defecto."""
        for company in self:
            default_template = company.export_template_ids.filtered(
                lambda t: t.is_default and t.active
            )
            company.default_export_template_id = default_template[:1]
    
    def action_open_export_templates(self):
        """Abrir la vista de plantillas de exportación para esta empresa."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Plantillas de Exportación'),
            'res_model': 'export.template',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
            'context': {
                'default_company_id': self.id,
                'search_default_active': True,
            },
            'help': _(
                '<p class="o_view_nocontent_smiling_face">'
                'Crea tu primera plantilla de exportación'
                '</p><p>'
                'Las plantillas permiten personalizar cómo se nombran '
                'los archivos durante la exportación masiva de facturas.'
                '</p>'
            )
        }
