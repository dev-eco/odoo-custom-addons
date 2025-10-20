# -*- coding: utf-8 -*-
"""
Extensión del Modelo res.company - Configuraciones de Exportación

Este archivo demuestra uno de los patrones más poderosos de Odoo: la herencia
de modelos existentes. En lugar de crear un modelo completamente nuevo para
almacenar configuraciones de exportación, extendemos el modelo base de empresa
(res.company) para añadir campos específicos de nuestro módulo.

¿Por qué extender res.company en lugar de crear un modelo nuevo?
==============================================================
Imagina que creas un modelo separado llamado 'export.configuration'. Esto
significaría que tendrías que:

1. Gestionar manualmente la relación empresa-configuración
2. Asegurar que cada empresa tenga exactamente una configuración
3. Manejar la seguridad multi-empresa desde cero
4. Crear vistas adicionales para gestionar estas configuraciones

Al extender res.company, todas estas complejidades desaparecen porque:
- Los datos se almacenan directamente en el registro de empresa
- La seguridad multi-empresa funciona automáticamente
- Las configuraciones aparecen naturalmente en la vista de empresa
- No necesitas gestionar relaciones adicionales

Conceptos Clave de Herencia en Odoo
==================================
Odoo soporta dos tipos de herencia de modelos:

1. **Herencia por extensión (_inherit = 'modelo.existente')**:
   Añade campos y métodos al modelo existente sin crear una nueva tabla.
   Los datos se almacenan en la misma tabla.

2. **Herencia por delegación (_inherit + _name diferentes)**:
   Crea una nueva tabla pero hereda comportamientos del modelo padre.
   Más complejo pero útil para casos específicos.

En este archivo usamos herencia por extensión porque queremos que los
datos de configuración vivan directamente en la tabla res_company.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """
    Extensión de la Empresa con Configuraciones de Exportación
    
    Esta clase extiende el modelo base de empresa (res.company) añadiendo
    campos específicos para configurar el comportamiento de la exportación
    masiva de facturas.
    
    Al usar herencia por extensión, estos campos aparecen como si fueran
    campos nativos del modelo empresa, proporcionando una experiencia
    de usuario completamente integrada.
    """
    
    # DEFINICIÓN DE HERENCIA
    # =====================
    _inherit = 'res.company'
    # Al usar _inherit sin definir _name, estamos extendiendo el modelo
    # existente. Los campos que definamos aquí se añadirán a la tabla
    # res_company en la base de datos.
    
    # CONFIGURACIONES DE EXPORTACIÓN POR DEFECTO
    # ==========================================
    default_compression_format = fields.Selection([
        ('zip', _('ZIP (Estándar)')),
        ('zip_best', _('ZIP (Mejor Compresión)')),
        ('tar_gz', _('TAR.GZ (Estándar Unix)')),
        ('7z', _('7-Zip (Compresión Ultra)')),
    ], string='Formato de Compresión Predeterminado',
       default='zip_best',
       help='Formato de compresión que se seleccionará automáticamente '
            'para las exportaciones de esta empresa')
    
    default_batch_size = fields.Integer(
        string='Tamaño de Lote Predeterminado',
        default=100,
        help='Número de facturas a procesar en cada lote. '
             'Valores más altos son más rápidos pero usan más memoria. '
             'Se recomienda entre 50-200 según la capacidad del servidor.'
    )
    
    # CONFIGURACIONES DE NOMENCLATURA
    # ==============================
    use_custom_filename_pattern = fields.Boolean(
        string='Usar Patrón de Nombres Personalizado',
        default=False,
        help='Si está activado, se usará el patrón personalizado definido abajo '
             'cuando no se seleccione una plantilla específica'
    )
    
    custom_filename_pattern = fields.Char(
        string='Patrón de Nombres Personalizado',
        default='{company_code}_{doc_type}_{number}_{date}',
        help='Patrón para generar nombres de archivo cuando no se use una plantilla. '
             'Variables disponibles: {company_code}, {doc_type}, {number}, '
             '{partner}, {date}, {year}, {month}, {currency}, {amount}'
    )
    
    # CONFIGURACIONES DE FILTRADO
    # ===========================
    default_include_customer_invoices = fields.Boolean(
        string='Incluir Facturas de Cliente por Defecto',
        default=True,
        help='Preseleccionar facturas de cliente en el wizard de exportación'
    )
    
    default_include_vendor_bills = fields.Boolean(
        string='Incluir Facturas de Proveedor por Defecto',
        default=True,
        help='Preseleccionar facturas de proveedor en el wizard de exportación'
    )
    
    default_include_credit_notes = fields.Boolean(
        string='Incluir Notas de Crédito por Defecto',
        default=False,
        help='Preseleccionar notas de crédito en el wizard de exportación'
    )
    
    # CONFIGURACIONES DE SEGURIDAD Y LÍMITES
    # ======================================
    max_export_invoices = fields.Integer(
        string='Máximo de Facturas por Exportación',
        default=5000,
        help='Límite máximo de facturas que se pueden exportar en una sola operación. '
             'Esto previene el uso excesivo de recursos del servidor.'
    )
    
    allow_draft_export = fields.Boolean(
        string='Permitir Exportar Facturas en Borrador',
        default=False,
        help='Si está activado, los usuarios pueden exportar facturas que aún '
             'no han sido confirmadas. Útil para revisiones internas.'
    )
    
    # RELACIONES CON OTROS MODELOS
    # ============================
    export_template_ids = fields.One2many(
        'export.template',
        'company_id',
        string='Plantillas de Exportación',
        help='Plantillas de nomenclatura disponibles para esta empresa'
    )
    
    # CAMPOS COMPUTED PARA ESTADÍSTICAS
    # =================================
    export_template_count = fields.Integer(
        string='Número de Plantillas',
        compute='_compute_export_template_count',
        help='Cantidad total de plantillas de exportación configuradas'
    )
    
    default_export_template_id = fields.Many2one(
        'export.template',
        string='Plantilla Predeterminada',
        compute='_compute_default_export_template',
        help='Plantilla que se usará por defecto en las exportaciones'
    )
    
    # MÉTODOS COMPUTED
    # ===============
    @api.depends('export_template_ids')
    def _compute_export_template_count(self):
        """
        Calcular el número de plantillas activas para cada empresa.
        
        Este campo computed es útil para mostrar información estadística
        en la vista de empresa y para implementar smart buttons que
        muestren cuántas plantillas tiene configuradas cada empresa.
        """
        for company in self:
            company.export_template_count = len(
                company.export_template_ids.filtered('active')
            )
    
    @api.depends('export_template_ids.is_default')
    def _compute_default_export_template(self):
        """
        Identificar cuál es la plantilla predeterminada de cada empresa.
        
        Este campo computed facilita mostrar y gestionar qué plantilla
        está configurada como predeterminada, sin necesidad de hacer
        búsquedas adicionales en cada operación.
        """
        for company in self:
            default_template = company.export_template_ids.filtered(
                lambda t: t.is_default and t.active
            )
            company.default_export_template_id = default_template[:1]
    
    # VALIDACIONES Y CONSTRAINS
    # =========================
    @api.constrains('default_batch_size')
    def _check_batch_size(self):
        """
        Validar que el tamaño de lote predeterminado esté en un rango razonable.
        
        Esta validación previene configuraciones que podrían causar problemas
        de rendimiento o agotamiento de memoria en el servidor.
        """
        for company in self:
            if company.default_batch_size < 1:
                raise ValidationError(_(
                    'El tamaño de lote debe ser al menos 1 factura.'
                ))
            
            if company.default_batch_size > 1000:
                raise ValidationError(_(
                    'El tamaño de lote no puede exceder 1000 facturas. '
                    'Valores muy altos pueden causar problemas de memoria.'
                ))
    
    @api.constrains('max_export_invoices')
    def _check_max_export_invoices(self):
        """
        Validar que el límite máximo de exportación sea razonable.
        """
        for company in self:
            if company.max_export_invoices < 1:
                raise ValidationError(_(
                    'El límite máximo de exportación debe ser al menos 1 factura.'
                ))
            
            if company.max_export_invoices > 50000:
                raise ValidationError(_(
                    'El límite máximo de exportación no puede exceder 50,000 facturas '
                    'para evitar problemas de rendimiento del servidor.'
                ))
    
    @api.constrains('custom_filename_pattern', 'use_custom_filename_pattern')
    def _check_custom_filename_pattern(self):
        """
        Validar que el patrón personalizado sea válido cuando esté activado.
        
        Esta validación reutiliza la misma lógica que usamos en el modelo
        de plantillas, manteniendo consistencia en toda la aplicación.
        """
        for company in self:
            if not company.use_custom_filename_pattern:
                continue  # No validar si no está activado
            
            if not company.custom_filename_pattern:
                raise ValidationError(_(
                    'Debe definir un patrón personalizado si está activada '
                    'la opción de usar patrón personalizado.'
                ))
            
            # Reutilizar la lógica de validación del modelo de plantillas
            valid_variables = {
                'company_code', 'doc_type', 'number', 'partner',
                'date', 'year', 'month', 'currency', 'amount'
            }
            
            try:
                import re
                pattern_variables = set(re.findall(
                    r'\{(\w+)\}', company.custom_filename_pattern
                ))
                
                invalid_vars = pattern_variables - valid_variables
                if invalid_vars:
                    raise ValidationError(_(
                        'Variables inválidas en el patrón personalizado: %s\n'
                        'Variables disponibles: %s'
                    ) % (', '.join(invalid_vars), ', '.join(sorted(valid_variables))))
                
                # Probar que el patrón se pueda formatear
                test_vars = {var: 'test' for var in valid_variables}
                company.custom_filename_pattern.format(**test_vars)
                
            except ValueError as e:
                raise ValidationError(_(
                    'Patrón personalizado inválido: %s'
                ) % str(e))
    
    # MÉTODOS DE NEGOCIO
    # =================
    def action_open_export_templates(self):
        """
        Abrir la vista de plantillas de exportación filtrada por esta empresa.
        
        Este método implementa la acción que se ejecuta cuando el usuario
        hace clic en el smart button de plantillas en la vista de empresa.
        """
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Plantillas de Exportación'),
            'res_model': 'export.template',
            'view_mode': 'tree,form',
            'domain': [('company_id', '=', self.id)],
            'context': {
                'default_company_id': self.id,
                'search_default_active': True,  # Filtro por defecto: solo activas
            },
            'help': _(
                '<p class="o_view_nocontent_smiling_face">'
                'Crea tu primera plantilla de exportación'
                '</p><p>'
                'Las plantillas te permiten personalizar cómo se nombran '
                'los archivos durante la exportación masiva de facturas.'
                '</p>'
            )
        }
    
    def action_create_export_template(self):
        """
        Abrir el formulario para crear una nueva plantilla de exportación.
        
        Este método proporciona un acceso rápido para crear plantillas
        directamente desde la vista de empresa, con valores predeterminados
        apropiados.
        """
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Plantilla de Exportación'),
            'res_model': 'export.template',
            'view_mode': 'form',
            'target': 'new',  # Abrir en modal
            'context': {
                'default_company_id': self.id,
                'default_name': _('Plantilla %s') % self.name,
                # Si es la primera plantilla, marcarla como predeterminada
                'default_is_default': not bool(self.export_template_ids),
            }
        }
    
    def get_export_defaults(self):
        """
        Obtener todas las configuraciones predeterminadas para exportación.
        
        Este método centraliza la obtención de configuraciones, facilitando
        su uso desde el wizard de exportación y otros componentes del sistema.
        
        Returns:
            dict: Diccionario con todas las configuraciones predeterminadas
        """
        self.ensure_one()
        
        return {
            'compression_format': self.default_compression_format,
            'batch_size': self.default_batch_size,
            'include_customer_invoices': self.default_include_customer_invoices,
            'include_vendor_bills': self.default_include_vendor_bills,
            'include_credit_notes': self.default_include_credit_notes,
            'max_export_invoices': self.max_export_invoices,
            'allow_draft_export': self.allow_draft_export,
            'use_custom_pattern': self.use_custom_filename_pattern,
            'custom_pattern': self.custom_filename_pattern,
            'default_template_id': self.default_export_template_id.id,
        }
    
    def test_custom_pattern(self):
        """
        Probar el patrón personalizado de la empresa con datos de ejemplo.
        
        Similar al método test_template() del modelo de plantillas, pero
        adaptado para probar el patrón personalizado configurado a nivel
        de empresa.
        """
        self.ensure_one()
        
        if not self.use_custom_filename_pattern or not self.custom_filename_pattern:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Patrón No Configurado'),
                    'message': _('No hay patrón personalizado configurado para probar.'),
                    'type': 'warning',
                }
            }
        
        # Datos de ejemplo
        test_data = {
            'company_code': self.code or 'COMP',
            'doc_type': 'CLIENTE',
            'number': 'FACT2024001',
            'partner': 'CLIENTE_EJEMPLO_SA',
            'date': '20240115',
            'year': '2024',
            'month': '01',
            'currency': 'EUR',
            'amount': '1250',
        }
        
        try:
            result = self.custom_filename_pattern.format(**test_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Prueba de Patrón Exitosa'),
                    'message': _(
                        'Patrón: %s\n'
                        'Resultado: %s.pdf'
                    ) % (self.custom_filename_pattern, result),
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error en Patrón'),
                    'message': _('Error al probar el patrón: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }


"""
PATRONES AVANZADOS EXPLICADOS EN DETALLE
========================================

