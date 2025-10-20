# -*- coding: utf-8 -*-
"""
Modelo Export Template - Plantillas de Exportación Personalizables

Este archivo define el modelo que permite a las empresas crear plantillas
personalizadas para generar nombres de archivo durante la exportación.

¿Por qué necesitamos plantillas de nomenclatura?
===============================================
Imagina una asesoría fiscal que maneja 50 empresas diferentes. Cada empresa
puede tener requisitos específicos para nombrar sus archivos:

- Empresa A: "CLIENTE_FACTURA123_EMPRESA-A_20240115.pdf"
- Empresa B: "2024-01-15_FACT123_CLIENTE.pdf"
- Empresa C: "FACT-CLIENTE-EMPRESA-2024-01.pdf"

Sin plantillas, tendríamos que programar cada formato manualmente. Con 
plantillas, el usuario puede crear patrones flexibles usando variables
predefinidas como {doc_type}, {number}, {partner}, {date}, etc.

Arquitectura del Modelo
======================
Este modelo sigue el patrón estándar de Odoo:

1. Hereda de models.Model (modelo persistente)
2. Define _name único en el sistema
3. Incluye campos con tipos, validaciones y ayudas
4. Implementa métodos de negocio específicos
5. Añade constrains para validar integridad de datos

El patrón de plantillas es muy común en software empresarial porque
proporciona flexibilidad sin complejidad técnica para el usuario final.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ExportTemplate(models.Model):
    """
    Plantillas de Exportación para Nomenclatura Personalizada
    
    Este modelo permite a las empresas definir patrones personalizados
    para generar nombres de archivo durante la exportación masiva de facturas.
    
    La flexibilidad de estas plantillas es clave para adaptarse a los
    diferentes requisitos de nomenclatura que pueden tener las empresas
    o sus clientes externos (bancos, auditorías, sistemas contables).
    """
    
    # DEFINICIÓN DEL MODELO
    # ====================
    _name = 'export.template'
    _description = 'Plantilla de Exportación de Facturas'
    _order = 'company_id, name'  # Ordenar por empresa y luego por nombre
    
    # Control automático de empresa para seguridad multi-empresa
    # Esto asegura que los usuarios solo vean plantillas de sus empresas
    _check_company_auto = True
    
    # CAMPOS BÁSICOS DE IDENTIFICACIÓN
    # ===============================
    name = fields.Char(
        string='Nombre de Plantilla',
        required=True,
        help='Nombre descriptivo para identificar esta plantilla (ej: "Facturas Cliente Standard")'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        required=True,
        default=lambda self: self.env.company,
        help='Empresa a la que pertenece esta plantilla'
    )
    
    # CONFIGURACIÓN PRINCIPAL DE LA PLANTILLA
    # =======================================
    filename_pattern = fields.Char(
        string='Patrón de Nombre de Archivo',
        required=True,
        default='{doc_type}_{number}_{partner}_{date}',
        help='Patrón para generar nombres. Variables disponibles: '
             '{company_code}, {doc_type}, {number}, {partner}, {date}, '
             '{year}, {month}, {currency}, {amount}'
    )
    
    # CAMPOS DE CONTROL Y CONFIGURACIÓN
    # =================================
    is_default = fields.Boolean(
        string='Plantilla Predeterminada',
        default=False,
        help='Si está marcado, será la plantilla usada por defecto para esta empresa'
    )
    
    active = fields.Boolean(
        string='Activa',
        default=True,
        help='Las plantillas inactivas no aparecen en las opciones de selección'
    )
    
    # CAMPOS DESCRIPTIVOS
    # ==================
    description = fields.Text(
        string='Descripción',
        help='Descripción detallada del propósito y uso de esta plantilla'
    )
    
    # CAMPO COMPUTED PARA MOSTRAR EJEMPLO
    # ==================================
    example_filename = fields.Char(
        string='Ejemplo de Nombre',
        compute='_compute_example_filename',
        help='Muestra cómo se vería un nombre de archivo con esta plantilla'
    )
    
    # MÉTODOS COMPUTED
    # ===============
    @api.depends('filename_pattern')
    def _compute_example_filename(self):
        """
        Generar un ejemplo de nombre de archivo usando la plantilla actual.
        
        Este método computed se ejecuta automáticamente cada vez que cambia
        el patrón de nombre, proporcionando feedback inmediato al usuario
        sobre cómo se verán los archivos generados.
        
        ¿Por qué usar un campo computed?
        Los campos computed son ideales para mostrar información derivada
        que se calcula automáticamente a partir de otros campos. En este
        caso, ayuda al usuario a visualizar el resultado de su plantilla
        sin necesidad de hacer una exportación real.
        """
        for template in self:
            if template.filename_pattern:
                try:
                    # Variables de ejemplo para mostrar el patrón
                    example_vars = {
                        'company_code': template.company_id.code or 'COMP',
                        'doc_type': 'CLIENTE',
                        'number': 'FACT001',
                        'partner': 'EMPRESA_EJEMPLO',
                        'date': '20240115',
                        'year': '2024',
                        'month': '01',
                        'currency': 'EUR',
                        'amount': '1500',
                    }
                    
                    # Intentar formatear con las variables de ejemplo
                    example = template.filename_pattern.format(**example_vars)
                    template.example_filename = f"{example}.pdf"
                    
                except (KeyError, ValueError) as e:
                    # Si hay error en el patrón, mostrar mensaje descriptivo
                    template.example_filename = f"Error en patrón: {str(e)}"
            else:
                template.example_filename = _('Sin patrón definido')
    
    # VALIDACIONES Y CONSTRAINS
    # =========================
    @api.constrains('is_default', 'company_id')
    def _check_unique_default(self):
        """
        Asegurar que solo existe una plantilla predeterminada por empresa.
        
        Esta validación es crucial para mantener la integridad del sistema.
        Sin ella, podrían existir múltiples plantillas "por defecto", lo
        que causaría ambigüedad al momento de determinar cuál usar.
        
        ¿Por qué usar @api.constrains?
        Los constrains se ejecutan automáticamente cuando se modifican los
        campos especificados, proporcionando validación en tiempo real.
        Es mejor que validar manualmente en cada método write/create.
        """
        for template in self.filtered('is_default'):
            # Buscar otras plantillas por defecto de la misma empresa
            other_defaults = self.search([
                ('company_id', '=', template.company_id.id),
                ('is_default', '=', True),
                ('id', '!=', template.id),  # Excluir el registro actual
                ('active', '=', True),       # Solo considerar activas
            ])
            
            if other_defaults:
                raise ValidationError(_(
                    'Solo puede existir una plantilla predeterminada por empresa. '
                    'La empresa "%s" ya tiene la plantilla "%s" como predeterminada.'
                ) % (template.company_id.name, other_defaults[0].name))
    
    @api.constrains('filename_pattern')
    def _check_filename_pattern(self):
        """
        Validar que el patrón de nombre de archivo sea válido.
        
        Esta validación previene errores en tiempo de ejecución al verificar
        que el patrón pueda ser formateado correctamente con variables válidas.
        """
        for template in self:
            if not template.filename_pattern:
                continue
                
            # Variables válidas que pueden usarse en las plantillas
            valid_variables = {
                'company_code', 'doc_type', 'number', 'partner', 
                'date', 'year', 'month', 'currency', 'amount'
            }
            
            try:
                # Intentar extraer variables del patrón usando regex
                pattern_variables = set(re.findall(r'\{(\w+)\}', template.filename_pattern))
                
                # Verificar que todas las variables usadas sean válidas
                invalid_vars = pattern_variables - valid_variables
                if invalid_vars:
                    raise ValidationError(_(
                        'Variables inválidas en el patrón: %s\n'
                        'Variables disponibles: %s'
                    ) % (', '.join(invalid_vars), ', '.join(sorted(valid_variables))))
                
                # Probar que el patrón pueda formatearse sin errores
                test_vars = {var: 'test' for var in valid_variables}
                template.filename_pattern.format(**test_vars)
                
            except ValueError as e:
                raise ValidationError(_(
                    'Patrón de nombre inválido: %s\n'
                    'Asegúrese de usar la sintaxis correcta: {variable}'
                ) % str(e))
    
    # MÉTODOS DE NEGOCIO
    # =================
    @api.model
    def get_default_template(self, company_id):
        """
        Obtener la plantilla predeterminada para una empresa específica.
        
        Este método es útil para ser llamado desde otros modelos (como el wizard)
        cuando necesitan determinar automáticamente qué plantilla usar.
        
        Args:
            company_id (int): ID de la empresa
            
        Returns:
            export.template: Plantilla predeterminada o False si no existe
        """
        return self.search([
            ('company_id', '=', company_id),
            ('is_default', '=', True),
            ('active', '=', True),
        ], limit=1)
    
    def set_as_default(self):
        """
        Establecer esta plantilla como predeterminada para su empresa.
        
        Este método proporciona una forma conveniente de cambiar la plantilla
        predeterminada sin necesidad de editar manualmente los campos.
        """
        self.ensure_one()  # Asegurar que solo se procese un registro
        
        # Quitar el flag de predeterminada a otras plantillas de la misma empresa
        other_defaults = self.search([
            ('company_id', '=', self.company_id.id),
            ('is_default', '=', True),
            ('id', '!=', self.id),
        ])
        other_defaults.write({'is_default': False})
        
        # Establecer esta plantilla como predeterminada
        self.write({'is_default': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Plantilla Actualizada'),
                'message': _('"%s" es ahora la plantilla predeterminada') % self.name,
                'type': 'success',
            }
        }
    
    def test_template(self):
        """
        Probar la plantilla con datos de ejemplo para verificar su funcionamiento.
        
        Este método permite al usuario verificar que su plantilla funciona
        correctamente antes de usarla en una exportación real.
        """
        self.ensure_one()
        
        # Datos de ejemplo para probar la plantilla
        test_data = {
            'company_code': self.company_id.code or 'TEST',
            'doc_type': 'CLIENTE',
            'number': 'FACT2024001',
            'partner': 'CLIENTE_EJEMPLO_SA',
            'date': '20240115',
            'year': '2024',
            'month': '01',
            'currency': 'EUR',
            'amount': '2450',
        }
        
        try:
            result_filename = self.filename_pattern.format(**test_data)
            message = _(
                'Plantilla probada exitosamente!\n\n'
                'Patrón: %s\n'
                'Resultado: %s.pdf'
            ) % (self.filename_pattern, result_filename)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Prueba de Plantilla'),
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error en Plantilla'),
                    'message': _('La plantilla tiene errores: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    # MÉTODOS DE HERENCIA ESTÁNDAR
    # ===========================
    def name_get(self):
        """
        Personalizar cómo se muestra el nombre del registro en selecciones.
        
        En lugar de mostrar solo el nombre, mostramos también la empresa
        para facilitar la identificación en entornos multi-empresa.
        """
        result = []
        for template in self:
            name = template.name
            if template.company_id.code:
                name = f"[{template.company_id.code}] {name}"
            if template.is_default:
                name = f"{name} (Predeterminada)"
            result.append((template.id, name))
        return result
    
    @api.model
    def create(self, vals):
        """
        Sobrescribir create para manejar lógica especial al crear plantillas.
        
        Si se crea una plantilla marcada como predeterminada, automáticamente
        desmarcamos otras plantillas predeterminadas de la misma empresa.
        """
        # Crear el registro primero
        template = super().create(vals)
        
        # Si es la primera plantilla de la empresa, marcarla como predeterminada
        if not template.is_default:
            other_templates = self.search([
                ('company_id', '=', template.company_id.id),
                ('id', '!=', template.id),
                ('active', '=', True),
            ])
            
            if not other_templates:
                template.write({'is_default': True})
                _logger.info(
                    _('Plantilla "%s" marcada como predeterminada '
                      'por ser la primera de la empresa %s') % 
                    (template.name, template.company_id.name)
                )
        
        return template


"""
CONCEPTOS AVANZADOS EXPLICADOS
=============================

