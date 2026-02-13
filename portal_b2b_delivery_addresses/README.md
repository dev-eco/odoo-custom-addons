# Portal B2B - Direcciones de Entrega

Módulo complementario para gestión de múltiples direcciones de entrega en el Portal B2B.

## Características

### Gestión de Direcciones
- ✅ Crear múltiples direcciones de entrega por distribuidor
- ✅ Editar información de direcciones
- ✅ Desactivar direcciones (soft delete)
- ✅ Marcar dirección como predeterminada
- ✅ Alias personalizados para cada dirección

### Información de Dirección
- ✅ Datos completos: calle, ciudad, código postal, provincia, país
- ✅ Contacto específico en destino (nombre y teléfono)
- ✅ Requisitos especiales de entrega:
  - Cita previa requerida
  - Camión con pluma/elevador
- ✅ Notas personalizadas para el transportista

### Integración con Pedidos
- ✅ Selección de dirección de entrega en creación de pedidos
- ✅ Asignación automática de dirección predeterminada
- ✅ Visualización de dirección completa en pedidos

### Portal B2B
- ✅ Interfaz responsive Bootstrap 5
- ✅ Búsqueda y filtrado de direcciones
- ✅ Gestión completa desde portal
- ✅ API JSON para integración

## Instalación

1. Copiar el módulo a `addons/`
2. Actualizar lista de módulos
3. Instalar `portal_b2b_delivery_addresses`

## Uso

### Crear Dirección
1. Ir a `/mis-direcciones`
2. Hacer clic en "Nueva Dirección"
3. Completar formulario
4. Guardar

### Editar Dirección
1. Ir a `/mis-direcciones`
2. Hacer clic en "Editar" en la dirección
3. Modificar datos
4. Guardar

### Marcar como Predeterminada
1. Ir a `/mis-direcciones`
2. Hacer clic en "Por Defecto" en la dirección
3. Se asignará automáticamente en nuevos pedidos

### Usar en Pedidos
1. Crear nuevo pedido
2. Seleccionar cliente
3. Se asignará automáticamente su dirección predeterminada
4. Cambiar si es necesario

## Modelos

### delivery.address
Almacena información de direcciones de entrega.

**Campos principales:**
- `partner_id`: Distribuidor propietario
- `name`: Alias de la dirección
- `street`, `city`, `zip`: Datos de dirección
- `state_id`, `country_id`: Ubicación geográfica
- `contact_name`, `contact_phone`: Contacto en destino
- `require_appointment`: Requiere cita previa
- `tail_lift_required`: Requiere pluma
- `delivery_notes`: Notas especiales
- `is_default`: Dirección predeterminada
- `active`: Activa/desactivada

## API JSON

### Listar Direcciones
