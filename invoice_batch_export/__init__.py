# -*- coding: utf-8 -*-
"""
Módulo Invoice Batch Export

Este es el archivo de inicialización principal del módulo invoice_batch_export.
Su función es importar todos los subdirectorios que contienen código Python
para que Odoo pueda cargar correctamente todos los componentes del módulo.

¿Por qué necesitamos __init__.py?
================================
En Python, un directorio se convierte en un "paquete" (package) solo cuando
contiene un archivo __init__.py. Este archivo le dice a Python:

1. "Este directorio es importable como módulo"
2. "Cuando alguien importe este directorio, ejecuta este código"
3. "Estos son los submódulos que debes cargar"

En Odoo, este patrón es fundamental porque:
- Odoo busca automáticamente directorios con __init__.py en addons_path
- Necesita importar los modelos Python para registrarlos en el ORM
- Permite control granular sobre qué se carga y en qué orden

Orden de Importación
===================
El orden de los imports puede ser importante si hay dependencias entre
los componentes. En nuestro caso:

1. models: Se cargan primero porque pueden ser referenciados por wizards
2. wizard: Se cargan después porque pueden usar modelos

¿Qué sucede si omitimos un import?
=================================
Si olvidamos importar un subdirectorio aquí:
- Los archivos .py de ese subdirectorio NO se cargarán
- Los modelos Python definidos ahí NO se registrarán en Odoo
- Aparecerán errores como "No existe el modelo xyz"
- Las vistas XML que referencien esos modelos fallarán

Convención de Nombres
====================
- Subdirectorios: snake_case (models, wizard)
- Archivos Python: snake_case (export_template.py)
- Clases Odoo: PascalCase (ExportTemplate)
"""

# Importar subdirectorios que contienen modelos Python
# Cada línea aquí le dice a Python que busque un directorio con ese nombre
# y ejecute su archivo __init__.py correspondiente

from . import models    # Importa models/__init__.py (modelos persistentes)
from . import wizard    # Importa wizard/__init__.py (modelos transitorios)

# Nota: NO importamos subdirectorios que solo contienen XML como:
# - views: Solo contiene archivos .xml, no .py
# - security: Solo contiene archivos .csv y .xml
# - data: Solo contiene archivos .xml
# - i18n: Solo contiene archivos .po
# 
# Los archivos XML/CSV se declaran en la sección 'data' del __manifest__.py
# y Odoo los carga automáticamente durante la instalación del módulo