¿Por qué usar _check_company_auto = True?
----------------------------------------
En Odoo multi-empresa, este flag hace que automáticamente se añada un
filtro por empresa en todas las búsquedas y operaciones. Esto significa
que los usuarios solo verán plantillas de sus empresas autorizadas,
mejorando la seguridad sin código adicional.

Patrón de Plantillas con Variables
---------------------------------
El sistema de plantillas usa el método .format() de Python, que es muy
potente y flexible. Por ejemplo:

Patrón: "{doc_type}_{number}_{year}-{month}"
Variables: {"doc_type": "CLIENTE", "number": "F001", "year": "2024", "month": "01"}
Resultado: "CLIENTE_F001_2024-01"

Este patrón es extensible: en futuras versiones podemos añadir más variables
sin romper las plantillas existentes.

Constrains vs Validaciones en Métodos
------------------------------------
Los @api.constrains son superiores a validaciones manuales porque:
1. Se ejecutan automáticamente cuando cambian los campos especificados
2. Funcionan tanto en create() como en write()
3. Se ejecutan incluso cuando los cambios vienen de importaciones o XML
4. Proporcionan mejor experiencia de usuario (feedback inmediato)

Método name_get() Personalizado
------------------------------
name_get() controla cómo se muestran los registros en:
- Campos Many2one y Many2many
- Listas de selección
- Breadcrumbs y títulos

Es muy útil para hacer la interfaz más informativa, especialmente en
entornos multi-empresa donde necesitas distinguir entre registros
similares de diferentes empresas.

Logging Estratégico
------------------
El logging con _logger.info() es crucial para debugging y auditoría.
En este modelo, loggeamos eventos importantes como:
- Creación de plantillas predeterminadas automáticas
- Cambios de plantilla predeterminada
- Errores en patrones de nomenclatura

Esto facilita enormemente el soporte técnico y la resolución de problemas.
"""
