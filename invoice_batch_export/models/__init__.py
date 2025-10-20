# -*- coding: utf-8 -*-
"""
Inicialización del Paquete Models

Este archivo es el __init__.py del directorio models/ y su función es importar
todos los archivos Python que contienen modelos de datos persistentes.

¿Qué son los Modelos Persistentes?
==================================
Los modelos persistentes son clases Python que heredan de models.Model y
representan tablas en la base de datos PostgreSQL. A diferencia de los
TransientModel (que son temporales), estos modelos:

1. Almacenan datos permanentemente en la base de datos
2. Sus registros persisten entre sesiones de usuario
3. Se pueden hacer consultas complejas sobre ellos
4. Soportan relaciones (Many2many, One2many, Many2one)

En nuestro módulo tenemos dos modelos persistentes:

1. ExportTemplate: Almacena plantillas de nomenclatura de archivos
2. ResCompany: Extiende el modelo de empresa con configuraciones

¿Por qué Separar en Archivos Diferentes?
========================================
Separar modelos en archivos diferentes es una buena práctica porque:

- Mejora la legibilidad (cada archivo tiene un propósito específico)
- Facilita el mantenimiento (cambios en un modelo no afectan otros)
- Permite trabajo en equipo (diferentes desarrolladores en diferentes archivos)
- Sigue la filosofía Unix: "hacer una cosa y hacerla bien"

Convención de Nombres
====================
- Archivos: snake_case matching el modelo (export_template.py)
- Clases: PascalCase matching el nombre del modelo (ExportTemplate)
- Modelos Odoo: snake_case con puntos (export.template)

El mapeo típico es:
export_template.py → class ExportTemplate → _name = 'export.template'

¿Qué Pasa Si Olvido un Import?
=============================
Si no importas un archivo .py aquí:
- La clase del modelo NO se registrará en el ORM de Odoo
- Las vistas XML que referencien ese modelo fallarán
- Los menús que apunten a ese modelo no funcionarán
- Aparecerán errores como "Model 'export.template' does not exist"

Orden de Importación
===================
En este caso, el orden no es crítico porque nuestros modelos no tienen
dependencias cruzadas. Sin embargo, si un modelo referencia a otro,
debe importarse después del modelo referenciado.

Por ejemplo, si ExportTemplate tuviera una relación Many2one hacia
un modelo CustomModel, entonces:

from . import custom_model      # Primero el modelo referenciado
from . import export_template   # Después el modelo que lo referencia
"""

# Importar modelos persistentes del módulo
# Cada import aquí carga un archivo .py y registra sus modelos en Odoo

from . import export_template   # Plantillas de exportación personalizables
from . import res_company       # Extensión del modelo de empresa

"""
EXPLICACIÓN DETALLADA DE CADA MODELO
====================================

export_template.py
-----------------
Contiene el modelo 'export.template' que permite a las empresas definir
plantillas personalizadas para los nombres de archivo. Esto es especialmente
útil para asesorías que manejan múltiples clientes y necesitan nomenclaturas
específicas para cada uno.

Campos principales:
- name: Nombre descriptivo de la plantilla
- company_id: Empresa a la que pertenece (seguridad multiempresa)
- filename_pattern: Patrón con variables para generar nombres
- is_default: Si es la plantilla por defecto de la empresa

res_company.py
--------------
Extiende el modelo base 'res.company' (empresas) con configuraciones
específicas para la exportación masiva. En lugar de crear un modelo
completamente nuevo, aprovechamos el sistema de herencia de Odoo.

Campos añadidos:
- default_compression_format: Formato de compresión preferido
- max_batch_size: Tamaño máximo de lote para esta empresa
- export_template_ids: Relación One2many a las plantillas

¿Por qué Extender res.company?
==============================
Extender res.company en lugar de crear un modelo separado tiene ventajas:

1. Los datos se almacenan junto con la empresa (coherencia)
2. El acceso multiempresa funciona automáticamente
3. Las configuraciones están donde el usuario las espera encontrar
4. No necesitamos gestionar la relación empresa-configuración manualmente

Esta es una técnica muy poderosa en Odoo que permite añadir funcionalidad
sin romper la estructura existente del sistema.
"""
