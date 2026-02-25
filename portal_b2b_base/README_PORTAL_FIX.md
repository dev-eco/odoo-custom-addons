# Fix de Visibilidad de Histórico en Portal B2B

## Problema

Los distribuidores que ya tenían pedidos y facturas antes de la implementación del portal no ven su histórico completo cuando acceden al portal.

## Causas Identificadas

1. **Campo `portal_visible`**: Los pedidos antiguos tienen `portal_visible=False` porque fueron creados antes de que el partner tuviera un usuario de portal.

2. **Relación de Partners**: Posibles inconsistencias en la jerarquía de partners comerciales.

3. **Access Tokens**: Pedidos/facturas antiguos pueden no tener `access_token` generado.

## Soluciones Implementadas

### 1. Mejora del Dominio de Filtrado

Los métodos `_get_orders_domain()` y `_get_invoices_domain()` ahora buscan explícitamente todos los partners relacionados con el `commercial_partner_id`, en lugar de depender solo de `child_of`.

### 2. Recálculo de `portal_visible`

Se añadieron acciones para recalcular el campo `portal_visible` en pedidos existentes.

### 3. Generación de Access Tokens

Se asegura que todos los pedidos y facturas tengan su `access_token` generado.

## Uso

### Opción A: Migración Automática (Recomendado)

Al actualizar el módulo, se ejecutará automáticamente la migración:

```bash
odoo-bin -u portal_b2b_base -d tu_base_de_datos
```

Esto:
- Recalculará portal_visible en todos los pedidos
- Generará access_token en pedidos y facturas sin token
- Mejorará los filtros del portal

### Opción B: Acciones Manuales

Si prefieres ejecutar las correcciones manualmente:

#### 1. Diagnóstico por Partner

1. Ir a Contactos > Distribuidores
2. Abrir el partner del distribuidor
3. Click en Acción > Diagnosticar Pedidos Portal
4. Revisar los logs del servidor

#### 2. Recalcular Visibilidad (Todos los Pedidos)

1. Ir a Portal B2B > Configuración > Herramientas Portal
2. Click en Recalcular Visibilidad Portal

#### 3. Recalcular Visibilidad (Un Partner Específico)

1. Ir a Contactos > Distribuidores
2. Abrir el partner
3. Click en Acción > Recalcular portal_visible (Este Partner)

#### 4. Generar Tokens Faltantes

1. Ir a Portal B2B > Configuración > Herramientas Portal
2. Click en Generar Tokens (Pedidos) o Generar Tokens (Facturas)

### Opción C: Script Python (Para Grandes Volúmenes)

```python
# Ejecutar en shell de Odoo
env['sale.order'].action_fix_portal_visibility_all()
env['sale.order'].action_ensure_access_tokens_all()
env['account.move'].action_ensure_access_tokens_all()
```

## Verificación

Para verificar que todo funciona correctamente:

1. **Backend**: Revisar que los pedidos antiguos tengan portal_visible=True
   - Ir a Ventas > Pedidos
   - Añadir columna "Visible en Portal"
   - Filtrar por partner del distribuidor

2. **Portal**: Acceder con usuario del distribuidor
   - Ir a "Mis Pedidos"
   - Verificar que se muestran pedidos antiguos y nuevos
   - Ir a "Mis Facturas"
   - Verificar que se muestran facturas antiguas y nuevas

3. **Logs**: Revisar logs del servidor
   ```bash
   grep "portal_visible\|access_token" odoo.log
   ```

## Troubleshooting

### Los pedidos siguen sin aparecer

1. Ejecutar diagnóstico:
   ```python
   partner = env['res.partner'].browse(PARTNER_ID)
   partner.action_diagnose_portal_orders()
   ```

2. Revisar logs para identificar el problema

3. Verificar que el partner tiene usuario de portal:
   ```python
   partner.user_ids  # Debe tener al menos 1 usuario
   ```

### Pedidos de contactos hijos no aparecen

Verificar que el commercial_partner_id sea correcto:

```python
parent = env['res.partner'].browse(PARENT_ID)
child = env['res.partner'].browse(CHILD_ID)

print(f"Parent commercial: {parent.commercial_partner_id.id}")
print(f"Child commercial: {child.commercial_partner_id.id}")
# Deben ser iguales
```

## Tests

Ejecutar tests:

```bash
odoo-bin -d test_db --test-enable --test-tags portal_b2b_base --stop-after-init
```

## Soporte

Si el problema persiste después de aplicar todas las soluciones:

1. Ejecutar diagnóstico completo
2. Revisar logs del servidor
3. Contactar con el equipo de desarrollo con los logs y resultados del diagnóstico
