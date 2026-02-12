/**
 * Portal B2B - JavaScript Frontend
 * Versión ultra-robusta con verificación exhaustiva
 * 
 * IMPORTANTE: portal_fix.js DEBE cargarse ANTES que este archivo
 */

(function() {
    'use strict';

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

        try {
            // Solo inicializar si estamos en la página correcta
            const currentPath = window.location.pathname;
            
            if (currentPath.includes('/crear-pedido')) {
                inicializarCrearPedido();
            }
            
            if (currentPath.includes('/mi-cuenta')) {
                inicializarMiCuenta();
            }
            
            // Estos pueden estar en crear-pedido
            if (document.getElementById('delivery-address-select')) {
                inicializarSelectorDirecciones();
            }
            
            if (document.getElementById('distributor-label-select')) {
                inicializarSelectorEtiquetas();
            }

        } catch (error) {
            console.error('Portal B2B: Error durante inicialización:', error);
        }
    }

    /**
     * Inicializa funcionalidad de crear pedido
     */
    function inicializarCrearPedido() {
        const productSearch = document.getElementById('product-search');
        const productResults = document.getElementById('product-results');
        const orderLinesBody = document.getElementById('order-lines-body');
        const formCrearPedido = document.getElementById('form-crear-pedido');

        // Verificar que TODOS los elementos existen
        if (!productSearch || !productResults || !orderLinesBody || !formCrearPedido) {
            console.log('Portal B2B: Página crear pedido - elementos no encontrados');
            return;
        }

        console.log('Portal B2B: Inicializando formulario crear pedido');

        let orderLines = [];
        let searchTimeout = null;

        // Búsqueda de productos al escribir
        productSearch.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                productResults.style.display = 'none';
                return;
            }

            searchTimeout = setTimeout(() => {
                buscarProductos(query);
            }, 300);
        });

        // Búsqueda al hacer clic en el botón
        const btnSearchProduct = document.getElementById('btn-search-product');
        if (btnSearchProduct) {
            btnSearchProduct.addEventListener('click', function() {
                const query = productSearch.value.trim();
                if (query.length >= 2) {
                    buscarProductos(query);
                }
            });
        }

        /**
         * Busca productos vía API
         */
        async function buscarProductos(query) {
            try {
                productResults.innerHTML = '<div class="list-group-item"><span class="spinner-border spinner-border-sm me-2"></span>Buscando...</div>';
                productResults.style.display = 'block';

                const response = await fetch('/api/productos/buscar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            query: query,
                            limit: 10,
                        },
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                // Manejar error JSON-RPC
                if (data.error) {
                    console.error('Portal B2B: Error JSON-RPC:', data.error);
                    const errorMsg = data.error.data?.message || data.error.message || 'Error desconocido';
                    productResults.innerHTML = `<div class="list-group-item text-danger">Error: ${escapeHtml(errorMsg)}</div>`;
                    return;
                }

                // Los datos están en data.result
                const result = data.result;
                
                if (!result) {
                    console.error('Portal B2B: Respuesta sin resultado');
                    productResults.innerHTML = '<div class="list-group-item text-danger">Error: Respuesta inválida del servidor</div>';
                    return;
                }
                
                if (result.error) {
                    console.error('Portal B2B: Error del servidor:', result.error);
                    productResults.innerHTML = `<div class="list-group-item text-danger">Error: ${escapeHtml(result.error)}</div>`;
                    return;
                }

                const products = result.products || [];
                
                if (products.length === 0) {
                    productResults.innerHTML = '<div class="list-group-item">No se encontraron productos</div>';
                    return;
                }

                mostrarResultadosProductos(products);

            } catch (error) {
                console.error('Portal B2B: Error al buscar productos:', error);
                productResults.innerHTML = '<div class="list-group-item text-danger">Error de conexión: ' + escapeHtml(error.message) + '</div>';
            }
        }

        /**
         * Muestra resultados de búsqueda de productos
         */
        function mostrarResultadosProductos(products) {
            productResults.innerHTML = '';

            if (products.length === 0) {
                productResults.innerHTML = '<div class="list-group-item">No se encontraron productos</div>';
                productResults.style.display = 'block';
                return;
            }

            products.forEach(product => {
                const item = document.createElement('a');
                item.href = '#';
                item.className = 'list-group-item list-group-item-action';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${escapeHtml(product.name)}</strong>
                            ${product.default_code ? `<br><small class="text-muted">Ref: ${escapeHtml(product.default_code)}</small>` : ''}
                        </div>
                        <div class="text-end">
                            <div><strong>${product.list_price.toFixed(2)} €</strong></div>
                            <small class="text-muted">Stock: ${product.qty_available}</small>
                        </div>
                    </div>
                `;

                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    agregarProductoAPedido(product);
                    productSearch.value = '';
                    productResults.style.display = 'none';
                });

                productResults.appendChild(item);
            });

            productResults.style.display = 'block';
        }

        /**
         * Agrega producto a las líneas del pedido
         */
        function agregarProductoAPedido(product) {
            const existingLine = orderLines.find(line => line.product_id === product.id);

            if (existingLine) {
                existingLine.qty += 1;
            } else {
                orderLines.push({
                    product_id: product.id,
                    product_name: product.name,
                    product_code: product.default_code,
                    qty: 1,
                    price: product.list_price,
                });
            }

            renderizarLineasPedido();
        }

        /**
         * Renderiza las líneas del pedido en la tabla
         */
        function renderizarLineasPedido() {
            // VERIFICAR que orderLinesBody existe antes de continuar
            if (!orderLinesBody) {
                console.error('Portal B2B: orderLinesBody no encontrado');
                return;
            }

            if (orderLines.length === 0) {
                orderLinesBody.innerHTML = `
                    <tr id="empty-lines-message">
                        <td colspan="5" class="text-center text-muted">
                            No hay productos agregados. Use el buscador arriba.
                        </td>
                    </tr>
                `;
                actualizarTotal();
                return;
            }

            orderLinesBody.innerHTML = '';

            orderLines.forEach((line, index) => {
                const subtotal = line.qty * line.price;

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <strong>${escapeHtml(line.product_name)}</strong>
                        ${line.product_code ? `<br><small class="text-muted">Ref: ${escapeHtml(line.product_code)}</small>` : ''}
                    </td>
                    <td class="text-center">
                        <input type="number" 
                               class="form-control form-control-sm text-center qty-input" 
                               data-index="${index}"
                               value="${line.qty}" 
                               min="1" 
                               step="1"
                               style="width: 80px; display: inline-block;"/>
                    </td>
                    <td class="text-end">${line.price.toFixed(2)} €</td>
                    <td class="text-end"><strong>${subtotal.toFixed(2)} €</strong></td>
                    <td class="text-center">
                        <button type="button" 
                                class="btn btn-sm btn-danger btn-remove-line" 
                                data-index="${index}">
                            <i class="fa fa-trash"></i>
                        </button>
                    </td>
                `;

                orderLinesBody.appendChild(row);
            });

            // Event listeners para cantidad
            document.querySelectorAll('.qty-input').forEach(input => {
                input.addEventListener('change', function() {
                    const index = parseInt(this.dataset.index);
                    const newQty = parseFloat(this.value);

                    if (newQty > 0) {
                        orderLines[index].qty = newQty;
                        renderizarLineasPedido();
                    }
                });
            });

            // Event listeners para eliminar
            document.querySelectorAll('.btn-remove-line').forEach(btn => {
                btn.addEventListener('click', function() {
                    const index = parseInt(this.dataset.index);
                    orderLines.splice(index, 1);
                    renderizarLineasPedido();
                });
            });

            actualizarTotal();
        }

        /**
         * Actualiza el total del pedido
         */
        function actualizarTotal() {
            const total = orderLines.reduce((sum, line) => sum + (line.qty * line.price), 0);
            const totalElement = document.getElementById('order-total');
            
            // VERIFICAR que el elemento existe antes de actualizar
            if (!totalElement) {
                console.warn('Portal B2B: Elemento order-total no encontrado');
                return;
            }

            totalElement.textContent = total.toFixed(2) + ' €';
        }

        /**
         * Submit del formulario crear pedido
         */
        formCrearPedido.addEventListener('submit', async function(e) {
            e.preventDefault();

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
                const notesElement = document.getElementById('order-notes');
                const deliveryAddressSelect = document.getElementById('delivery-address-select');
                const distributorLabelSelect = document.getElementById('distributor-label-select');
                const customerDeliveryRef = document.getElementById('customer-delivery-ref');
                const deliveryScheduleElement = document.getElementById('delivery-schedule');
                const clientOrderRefElement = document.getElementById('client-order-ref');

                const notes = notesElement ? notesElement.value : '';
                const deliveryAddressId = deliveryAddressSelect ? deliveryAddressSelect.value : null;
                const distributorLabelId = distributorLabelSelect ? distributorLabelSelect.value : null;
                const customerDeliveryReference = customerDeliveryRef ? customerDeliveryRef.value : '';
                const deliverySchedule = deliveryScheduleElement ? deliveryScheduleElement.value : '';
                const clientOrderRef = clientOrderRefElement ? clientOrderRefElement.value : '';

                // Procesar archivos adjuntos
                const transportLabelsFiles = await procesarArchivos(document.getElementById('transport-labels'));
                const customerNotesFiles = await procesarArchivos(document.getElementById('customer-delivery-notes'));
                const otherDocsFiles = await procesarArchivos(document.getElementById('other-documents'));

                const response = await fetch('/crear-pedido/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            lines: orderLines,
                            notes: notes,
                            delivery_address_id: deliveryAddressId,
                            distributor_label_id: distributorLabelId,
                            customer_delivery_reference: customerDeliveryReference,
                            delivery_schedule: deliverySchedule,
                            client_order_ref: clientOrderRef,
                            transport_labels: transportLabelsFiles,
                            customer_delivery_notes: customerNotesFiles,
                            other_documents: otherDocsFiles,
                        },
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }

                const data = await response.json();

                // Manejar respuesta JSON-RPC
                if (data.error) {
                    const errorMsg = data.error.data?.message || data.error.message || 'Error desconocido';
                    alert(errorMsg);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                    return;
                }

                const result = data.result;

                if (result.error) {
                    alert(result.error);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                    return;
                }

                if (result.success && result.redirect_url) {
                    // Redirigir al pedido creado
                    window.location.href = result.redirect_url;
                } else {
                    alert('Error: respuesta inesperada del servidor');
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

        // Inicializar gestión de archivos
        inicializarGestionArchivos();
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
     * Convierte archivos a base64 para envío
     */
    async function procesarArchivos(input) {
        if (!input || !input.files || input.files.length === 0) {
            return [];
        }
        
        const archivos = [];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        for (let file of input.files) {
            if (file.size > maxSize) {
                console.warn(`Archivo ${file.name} excede 10MB, omitiendo`);
                continue;
            }
            
            try {
                const base64 = await convertirArchivoABase64(file);
                archivos.push({
                    filename: file.name,
                    content: base64.split(',')[1], // Remover el prefijo data:...
                    mimetype: file.type
                });
            } catch (error) {
                console.error(`Error procesando archivo ${file.name}:`, error);
            }
        }
        
        return archivos;
    }

    /**
     * Convierte un archivo a base64
     */
    function convertirArchivoABase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
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

    /**
     * Inicializa selector de direcciones de entrega
     */
    function inicializarSelectorDirecciones() {
        const deliveryAddressSelect = document.getElementById('delivery-address-select');
        if (!deliveryAddressSelect) {
            console.log('Portal B2B: Selector de direcciones no encontrado');
            return;
        }

        console.log('Portal B2B: Inicializando selector de direcciones');

        const addressInfo = document.getElementById('address-info');
        const addressFull = document.getElementById('address-full');

        if (!addressInfo || !addressFull) {
            console.warn('Portal B2B: Elementos de dirección no encontrados');
            return;
        }

        deliveryAddressSelect.addEventListener('change', function() {
            try {
                const selectedOption = this.options[this.selectedIndex];
                if (!selectedOption) {
                    console.warn('Portal B2B: Opción seleccionada no encontrada');
                    return;
                }

                const fullAddress = selectedOption.getAttribute('data-full-address') || '';
                const requireAppointment = selectedOption.getAttribute('data-require-appointment') === 'True';
                const tailLift = selectedOption.getAttribute('data-tail-lift') === 'True';

                if (this.value) {
                    addressFull.textContent = fullAddress;
                    
                    const addressRequirements = document.getElementById('address-requirements');
                    const appointmentWarning = document.getElementById('appointment-warning');
                    const tailLiftWarning = document.getElementById('tail-lift-warning');
                    
                    if (addressRequirements) {
                        if (requireAppointment || tailLift) {
                            addressRequirements.style.display = 'block';
                            if (appointmentWarning) {
                                appointmentWarning.style.display = requireAppointment ? 'block' : 'none';
                            }
                            if (tailLiftWarning) {
                                tailLiftWarning.style.display = tailLift ? 'block' : 'none';
                            }
                        } else {
                            addressRequirements.style.display = 'none';
                        }
                    }

                    addressInfo.style.display = 'block';
                } else {
                    addressInfo.style.display = 'none';
                }
            } catch (error) {
                console.error('Portal B2B: Error en selector de direcciones:', error);
            }
        });

        // Trigger inicial
        if (deliveryAddressSelect.value) {
            deliveryAddressSelect.dispatchEvent(new Event('change'));
        }
    }

    /**
     * Inicializa selector de etiquetas cliente final
     */
    function inicializarSelectorEtiquetas() {
        const distributorLabelSelect = document.getElementById('distributor-label-select');
        if (!distributorLabelSelect) {
            console.log('Portal B2B: Selector de etiquetas no encontrado');
            return;
        }

        console.log('Portal B2B: Inicializando selector de etiquetas');

        const labelInfo = document.getElementById('label-info');
        const labelCustomerName = document.getElementById('label-customer-name');
        const customerDeliveryRefGroup = document.getElementById('customer-delivery-ref-group');

        if (!labelInfo || !labelCustomerName) {
            console.warn('Portal B2B: Elementos de etiqueta no encontrados');
            return;
        }

        distributorLabelSelect.addEventListener('change', function() {
            try {
                const selectedOption = this.options[this.selectedIndex];
                if (!selectedOption) {
                    console.warn('Portal B2B: Opción de etiqueta seleccionada no encontrada');
                    return;
                }

                const customerName = selectedOption.getAttribute('data-customer-name') || '';
                const customerRef = selectedOption.getAttribute('data-customer-ref') || '';
                const hideCompany = selectedOption.getAttribute('data-hide-company') === '1';
                const printDelivery = selectedOption.getAttribute('data-print-delivery') === '1';

                if (this.value) {
                    labelCustomerName.textContent = customerName;
                    
                    const labelCustomerRef = document.getElementById('label-customer-ref');
                    const labelCustomerRefContainer = document.getElementById('label-customer-ref-container');
                    
                    if (customerRef && labelCustomerRef && labelCustomerRefContainer) {
                        labelCustomerRef.textContent = customerRef;
                        labelCustomerRefContainer.style.display = 'block';
                    } else if (labelCustomerRefContainer) {
                        labelCustomerRefContainer.style.display = 'none';
                    }

                    const labelSettings = document.getElementById('label-settings');
                    const labelPrintDelivery = document.getElementById('label-print-delivery');
                    const labelHideCompany = document.getElementById('label-hide-company');
                    
                    if (labelSettings) {
                        if (hideCompany || printDelivery) {
                            labelSettings.style.display = 'block';
                            if (labelPrintDelivery) {
                                labelPrintDelivery.style.display = printDelivery ? 'block' : 'none';
                            }
                            if (labelHideCompany) {
                                labelHideCompany.style.display = hideCompany ? 'block' : 'none';
                            }
                        } else {
                            labelSettings.style.display = 'none';
                        }
                    }

                    // MOSTRAR campo de referencia cuando se selecciona etiqueta
                    if (customerDeliveryRefGroup) {
                        customerDeliveryRefGroup.style.display = 'block';
                    }
                    
                    labelInfo.style.display = 'block';
                } else {
                    labelInfo.style.display = 'none';
                    // OCULTAR cuando no hay etiqueta seleccionada
                    if (customerDeliveryRefGroup) {
                        customerDeliveryRefGroup.style.display = 'none';
                    }
                }
            } catch (error) {
                console.error('Portal B2B: Error en selector de etiquetas:', error);
            }
        });

        // Trigger inicial si ya hay una etiqueta seleccionada
        if (distributorLabelSelect.value) {
            distributorLabelSelect.dispatchEvent(new Event('change'));
        }
    }

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
     * Oculta el breadcrumb de "Pedidos de compra" (/my/purchase)
     * Solución robusta con múltiples estrategias
     */
    function ocultarBreadcrumbCompras() {
        try {
            // Estrategia 1: Buscar y ocultar enlaces directos a /my/purchase
            const enlacesCompra = document.querySelectorAll('a[href*="/my/purchase"]');
            
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

            console.log('Breadcrumbs de compra ocultados correctamente');

        } catch (error) {
            console.warn('Error al ocultar breadcrumbs de compra:', error);
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

})();
