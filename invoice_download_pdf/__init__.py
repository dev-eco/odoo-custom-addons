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
   - Esencial para módulos con dependencias internas

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


# ==============================================
# wizard/__init__.py (subdirectorio wizard)
# ==============================================
# -*- coding: utf-8 -*-
"""
Paquete wizard del módulo Mass Invoice Export

Este __init__.py está dentro del subdirectorio wizard/ y controla
qué archivos Python se cargan cuando se importa el paquete wizard.

Estructura de directorios esperada:
mass_invoice_export/
├── __init__.py (el archivo de arriba)
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── wizard/
│   ├── __init__.py (este archivo)
│   ├── invoice_export_wizard.py (el modelo Python)
│   └── invoice_export_wizard_views.xml (las vistas)
└── views/
    └── account_move_views.xml

¿Por qué separar models de views?
---------------------------------
- Los archivos .py (modelos) se importan aquí en __init__.py
- Los archivos .xml (vistas) NO se importan aquí
- Los XMLs se declaran en la lista 'data' del __manifest__.py
- Esta separación es una convención de Odoo que mejora la claridad

¿Qué pasa si olvido este archivo?
---------------------------------
Si no existe wizard/__init__.py:
1. Python no reconocerá wizard/ como paquete
2. El import en el __init__.py principal fallará
3. Odoo no podrá cargar el módulo
4. Verás un error como: "ModuleNotFoundError: No module named 'wizard'"
"""
