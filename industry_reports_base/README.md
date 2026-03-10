# Industry Reports Base

Módulo base para sistema de reportes industriales en Odoo 17 Community.

## Descripción

Proporciona campos técnicos de dimensiones en productos para ser utilizados por módulos de reportes especializados (presupuestos, albaranes, facturas).

## Características - Fase Piloto

### Campos de Dimensiones en Productos

- **Largo (mm)**: Longitud del producto en milímetros
- **Ancho (mm)**: Ancho del producto en milímetros
- **Alto (mm)**: Altura del producto en milímetros
- **Diámetro (mm)**: Diámetro para productos cilíndricos
- **Dimensiones (computed)**: Formato legible automático
  - Rectangular: "100 x 50 x 30 mm"
  - Cilíndrico: "Ø 75 mm"

### Ubicación en Interfaz

Los campos se encuentran en:
- **Productos → Producto → Pestaña "Inventory" → Group "Dimensiones"**

## Instalación

```bash
# 1. Copiar módulo a custom-addons
cp -r industry_reports_base /opt/odoo/custom-addons/

# 2. Activar ambiente virtual
source /opt/odoo/odoo-core/venv17/bin/activate

# 3. Instalar módulo
/opt/odoo/odoo-core/odoo-bin -c /etc/odoo/odoo.conf \
  -d NOMBRE_DB \
  -i industry_reports_base \
  --stop-after-init
```

## Uso

### Configurar Dimensiones en Productos

1. Ir a **Productos → Productos**
2. Abrir un producto existente
3. Ir a pestaña **Inventory**
4. Rellenar campos en group **Dimensiones**:
   - Para productos rectangulares: Largo, Ancho, Alto
   - Para productos cilíndricos: Diámetro
5. Guardar

El campo **Dimensiones** se calcula automáticamente mostrando el formato legible.

### Ejemplos

**Producto rectangular:**
- Largo: 100 mm
- Ancho: 50 mm
- Alto: 30 mm
- **Resultado**: "100 x 50 x 30 mm"

**Producto cilíndrico:**
- Diámetro: 75 mm
- **Resultado**: "Ø 75 mm"

## Dependencias

- `product` (módulo core Odoo)

## Roadmap - Fase 2

Campos a añadir en futuras versiones:
- Material/Composición (Char)
- Acabado superficial (Selection)
- Ficha técnica PDF (Binary)
- Unidades por caja (Integer)
- Peso caja completa (Float)

## Soporte

Para reportar bugs o solicitar features, contactar con el equipo de desarrollo.

## Licencia

LGPL-3

## Autor

Tu Empresa - 2025
