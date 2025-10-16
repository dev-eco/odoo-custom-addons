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

# Importar el archivo con los modelos Python
# Nota: importamos invoice_export_wizard (el nombre del archivo)
# NO importamos la clase InvoiceExportWizard
# Odoo descubre automáticamente las clases que heredan de models.Model
from . import invoice_export_wizard


# ==============================================
# NOTAS ADICIONALES PARA EL DESARROLLADOR
# ==============================================
"""
Mejores Prácticas para __init__.py en Odoo:

1. **Mantenerlos simples**
   - Solo imports, sin lógica compleja
   - Sin código ejecutable que no sean imports
   - Sin configuraciones o constantes globales

2. **Orden de imports**
   - Primero subdirectorios (models, wizard, controllers)
   - Luego archivos individuales si los hay
   - El orden puede importar si hay dependencias entre módulos

3. **Comentarios claros**
   - Documenta qué hace cada import si no es obvio
   - Especialmente útil en módulos grandes con muchos subdirectorios

4. **Convenciones de nombres**
   - Subdirectorios comunes: models, wizard, controllers, reports
   - Archivos Python: nombres descriptivos en snake_case
   - Clases Odoo: nombres en PascalCase

5. **Testing**
   - Si el __init__.py tiene un error de sintaxis, el módulo no cargará
   - Siempre verifica que los nombres de archivos coincidan con los imports
   - Usa el log de Odoo para detectar problemas de importación

Errores Comunes y Soluciones:
-----------------------------

❌ Error: "No module named 'invoice_export_wizard'"
✅ Solución: Verifica que el archivo se llame exactamente 'invoice_export_wizard.py'

❌ Error: "cannot import name 'wizard'"
✅ Solución: Asegúrate que existe wizard/__init__.py

❌ Error: El módulo aparece en Odoo pero no funciona
✅ Solución: Revisa el log de Odoo, probablemente hay un error en el código Python

❌ Error: "SyntaxError" en __init__.py
✅ Solución: Verifica que los imports estén bien escritos, especialmente los puntos

Debugging de problemas de importación:
--------------------------------------

1. Activa el modo debug de Odoo: ?debug=1 en la URL
2. Revisa el log con: sudo journalctl -u odoo-dev -f
3. Busca líneas con "ModuleNotFoundError" o "ImportError"
4. Verifica la estructura de archivos con: tree mass_invoice_export/
5. Confirma permisos: todos los .py deben ser legibles por el usuario odoo

Estructura completa del módulo final:
-------------------------------------

mass_invoice_export/
├── __init__.py                          ← Imports: wizard
├── __manifest__.py                      ← Metadata del módulo
├── README.md                            ← Documentación (opcional pero recomendado)
├── static/
│   ├── description/
│   │   ├── icon.png                    ← Icono del módulo (128x128)
│   │   └── index.html                  ← Descripción HTML (opcional)
├── security/
│   └── ir.model.access.csv             ← Permisos de acceso a modelos
├── wizard/
│   ├── __init__.py                      ← Imports: invoice_export_wizard
│   ├── invoice_export_wizard.py        ← Modelo TransientModel
│   └── invoice_export_wizard_views.xml ← Vistas del wizard
├── views/
│   └── account_move_views.xml          ← Herencia vista facturas
└── tests/                               ← Tests unitarios (opcional)
    ├── __init__.py
    └── test_invoice_export.py

¿Quieres añadir más subdirectorios?
----------------------------------

Si en el futuro quieres expandir el módulo con:
- Controllers (para APIs web): crea controllers/ y añade import
- Reports (reportes QWeb): crea reports/ y añade import  
- Models regulares (no wizards): crea models/ y añade import

Ejemplo de __init__.py expandido:

    # -*- coding: utf-8 -*-
    from . import models
    from . import wizard
    from . import controllers
    from . import reports

Cada subdirectorio necesitará su propio __init__.py importando
los archivos .py correspondientes.
"""