¿Por qué Herencia por Extensión vs Modelo Separado?
--------------------------------------------------
La decisión de usar herencia por extensión (_inherit sin _name nuevo) en lugar
de crear un modelo separado es estratégica:

**Ventajas de Herencia por Extensión:**
1. Los datos viven en la misma tabla (res_company)
2. No necesitas gestionar relaciones One2one
3. La seguridad multi-empresa funciona automáticamente
4. Las configuraciones aparecen naturalmente en la vista de empresa
5. Menos consultas SQL (mejor rendimiento)

**Cuándo usar Modelo Separado:**
1. Cuando necesitas múltiples configuraciones por empresa
2. Cuando los datos son muy complejos o numerosos
3. Cuando diferentes usuarios necesitan accesos diferentes
4. Cuando quieres historial de cambios independiente

Patrón de Configuraciones Predeterminadas
----------------------------------------
El patrón que implementamos aquí es muy común en software empresarial:
- Configuraciones globales a nivel de empresa
- Configuraciones específicas a nivel de operación (wizard)
- Las específicas sobrescriben las globales

Esto proporciona flexibilidad sin complejidad: el usuario puede configurar
valores por defecto que le ahorren tiempo, pero puede cambiarlos cuando
sea necesario para casos específicos.

Campos Computed para Información Derivada
----------------------------------------
Los campos computed como export_template_count y default_export_template_id
son ejemplos de información "derivada" que se calcula automáticamente.

