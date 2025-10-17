# ==============================================
# __init__.py (raíz del módulo)
# ==============================================
# -*- coding: utf-8 -*-
"""
Módulo Mass Invoice Export to ZIP

Este es el archivo __init__.py principal del módulo.

¿Para qué sirve __init__.py?
-----------------------------
En Python, __init__.py tiene dos propósitos fundamentales:

1. **Marca el directorio como paquete Python**
   - Sin __init__.py, Python no reconoce el directorio como importable
   - Esto es un requisito histórico de Python < 3.3
   - Odoo sigue requiriéndolo para mantener compatibilidad
   
2. **Controla qué se importa cuando se carga el módulo**
   - Los imports aquí se ejecutan cuando Odoo carga el módulo
   - Permite controlar el orden de carga de componentes

¿Por qué importar subdirectorios?
---------------------------------
Cuando escribimos "from . import wizard", le decimos a Python:
- El punto (.) significa "desde el directorio actual"
- "wizard" es un subdirectorio que también debe importarse
- Python entonces buscará y ejecutará wizard/__init__.py

Este patrón es estándar en Odoo para organizar código por funcionalidad.
"""

# Importar el subdirectorio wizard
# Esto cargará todos los modelos Python definidos en wizard/__init__.py
from . import wizard
