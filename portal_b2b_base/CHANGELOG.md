# Changelog - Portal B2B Base

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [17.0.1.0.0] - 2024-01-15

### Added
- ✅ Versión inicial del módulo Portal B2B Base
- ✅ Gestión completa de pedidos desde portal
- ✅ Búsqueda avanzada de productos con autocompletado
- ✅ Control de límite de crédito en tiempo real
- ✅ Validación de crédito antes de confirmar pedidos
- ✅ Creación y repetición de pedidos
- ✅ Cancelación de pedidos desde portal
- ✅ Consulta de facturas con filtros
- ✅ Descarga de PDF de facturas
- ✅ Gestión de datos de cuenta
- ✅ Notificaciones de disponibilidad de stock
- ✅ API JSON para búsqueda de productos
- ✅ API JSON para información de stock
- ✅ Paginación y filtros avanzados
- ✅ Seguridad por record rules
- ✅ Multi-empresa compatible
- ✅ Responsive Bootstrap 5
- ✅ Estilos SCSS personalizados
- ✅ JavaScript moderno con AJAX
- ✅ Prevención de XSS
- ✅ CSRF token en formularios
- ✅ Documentación completa

### Security
- Implementación de record rules para acceso seguro
- Validación de permisos en cada ruta
- Escapado de HTML en plantillas
- CSRF tokens en formularios POST
- Validación de entrada de usuario

## Tipos de Cambios

- **Added**: Para nuevas funcionalidades
- **Changed**: Para cambios en funcionalidades existentes
- **Deprecated**: Para funcionalidades que serán removidas pronto
- **Removed**: Para funcionalidades removidas
- **Fixed**: Para corrección de bugs
- **Security**: Para cambios de seguridad

## Versionado

Este proyecto sigue [Semantic Versioning](https://semver.org/lang/es/):

- **MAJOR**: Cambios incompatibles con versiones anteriores
- **MINOR**: Nuevas funcionalidades compatibles hacia atrás
- **PATCH**: Correcciones de bugs compatibles hacia atrás

Formato: `ODOO_VERSION.MAJOR.MINOR.PATCH`

Ejemplo: `17.0.1.2.3`
- 17.0: Versión de Odoo
- 1: Versión mayor del módulo
- 2: Versión menor del módulo
- 3: Versión de parche
