/** @odoo-module **/

(function() {
    'use strict';

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        const formOrder = document.getElementById('form-crear-pedido');
        if (formOrder) {
            inicializarFormularioPedido(formOrder);
        }
    }

    function inicializarFormularioPedido(form) {
        const btnSubmit = form.querySelector('button[type="submit"]');
        const orderLinesContainer = document.getElementById('order-lines-container');
        const btnAddLine = document.getElementById('btn-add-line');
        
        let lineCounter = 0;

        // Añadir línea de producto
        if (btnAddLine) {
            btnAddLine.addEventListener('click', function() {
                añadirLineaPedido(orderLinesContainer, lineCounter++);
            });
        }

        // Añadir primera línea automáticamente
        añadirLineaPedido(orderLinesContainer, lineCounter++);

        // Gestión de archivos
        const inputDeliveryNotes = document.getElementById('input-delivery-notes');
        const inputLabels = document.getElementById('input-labels');

        if (inputDeliveryNotes) {
            inputDeliveryNotes.addEventListener('change', function() {
                validarArchivos(this, 10, 'delivery-notes-list');
            });
        }

        if (inputLabels) {
            inputLabels.addEventListener('change', function() {
                validarArchivos(this, 10, 'labels-list');
            });
        }

        // Submit del formulario
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Validar líneas de pedido
            const orderLines = recopilarLineasPedido();
            if (orderLines.length === 0) {
                mostrarError('Debe añadir al menos un producto al pedido');
                return;
            }

            // Deshabilitar botón
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fa fa-spinner fa-spin me-2"></i>Creando pedido...';

            try {
                // Recopilar datos del formulario
                const formData = {
                    delivery_address_id: document.getElementById('input-delivery-address')?.value || null,
                    distributor_label_id: document.getElementById('input-label')?.value || null,
                    customer_delivery_reference: document.getElementById('input-customer-ref')?.value || '',
                    distributor_notes: document.getElementById('input-notes')?.value || '',
                    order_lines: orderLines,
                    customer_delivery_notes: await procesarArchivos(inputDeliveryNotes),
                    customer_labels: await procesarArchivos(inputLabels),
                };

                // Enviar al servidor
                const response = await fetch('/crear-pedido/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify(formData),
                });

                const result = await response.json();

                if (result.error) {
                    mostrarError(result.error.data?.message || result.error.message || 'Error desconocido');
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                    return;
                }

                if (result.result?.success) {
                    mostrarExito(result.result.message);
                    setTimeout(() => {
                        window.location.href = result.result.redirect;
                    }, 1500);
                } else {
                    mostrarError(result.result?.error || 'Error al crear el pedido');
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
                }

            } catch (error) {
                console.error('Error:', error);
                mostrarError('Error de conexión. Por favor, inténtelo de nuevo.');
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<i class="fa fa-check me-2"></i>Crear Pedido';
            }
        });
    }

    function añadirLineaPedido(container, index) {
        const lineHtml = `
            <div class="card mb-3 order-line" data-line-index="${index}">
                <div class="card-body">
                    <div class="row align-items-end">
                        <div class="col-md-5">
                            <label class="form-label">Producto *</label>
                            <select class="form-control product-select" required>
                                <option value="">Seleccionar producto...</option>
                                ${window.portalProducts?.map(p => 
                                    `<option value="${p.id}" data-price="${p.price}">${p.name} - ${p.price}€</option>`
                                ).join('') || ''}
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Cantidad *</label>
                            <input type="number" class="form-control quantity-input" 
                                   min="1" step="1" value="1" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Precio Unit.</label>
                            <input type="number" class="form-control price-input" 
                                   min="0" step="0.01" readonly>
                        </div>
                        <div class="col-md-1">
                            <button type="button" class="btn btn-danger btn-remove-line w-100" title="Eliminar">
                                <i class="fa fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', lineHtml);

        // Event listeners para la nueva línea
        const newLine = container.lastElementChild;
        const productSelect = newLine.querySelector('.product-select');
        const priceInput = newLine.querySelector('.price-input');
        const btnRemove = newLine.querySelector('.btn-remove-line');

        productSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const price = selectedOption.getAttribute('data-price') || 0;
            priceInput.value = price;
        });

        btnRemove.addEventListener('click', function() {
            if (container.querySelectorAll('.order-line').length > 1) {
                newLine.remove();
            } else {
                mostrarError('Debe mantener al menos una línea de pedido');
            }
        });
    }

    function recopilarLineasPedido() {
        const lines = [];
        const orderLines = document.querySelectorAll('.order-line');

        orderLines.forEach(line => {
            const productId = line.querySelector('.product-select').value;
            const quantity = line.querySelector('.quantity-input').value;
            const priceUnit = line.querySelector('.price-input').value;

            if (productId && quantity && parseFloat(quantity) > 0) {
                lines.push({
                    product_id: productId,
                    quantity: quantity,
                    price_unit: priceUnit || 0,
                });
            }
        });

        return lines;
    }

    async function procesarArchivos(input) {
        if (!input || !input.files || input.files.length === 0) {
            return [];
        }

        const files = [];
        for (let i = 0; i < input.files.length; i++) {
            const file = input.files[i];
            const base64 = await convertirArchivoABase64(file);
            files.push({
                filename: file.name,
                content: base64.split(',')[1], // Remover prefijo data:...
            });
        }

        return files;
    }

    function convertirArchivoABase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    function validarArchivos(input, maxMB, listId) {
        const fileList = document.getElementById(listId);
        if (!fileList) return;

        fileList.innerHTML = '';

        if (!input.files || input.files.length === 0) {
            return;
        }

        const maxBytes = maxMB * 1024 * 1024;
        let hasError = false;

        Array.from(input.files).forEach(file => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';

            if (file.size > maxBytes) {
                li.innerHTML = `
                    <span class="text-danger">
                        <i class="fa fa-exclamation-triangle me-2"></i>
                        ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)
                    </span>
                    <span class="badge bg-danger">Excede ${maxMB}MB</span>
                `;
                hasError = true;
            } else {
                li.innerHTML = `
                    <span>
                        <i class="fa fa-file me-2"></i>
                        ${file.name} (${(file.size / 1024).toFixed(2)}KB)
                    </span>
                    <span class="badge bg-success">OK</span>
                `;
            }

            fileList.appendChild(li);
        });

        if (hasError) {
            mostrarError(`Algunos archivos exceden el tamaño máximo de ${maxMB}MB`);
            input.value = '';
            fileList.innerHTML = '';
        }
    }

    function mostrarError(mensaje) {
        const alertHtml = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="fa fa-exclamation-circle me-2"></i>
                ${mensaje}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        const messageContainer = document.getElementById('order-message');
        if (messageContainer) {
            messageContainer.innerHTML = alertHtml;
            messageContainer.style.display = 'block';
            messageContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            alert(mensaje);
        }
    }

    function mostrarExito(mensaje) {
        const alertHtml = `
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="fa fa-check-circle me-2"></i>
                ${mensaje}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        const messageContainer = document.getElementById('order-message');
        if (messageContainer) {
            messageContainer.innerHTML = alertHtml;
            messageContainer.style.display = 'block';
            messageContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

})();