Esto es mejor que almacenar estos valores manualmente porque:
1. Siempre están actualizados (se recalculan cuando cambian las dependencias)
2. No ocupan espacio adicional en base de datos
3. No se pueden corromper por cambios manuales
4. Facilitan la implementación de smart buttons y estadísticas

Smart Buttons y Acciones de Navegación
-------------------------------------
Los métodos action_open_export_templates() y action_create_export_template()
implementan el patrón de "smart buttons" que es muy común en Odoo.

Los smart buttons proporcionan navegación contextual: desde la empresa
puedes ir directamente a sus plantillas relacionadas, con filtros
automáticos aplicados. Esto mejora enormemente la experiencia del usuario.

Validaciones Centralizadas
-------------------------
Al centralizar las validaciones en constrains, aseguramos que las reglas
de negocio se apliquen consistentemente sin importar cómo se modifiquen
los datos (interfaz web, importación, API, etc.).

Esta es una diferencia clave entre el desarrollo en Odoo y otros frameworks:
las validaciones viven en el modelo, no en las vistas o controladores.

Métodos de Negocio como API Interna
----------------------------------
Métodos como get_export_defaults() actúan como una "API interna" que otros
componentes pueden usar para obtener configuraciones de forma consistente.

Esto es mejor que acceder directamente a los campos porque:
1. Centraliza la lógica de obtención de configuraciones
2. Permite transformaciones o validaciones adicionales
3. Facilita cambios futuros sin romper código dependiente
4. Proporciona un punto único para debugging y logging

Reutilización de Lógica de Validación
------------------------------------
En _check_custom_filename_pattern() reutilizamos la misma lógica de validación
que implementamos en el modelo de plantillas. Esto es un ejemplo de DRY
(Don't Repeat Yourself) aplicado correctamente.

Si necesitáramos cambiar las reglas de validación en el futuro, podríamos
extraer esta lógica a un método helper común que ambos modelos puedan usar.
"""
