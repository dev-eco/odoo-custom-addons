# -*- coding: utf-8 -*-
"""
Inicialización del Paquete Wizard

Este archivo __init__.py del directorio wizard/ tiene la responsabilidad de
importar todos los modelos transitorios (TransientModel) que forman parte
de nuestro sistema de exportación masiva.

¿Qué son los Wizards en Odoo?
============================
Los wizards en Odoo son interfaces especiales diseñadas para guiar al usuario
a través de un proceso paso a paso. Son como "asistentes" que recopilan
información del usuario y ejecutan acciones complejas basadas en esa información.

Imagina que estás comprando un producto en línea: el proceso de checkout es
como un wizard. Te guía paso a paso (información personal, dirección de envío,
método de pago, confirmación) hasta completar la compra.

En nuestro caso, el wizard de exportación:
1. Recopila criterios de filtrado (fechas, tipos de documento, etc.)
2. Permite configurar opciones (formato de compresión, tamaño de lote)
3. Ejecuta la exportación masiva
4. Muestra resultados y proporciona descarga

Características de los TransientModel
====================================
Los wizards en Odoo se implementan usando TransientModel, que tienen
características especiales que los hacen perfectos para este propósito:

**Temporalidad Automática:**
- Los registros se eliminan automáticamente después de un tiempo
- No acumulan datos innecesariamente en la base de datos
- Ideales para procesos que no requieren persistencia

**Rendimiento Optimizado:**
- Tabla temporal que se limpia periódicamente
- Menos overhead que modelos persistentes
- Mejor rendimiento para operaciones frecuentes

**Seguridad Natural:**
- Los datos desaparecen automáticamente
- No hay riesgo de acumulación de información sensible
- Perfecto para procesos que manejan datos temporales

¿Por qué Separar Wizards de Models?
==================================
Separar los wizards en su propio directorio es una práctica organizacional
que mejora la claridad y mantenibilidad del código:

**Claridad Conceptual:**
- Models: Datos que persisten (plantillas, configuraciones)
- Wizards: Procesos temporales (exportaciones, importaciones)

**Facilidad de Mantenimiento:**
- Los wizards suelen cambiar más frecuentemente que los modelos
- Diferentes desarrolladores pueden trabajar en cada área
- Más fácil localizar código relacionado con procesos específicos

**Escalabilidad:**
- A medida que el módulo crece, los wizards se multiplican
- Cada proceso complejo puede tener su propio wizard
- La organización en directorios mantiene todo ordenado

Convención de Nombres en Wizards
===============================
Para wizards, seguimos estas convenciones específicas:

**Archivos Python:**
- Nombre descriptivo del proceso: batch_export_wizard.py
- Sufijo "_wizard" para claridad: import_wizard.py, config_wizard.py

**Clases Python:**
- PascalCase del proceso: BatchExportWizard
- Sufijo "Wizard" para consistencia: ImportWizard, ConfigWizard

**Modelos Odoo:**
- snake_case con puntos: batch.export.wizard
- Namespace del módulo implícito: todas empiezan igual

**Archivos XML:**
- Mismo nombre que el Python + _views.xml
- batch_export_wizard_views.xml, import_wizard_views.xml

Esta consistencia hace que cualquier desarrollador pueda entender
inmediatamente la estructura y localizar archivos específicos.
"""

# Importar modelos transitorios (wizards) del módulo
# Cada wizard se define en su propio archivo para mejor organización

from . import batch_export_wizard    # Wizard principal de exportación masiva

"""
EXPANSIÓN FUTURA DEL PAQUETE WIZARD
===================================

A medida que el módulo evolucione, podrías añadir wizards adicionales:

from . import batch_export_wizard      # Exportación masiva (actual)
from . import batch_import_wizard      # Importación masiva de facturas
from . import export_config_wizard     # Configuración de exportación
from . import template_wizard          # Asistente para crear plantillas
from . import migration_wizard         # Migración de datos entre versiones

Cada wizard tendría su propósito específico:

**batch_import_wizard:**
Podría manejar la importación masiva de facturas desde archivos ZIP,
permitiendo cargar múltiples PDFs y crear automáticamente las facturas
correspondientes en Odoo.

**export_config_wizard:**
Un asistente para configurar las opciones de exportación de una empresa,
guiando paso a paso a través de todas las opciones disponibles.

**template_wizard:**
Un asistente inteligente que ayude a crear plantillas de nomenclatura
preguntando al usuario qué información quiere incluir y en qué formato.

**migration_wizard:**
Para migrar configuraciones y plantillas cuando se actualice el módulo
a versiones futuras con nuevas características.

Patrón de Diseño: Un Wizard por Proceso
=======================================
La regla general es: un wizard por cada proceso complejo que requiera
múltiples pasos o configuraciones del usuario.

**Señales de que necesitas un wizard:**
- El proceso requiere más de 2-3 campos de entrada
- Hay validaciones complejas entre campos
- El proceso tiene múltiples pasos o fases
- Necesitas mostrar resultados o confirmaciones al usuario
- El proceso es ocasional (no de uso diario)

**Cuándo NO usar un wizard:**
- Para operaciones simples de un solo campo
- Para acciones frecuentes que el usuario hace muchas veces al día
- Cuando toda la información está disponible en el contexto actual
- Para operaciones que no requieren configuración del usuario

Mejores Prácticas para Wizards
=============================

**Estructura Paso a Paso:**
1. Recopilar información del usuario (campos de entrada)
2. Validar datos y mostrar vista previa si es posible
3. Ejecutar el proceso (con barra de progreso si es largo)
4. Mostrar resultados y opciones de descarga/continuar

**Experiencia de Usuario:**
- Campos con valores por defecto inteligentes
- Ayudas contextuales (help) en todos los campos
- Validación en tiempo real cuando sea posible
- Mensajes de error claros y accionables
- Confirmaciones de éxito con información específica

**Manejo de Errores:**
- Try/catch en todas las operaciones críticas
- Logging detallado para debugging
- Mensajes de error informativos para el usuario
- Opciones de recuperación cuando sea posible
- Limpieza automática en caso de fallos

**Rendimiento:**
- Procesamiento por lotes para operaciones grandes
- Indicadores de progreso para procesos largos
- Timeouts apropiados para evitar bloqueos
- Limpieza de recursos temporales automática
"""
