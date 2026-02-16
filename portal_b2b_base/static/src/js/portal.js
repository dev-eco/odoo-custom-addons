/**
 * Portal B2B - JavaScript Frontend
 * Versión ultra-robusta con verificación exhaustiva
 * 
 * IMPORTANTE: portal_fix.js DEBE cargarse ANTES que este archivo
 */

(function() {
    'use strict';

    console.log('Portal B2B: Inicializando script principal');

    // Esperar a que el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        console.log('Portal B2B JS inicializado');

        // Ocultar breadcrumb de pedidos de compra
        ocultarBreadcrumbCompras();

        const currentPath = window.location.pathname;
        
        if (currentPath.includes('/crear-pedido')) {
            console.log('Portal B2B: Inicializando página crear pedido');
            inicializarCrearPedido();
        }
        
        if (currentPath.includes('/mi-cuenta')) {
            console.log('Portal B2B: Inicializando página mi cuenta');
            inicializarMiCuenta();
        }

        if (currentPath.includes('/crear-plantilla')) {
            console.log('Portal B2B: Inicializando página crear plantilla');
            inicializarCrearPlantillaDesdePedido();
        }
    }

    /**
     * Inicializa funcionalidad de crear pedido
     * NOTA: El grid de productos está gestionado por product_grid.js
     */
    function inicializarCrearPedido() {
        const formCrearPedido = document.getElementById('form-crear-pedido');

        if (!formCrearPedido) {
            console.log('Portal B2B: Formulario crear pedido no encontrado');
            return;
        }

        console.log('Portal B2B: Inicializando handlers de crear pedido');

        /**
         * Botón "Revisar Pedido"
         */
        const btnShowSummary = document.getElementById('btn-show-summary');
        if (btnShowSummary) {
            btnShowSummary.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Obtener orderLines desde product_grid.js
                const orderLines = window.orderLines || [];
                
                // Validar que hay productos
                if (!orderLines || orderLines.length === 0) {
                    alert('Debe agregar al menos un producto antes de revisar el pedido');
                    return;
                }
                
                // Generar resumen
                mostrarResumenPedido(orderLines);
                
                // Mostrar sección de resumen
                const summarySection = document.getElementById('order-summary-section');
                if (summarySection) {
                    summarySection.style.display = 'block';
                }
                
                // Ocultar botón "Revisar" y mostrar botón "Crear"
                btnShowSummary.style.display = 'none';
                const btnSubmit = document.getElementById('btn-submit-order');
                if (btnSubmit) {
                    btnSubmit.style.display = 'inline-block';
                }
                
                // Scroll suave al resumen
                if (summarySection) {
                    summarySection.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start' 
                    });
                }
            });
        }

        /**
         * Función para mostrar resumen
         */
        function mostrarResumenPedido(orderLines) {
            const summaryLines = document.getElementById('summary-lines');
            const summaryTotal = document.getElementById('summary-total');
            
            if (!summaryLines || !summaryTotal) {
                console.error('Portal B2B: Elementos de resumen no encontrados');
                alert('Error al mostrar el resumen. Por favor, recargue la página.');
                return;
            }
            
            summaryLines.innerHTML = '';
            
            if (!orderLines || orderLines.length === 0) {
                summaryLines.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No hay productos</td></tr>';
                summaryTotal.textContent = '0.00 €';
                return;
            }
            
            let total = 0;
            
            orderLines.forEach(line => {
                const subtotal = line.qty * line.price;
                total += subtotal;
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <strong>${escapeHtml(line.product_name)}</strong>
                        ${line.product_code ? `<br><small class="text-muted">Ref: ${escapeHtml(line.product_code)}</small>` : ''}
                    </td>
                    <td class="text-center">${line.qty}</td>
                    <td class="text-end">${line.price.toFixed(2)} €</td>
                    <td class="text-end"><strong>${subtotal.toFixed(2)} €</strong></td>
                `;
                summaryLines.appendChild(row);
            });
            
            summaryTotal.textContent = total.toFixed(2) + ' €';
            
            console.log('Portal B2B: Resumen generado -', orderLines.length, 'productos, Total:', total.toFixed(2), '€');
        }

        /**
         * Submit del formulario crear pedido
         */
        formCrearPedido.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Obtener orderLines desde product_grid.js
            const orderLines = window.orderLines || [];

            // Validar checkbox de confirmación
            const confirmCheckbox = document.getElementById('confirm-order-checkbox');
            if (!confirmCheckbox || !confirmCheckbox.checked) {
                alert('Debe confirmar que ha revisado el pedido');
                if (confirmCheckbox) confirmCheckbox.focus();
                return;
            }

            if (orderLines.length === 0) {
                alert('Debe agregar al menos un producto');
                return;
            }

            const btnSubmit = document.getElementById('btn-submit-order');
            if (!btnSubmit) {
                console.error('Portal B2B: Botón submit no encontrado');
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Creando...';

            try {
                // Recopilar datos del formulario
                const deliveryAddressSelect = document.getElementById('delivery-address-select');
                const distributorLabelSelect = document.getElementById('distributor-label-select');
                const notesElement = document.getElementById('order-notes');
                const deliveryScheduleElement = document.getElementById('delivery-schedule');
                const clientOrderRefElement = document.getElementById('client-order-ref');

                const formData = {
                    lines: orderLines,
                    notes: notesElement ? notesElement.value : '',
                    delivery_address_id: deliveryAddressSelect ? deliveryAddressSelect.value : null,
                    distributor_label_id: distributorLabelSelect ? distributorLabelSelect.value : null,
                    delivery_schedule: deliveryScheduleElement ? deliveryScheduleElement.value : '',
                    client_order_ref: clientOrderRefElement ? clientOrderRefElement.value : '',
                };

                console.log('Portal B2B: Enviando datos del pedido:', formData);

                const response = await fetch('/crear-pedido/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: formData,
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                console.log('Portal B2B: Respuesta del servidor:', data);

                if (data.error) {
                    const errorMsg = data.error.data?.message || data.error.message || 'Error desconocido';
                    alert('Error: ' + errorMsg);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                    return;
                }

                const result = data.result;

                if (result.error) {
                    alert('Error: ' + result.error);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                    return;
                }

                if (result.success && result.redirect_url) {
                    alert('¡Pedido creado exitosamente!');
                    window.location.href = result.redirect_url;
                } else {
                    alert('Error: respuesta inesperada del servidor');
                    console.error('Respuesta inesperada:', result);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                }

            } catch (error) {
                console.error('Portal B2B: Error al crear pedido:', error);
                alert('Error al crear el pedido: ' + error.message);
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
            }
        });
    }

    /**
     * Inicializa la gestión de archivos adjuntos
     */
    function inicializarGestionArchivos() {
        // Etiquetas de transporte
        const transportLabels = document.getElementById('transport-labels');
        if (transportLabels) {
            transportLabels.addEventListener('change', function() {
                mostrarArchivosSeleccionados(this, 'transport-labels-list');
            });
        }
        
        // Albaranes de cliente
        const customerNotes = document.getElementById('customer-delivery-notes');
        if (customerNotes) {
            customerNotes.addEventListener('change', function() {
                mostrarArchivosSeleccionados(this, 'delivery-notes-list');
            });
        }
        
        // Otros documentos
        const otherDocs = document.getElementById('other-documents');
        if (otherDocs) {
            otherDocs.addEventListener('change', function() {
                mostrarArchivosSeleccionados(this, 'other-documents-list');
            });
        }
    }

    /**
     * Muestra los archivos seleccionados
     */
    function mostrarArchivosSeleccionados(input, listId) {
        const listElement = document.getElementById(listId);
        if (!listElement) return;
        
        listElement.innerHTML = '';
        
        if (!input.files || input.files.length === 0) {
            return;
        }
        
        const ul = document.createElement('ul');
        ul.className = 'list-unstyled mt-2';
        
        let totalSize = 0;
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        Array.from(input.files).forEach((file, index) => {
            totalSize += file.size;
            
            const li = document.createElement('li');
            li.className = 'mb-1';
            
            const sizeKB = (file.size / 1024).toFixed(2);
            const sizeMB = (file.size / 1024 / 1024).toFixed(2);
            const sizeText = file.size > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;
            
            if (file.size > maxSize) {
                li.innerHTML = `
                    <span class="text-danger">
                        <i class="fa fa-exclamation-triangle me-2"></i>
                        ${escapeHtml(file.name)} (${sizeText}) - EXCEDE 10MB
                    </span>
                `;
            } else {
                li.innerHTML = `
                    <span class="text-success">
                        <i class="fa fa-check-circle me-2"></i>
                        ${escapeHtml(file.name)} (${sizeText})
                    </span>
                `;
            }
            
            ul.appendChild(li);
        });
        
        listElement.appendChild(ul);
        
        // Validar tamaño total
        if (totalSize > maxSize * 3) { // Máximo 30MB en total
            const warning = document.createElement('div');
            warning.className = 'alert alert-warning mt-2';
            warning.innerHTML = '<i class="fa fa-exclamation-triangle me-2"></i>El tamaño total de archivos no debe exceder 30MB';
            listElement.appendChild(warning);
        }
    }


    /**
     * Inicializa funcionalidad de mi cuenta
     */
    function inicializarMiCuenta() {
        const formUpdateAccount = document.getElementById('form-update-account');
        if (!formUpdateAccount) {
            console.log('Portal B2B: Formulario mi cuenta no encontrado');
            return;
        }

        console.log('Portal B2B: Inicializando formulario mi cuenta');

        formUpdateAccount.addEventListener('submit', async function(e) {
            e.preventDefault();

            const phoneInput = document.getElementById('input-phone');
            const mobileInput = document.getElementById('input-mobile');
            const emailInput = document.getElementById('input-email');

            if (!phoneInput || !mobileInput || !emailInput) {
                console.error('Portal B2B: Campos del formulario no encontrados');
                return;
            }

            const submitBtn = this.querySelector('button[type="submit"]');
            if (!submitBtn) {
                console.error('Portal B2B: Botón submit no encontrado en formulario mi cuenta');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

            try {
                const response = await fetch('/mi-cuenta/actualizar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            phone: phoneInput.value,
                            mobile: mobileInput.value,
                            email: emailInput.value,
                        },
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }

                const data = await response.json();

                if (data.error) {
                    const errorMsg = data.error.data?.message || data.error.message || 'Error desconocido';
                    alert(errorMsg);
                } else {
                    const result = data.result;
                    if (result.error) {
                        alert(result.error);
                    } else if (result.message) {
                        alert(result.message);
                    } else {
                        alert('Datos actualizados correctamente');
                    }
                }

                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa fa-save me-2"></i>Guardar Cambios';

            } catch (error) {
                console.error('Portal B2B: Error al actualizar cuenta:', error);
                alert('Error al actualizar los datos: ' + error.message);
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fa fa-save me-2"></i>Guardar Cambios';
            }
        });
    }

    // ❌ FUNCIONES ELIMINADAS: Movidas a product_grid.js
    // - inicializarSelectorDirecciones()
    // - inicializarSelectorEtiquetas()

    /**
     * Escapa HTML para prevenir XSS
     */
    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Verifica si un elemento existe en el DOM
     */
    function elementExists(id) {
        return document.getElementById(id) !== null;
    }

    /**
     * Obtiene un elemento de forma segura
     */
    function getElement(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Portal B2B: Elemento ${id} no encontrado`);
        }
        return element;
    }

    /**
     * Oculta el breadcrumb de "Pedidos de compra" (/my/purchase)
     * Solución robusta con múltiples estrategias
     */
    function ocultarBreadcrumbCompras() {
        try {
            // Estrategia 1: Buscar y ocultar enlaces directos a /my/purchase
            const enlacesCompra = document.querySelectorAll('a[href*="/my/purchase"]');
            
            if (enlacesCompra.length > 0) {
                console.log(`Portal B2B: Encontrados ${enlacesCompra.length} enlaces a /my/purchase`);
            }
            
            enlacesCompra.forEach(enlace => {
                // Ocultar el enlace
                enlace.style.display = 'none';
                
                // Ocultar el breadcrumb-item padre
                const breadcrumbItem = enlace.closest('.breadcrumb-item');
                if (breadcrumbItem) {
                    breadcrumbItem.style.display = 'none';
                }
                
                // Ocultar el separador siguiente
                const siguienteItem = breadcrumbItem?.nextElementSibling;
                if (siguienteItem && siguienteItem.classList.contains('breadcrumb-item')) {
                    siguienteItem.style.display = 'none';
                }
                
                // Ocultar el breadcrumb completo si es necesario
                const breadcrumb = enlace.closest('.breadcrumb, ol, ul');
                if (breadcrumb) {
                    // Verificar si todos los items están ocultos
                    const itemsVisibles = breadcrumb.querySelectorAll(
                        '.breadcrumb-item:not([style*="display: none"]), li:not([style*="display: none"])'
                    );
                    if (itemsVisibles.length === 0) {
                        breadcrumb.style.display = 'none';
                    }
                }
            });

            // Estrategia 2: Ocultar breadcrumbs vacíos
            const breadcrumbs = document.querySelectorAll('.breadcrumb, ol, ul');
            breadcrumbs.forEach(breadcrumb => {
                const itemsVisibles = breadcrumb.querySelectorAll(
                    '.breadcrumb-item:not([style*="display: none"]), li:not([style*="display: none"])'
                );
                if (itemsVisibles.length === 0) {
                    breadcrumb.style.display = 'none';
                }
            });

            console.log('Portal B2B: Breadcrumbs de compra ocultados correctamente');

        } catch (error) {
            console.warn('Portal B2B: Error al ocultar breadcrumbs de compra:', error);
        }
    }

    // Ejecutar también después de cambios dinámicos
    const observer = new MutationObserver(function() {
        ocultarBreadcrumbCompras();
    });

    // Observar cambios en el DOM
    if (document.body) {
        observer.observe(document.body, { 
            childList: true, 
            subtree: true,
            attributes: false,
            characterData: false
        });
    }

    /**
     * Inicializa formulario de crear plantilla desde pedido
     */
    function inicializarCrearPlantillaDesdePedido() {
        const formCreateTemplate = document.getElementById('form-create-template-from-order');
        if (!formCreateTemplate) {
            return;
        }

        console.log('Portal B2B: Inicializando formulario crear plantilla desde pedido');

        formCreateTemplate.addEventListener('submit', async function(e) {
            e.preventDefault();

            const templateNameInput = document.getElementById('template-name');
            const includeNotesCheckbox = document.getElementById('include-notes');
            const includeDeliveryAddressCheckbox = document.getElementById('include-delivery-address');
            const includeDistributorLabelCheckbox = document.getElementById('include-distributor-label');
            const btnSubmit = document.getElementById('btn-submit-template');

            if (!templateNameInput || !btnSubmit) {
                console.error('Portal B2B: Elementos del formulario no encontrados');
                return;
            }

            const templateName = templateNameInput.value.trim();

            if (!templateName) {
                alert('El nombre de la plantilla es obligatorio');
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creando...';

            try {
                // Obtener order_id de la URL
                const pathParts = window.location.pathname.split('/');
                const orderIdIndex = pathParts.indexOf('mis-pedidos') + 1;
                const orderId = parseInt(pathParts[orderIdIndex]);

                if (!orderId) {
                    throw new Error('No se pudo obtener el ID del pedido');
                }

                const response = await fetch(`/mis-pedidos/${orderId}/crear-plantilla/submit`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            template_name: templateName,
                            include_notes: includeNotesCheckbox ? includeNotesCheckbox.checked : false,
                            include_delivery_address: includeDeliveryAddressCheckbox ? includeDeliveryAddressCheckbox.checked : false,
                            include_distributor_label: includeDistributorLabelCheckbox ? includeDistributorLabelCheckbox.checked : false,
                        },
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }

                const data = await response.json();

                if (data.error) {
                    const errorMsg = data.error.data?.message || data.error.message || 'Error desconocido';
                    alert(errorMsg);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Plantilla';
                    return;
                }

                const result = data.result;

                if (result.error) {
                    alert(result.error);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Plantilla';
                    return;
                }

                if (result.success && result.redirect_url) {
                    window.location.href = result.redirect_url;
                } else {
                    alert('Plantilla creada exitosamente');
                    window.location.href = '/mis-plantillas';
                }

            } catch (error) {
                console.error('Portal B2B: Error al crear plantilla:', error);
                alert('Error al crear la plantilla: ' + error.message);
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Plantilla';
            }
        });
    }

    /**
     * ============================================
     * WIDGET DE CRÉDITO FLOTANTE
     * ============================================
     */

    /**
     * Inicializa el widget de crédito flotante
     */
    function inicializarWidgetCredito() {
        // Verificar si el usuario es distribuidor
        const creditWidgetRoot = document.getElementById('credit-widget-root');
        if (!creditWidgetRoot) {
            console.log('Portal B2B: Widget de crédito no disponible (usuario no es distribuidor)');
            return;
        }

        console.log('Portal B2B: Inicializando widget de crédito');

        // Estado del widget
        const widgetState = {
            limit: 0,
            used: 0,
            pending: 0,
            available: 0,
            percentage_used: 0,
            currency_symbol: '€',
            loading: true,
            error: null,
            collapsed: false,
            intervalId: null
        };

        // Crear estructura HTML del widget
        const widgetHTML = `
            <div class="credit-widget-floating" id="credit-widget">
                <div class="credit-widget-header" id="credit-widget-header">
                    <div class="credit-widget-title-group">
                        <i class="fa fa-check-circle" id="credit-status-icon"></i>
                        <span class="credit-widget-title">Estado de Crédito</span>
                    </div>
                    <div class="credit-widget-actions">
                        <button class="btn-refresh" id="credit-refresh-btn" title="Actualizar">
                            <i class="fa fa-refresh"></i>
                        </button>
                        <button class="btn-collapse" id="credit-collapse-btn" title="Minimizar/Expandir">
                            <i class="fa fa-chevron-up"></i>
                        </button>
                    </div>
                </div>
                
                <div class="credit-widget-content" id="credit-widget-content">
                    <!-- Loading State -->
                    <div class="credit-widget-loading" id="credit-loading">
                        <i class="fa fa-spinner fa-spin"></i>
                        <span>Cargando...</span>
                    </div>
                    
                    <!-- Error State -->
                    <div class="credit-widget-error" id="credit-error" style="display: none;">
                        <i class="fa fa-exclamation-triangle"></i>
                        <span id="credit-error-message"></span>
                    </div>
                    
                    <!-- Data Content -->
                    <div class="credit-widget-data" id="credit-data" style="display: none;">
                        <!-- Progress Bar -->
                        <div class="credit-progress-container">
                            <div class="credit-progress-bar">
                                <div class="credit-progress-fill" id="credit-progress-fill"></div>
                            </div>
                            <div class="credit-progress-label">
                                <span id="credit-percentage">0</span>% usado
                            </div>
                        </div>
                        
                        <!-- Info Grid -->
                        <div class="credit-info-grid">
                            <div class="credit-info-item">
                                <span class="credit-label">
                                    <i class="fa fa-credit-card"></i>
                                    Límite
                                </span>
                                <span class="credit-value" id="credit-limit">0,00 €</span>
                            </div>
                            
                            <div class="credit-info-item">
                                <span class="credit-label">
                                    <i class="fa fa-money"></i>
                                    Usado
                                </span>
                                <span class="credit-value text-muted" id="credit-used">0,00 €</span>
                            </div>
                            
                            <div class="credit-info-item" id="credit-pending-container" style="display: none;">
                                <span class="credit-label">
                                    <i class="fa fa-clock-o"></i>
                                    Pendiente
                                </span>
                                <span class="credit-value text-warning" id="credit-pending">0,00 €</span>
                            </div>
                            
                            <div class="credit-info-item credit-available">
                                <span class="credit-label">
                                    <i class="fa fa-check-circle"></i>
                                    Disponible
                                </span>
                                <span class="credit-value credit-value-large" id="credit-available">0,00 €</span>
                            </div>
                        </div>
                        
                        <!-- Tooltip Info -->
                        <div class="credit-tooltip-trigger">
                            <i class="fa fa-info-circle"></i>
                            <span>¿Qué significa esto?</span>
                            
                            <div class="credit-tooltip-content">
                                <div class="tooltip-item">
                                    <strong>Límite:</strong>
                                    <p>Crédito máximo autorizado para tu cuenta</p>
                                </div>
                                <div class="tooltip-item">
                                    <strong>Usado:</strong>
                                    <p>Facturas pendientes de pago</p>
                                </div>
                                <div class="tooltip-item">
                                    <strong>Pendiente:</strong>
                                    <p>Pedidos enviados esperando confirmación</p>
                                </div>
                                <div class="tooltip-item">
                                    <strong>Disponible:</strong>
                                    <p>Crédito real que puedes usar para nuevos pedidos</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Insertar widget en el DOM
        creditWidgetRoot.innerHTML = widgetHTML;

        // Referencias a elementos
        const widget = document.getElementById('credit-widget');
        const header = document.getElementById('credit-widget-header');
        const content = document.getElementById('credit-widget-content');
        const refreshBtn = document.getElementById('credit-refresh-btn');
        const collapseBtn = document.getElementById('credit-collapse-btn');
        const collapseIcon = collapseBtn.querySelector('i');
        
        const loadingEl = document.getElementById('credit-loading');
        const errorEl = document.getElementById('credit-error');
        const errorMessageEl = document.getElementById('credit-error-message');
        const dataEl = document.getElementById('credit-data');
        
        const statusIcon = document.getElementById('credit-status-icon');
        const progressFill = document.getElementById('credit-progress-fill');
        const percentageEl = document.getElementById('credit-percentage');
        const limitEl = document.getElementById('credit-limit');
        const usedEl = document.getElementById('credit-used');
        const pendingEl = document.getElementById('credit-pending');
        const pendingContainer = document.getElementById('credit-pending-container');
        const availableEl = document.getElementById('credit-available');

        /**
         * Formatea un número como moneda
         */
        function formatCurrency(amount) {
            return new Intl.NumberFormat('es-ES', {
                style: 'currency',
                currency: 'EUR',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
        }

        /**
         * Determina el color del estado según el porcentaje
         */
        function getStatusColor(percentage) {
            if (percentage >= 90) return 'danger';
            if (percentage >= 70) return 'warning';
            return 'success';
        }

        /**
         * Determina el icono según el estado
         */
        function getStatusIcon(percentage) {
            if (percentage >= 90) return 'fa-exclamation-triangle';
            if (percentage >= 70) return 'fa-exclamation-circle';
            return 'fa-check-circle';
        }

        /**
         * Actualiza la UI con los datos del estado
         */
        function updateUI() {
            // Ocultar loading y error
            loadingEl.style.display = 'none';
            errorEl.style.display = 'none';

            if (widgetState.error) {
                // Mostrar error
                errorMessageEl.textContent = widgetState.error;
                errorEl.style.display = 'flex';
                dataEl.style.display = 'none';
                return;
            }

            // Mostrar datos
            dataEl.style.display = 'block';

            // Actualizar valores
            limitEl.textContent = formatCurrency(widgetState.limit);
            usedEl.textContent = formatCurrency(widgetState.used);
            pendingEl.textContent = formatCurrency(widgetState.pending);
            availableEl.textContent = formatCurrency(widgetState.available);
            percentageEl.textContent = widgetState.percentage_used.toFixed(1);

            // Mostrar/ocultar pendiente
            if (widgetState.pending > 0) {
                pendingContainer.style.display = 'flex';
            } else {
                pendingContainer.style.display = 'none';
            }

            // Actualizar color disponible
            availableEl.className = 'credit-value credit-value-large ' + 
                (widgetState.available > 0 ? 'text-success' : 'text-danger');

            // Actualizar barra de progreso
            const percentage = Math.min(widgetState.percentage_used, 100);
            const statusColor = getStatusColor(percentage);
            progressFill.style.width = percentage + '%';
            progressFill.className = 'credit-progress-fill bg-' + statusColor;

            // Actualizar icono de estado
            const iconClass = getStatusIcon(percentage);
            statusIcon.className = 'fa ' + iconClass;

            // Actualizar clase del widget
            widget.className = 'credit-widget-floating status-' + statusColor + 
                (widgetState.collapsed ? ' collapsed' : '');
        }

        /**
         * Carga el estado de crédito desde el servidor
         */
        async function loadCreditStatus() {
            try {
                widgetState.loading = true;
                widgetState.error = null;

                // Mostrar spinner en botón refresh
                const refreshIcon = refreshBtn.querySelector('i');
                refreshIcon.classList.add('fa-spin');
                refreshBtn.disabled = true;

                const response = await fetch('/api/distributor/credit_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {},
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                // Manejar error JSON-RPC
                if (data.error) {
                    const errorMsg = data.error.data?.message || data.error.message || 'Error desconocido';
                    throw new Error(errorMsg);
                }

                const result = data.result;

                if (result.error) {
                    throw new Error(result.error);
                }

                if (result.success && result.data) {
                    // Actualizar estado
                    Object.assign(widgetState, result.data);
                    widgetState.loading = false;
                    widgetState.error = null;

                    console.log('Portal B2B: Estado de crédito actualizado', widgetState);
                } else {
                    throw new Error('Respuesta inválida del servidor');
                }

            } catch (error) {
                console.error('Portal B2B: Error al cargar estado de crédito:', error);
                widgetState.error = 'Error de conexión. Reintentando...';
                widgetState.loading = false;
            } finally {
                // Quitar spinner
                const refreshIcon = refreshBtn.querySelector('i');
                refreshIcon.classList.remove('fa-spin');
                refreshBtn.disabled = false;

                // Actualizar UI
                updateUI();
            }
        }

        /**
         * Alterna el estado colapsado
         */
        function toggleCollapse() {
            widgetState.collapsed = !widgetState.collapsed;
            
            if (widgetState.collapsed) {
                content.style.display = 'none';
                collapseIcon.className = 'fa fa-chevron-down';
                widget.classList.add('collapsed');
            } else {
                content.style.display = 'block';
                collapseIcon.className = 'fa fa-chevron-up';
                widget.classList.remove('collapsed');
            }
        }

        /**
         * Inicia el polling automático
         */
        function startPolling() {
            // Cargar inmediatamente
            loadCreditStatus();

            // Actualizar cada 30 segundos
            widgetState.intervalId = setInterval(() => {
                loadCreditStatus();
            }, 30000);

            console.log('Portal B2B: Polling de crédito iniciado (cada 30s)');
        }

        /**
         * Detiene el polling
         */
        function stopPolling() {
            if (widgetState.intervalId) {
                clearInterval(widgetState.intervalId);
                widgetState.intervalId = null;
                console.log('Portal B2B: Polling de crédito detenido');
            }
        }

        // Event Listeners
        refreshBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            loadCreditStatus();
        });

        collapseBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleCollapse();
        });

        header.addEventListener('click', function() {
            toggleCollapse();
        });

        // Iniciar polling
        startPolling();

        // Limpiar al salir de la página
        window.addEventListener('beforeunload', function() {
            stopPolling();
        });

        console.log('Portal B2B: Widget de crédito inicializado correctamente');
    }

})();
