/**
 * Portal B2B - Gestión de Devoluciones
 */

(function() {
    'use strict';

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        const currentPath = window.location.pathname;
        
        if (currentPath.includes('/crear-devolucion')) {
            console.log('Portal B2B: Inicializando crear devolución');
            inicializarCrearDevolucion();
        }
    }

    function inicializarCrearDevolucion() {
        const orderSelect = document.getElementById('order-select');
        const productsContainer = document.getElementById('products-container');
        
        if (!orderSelect || !productsContainer) {
            console.log('Portal B2B: Elementos de devolución no encontrados');
            return;
        }

        // Cargar pedidos con productos
        cargarPedidosConProductos();

        orderSelect.addEventListener('change', function() {
            const orderId = this.value;
            if (orderId) {
                mostrarProductosDelPedido(orderId);
            } else {
                productsContainer.innerHTML = '<p class="text-muted">Seleccione un pedido para ver los productos disponibles.</p>';
            }
        });
    }

    async function cargarPedidosConProductos() {
        try {
            const response = await fetch('/api/distributor/orders_products', {
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

            const data = await response.json();

            if (data.result && data.result.success) {
                window.distributorOrders = data.result.orders;
                poblarSelectorPedidos(data.result.orders);
            } else {
                console.error('Error cargando pedidos:', data.result?.error);
            }

        } catch (error) {
            console.error('Error cargando pedidos:', error);
        }
    }

    function poblarSelectorPedidos(orders) {
        const orderSelect = document.getElementById('order-select');
        
        orderSelect.innerHTML = '<option value="">Seleccionar pedido...</option>';
        
        orders.forEach(order => {
            const option = document.createElement('option');
            option.value = order.id;
            option.textContent = `${order.name} - ${order.date_order} (${order.products.length} productos)`;
            orderSelect.appendChild(option);
        });
    }

    function mostrarProductosDelPedido(orderId) {
        const order = window.distributorOrders.find(o => o.id == orderId);
        if (!order) return;

        const productsContainer = document.getElementById('products-container');
        
        let html = `
            <h5>Productos del pedido ${order.name}</h5>
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Producto</th>
                            <th>Cantidad Pedida</th>
                            <th>Precio Unit.</th>
                            <th>Cantidad a Devolver</th>
                            <th>Condición</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        order.products.forEach(product => {
            html += `
                <tr data-product-id="${product.id}">
                    <td>
                        <strong>${escapeHtml(product.name)}</strong>
                        ${product.default_code ? '<br><small class="text-muted">Ref: ' + escapeHtml(product.default_code) + '</small>' : ''}
                    </td>
                    <td>${product.quantity_ordered} ${product.uom_name}</td>
                    <td>${product.price_unit.toFixed(2)} €</td>
                    <td>
                        <input type="number" 
                               class="form-control form-control-sm return-qty" 
                               min="0" 
                               max="${product.quantity_ordered}"
                               step="1" 
                               value="0"
                               style="width: 100px;">
                    </td>
                    <td>
                        <select class="form-control form-control-sm return-condition">
                            <option value="new">Nuevo</option>
                            <option value="used">Usado</option>
                            <option value="damaged">Dañado</option>
                            <option value="defective">Defectuoso</option>
                        </select>
                    </td>
                    <td>
                        <button type="button" 
                                class="btn btn-sm btn-primary add-to-return"
                                data-product-id="${product.id}"
                                data-product-name="${escapeHtml(product.name)}"
                                data-price="${product.price_unit}">
                            <i class="fa fa-plus"></i> Añadir
                        </button>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        productsContainer.innerHTML = html;

        // Event listeners para botones "Añadir"
        document.querySelectorAll('.add-to-return').forEach(btn => {
            btn.addEventListener('click', function() {
                const row = this.closest('tr');
                const productId = this.dataset.productId;
                const productName = this.dataset.productName;
                const price = parseFloat(this.dataset.price);
                const qty = parseFloat(row.querySelector('.return-qty').value);
                const condition = row.querySelector('.return-condition').value;

                if (qty <= 0) {
                    alert('Introduzca una cantidad válida');
                    return;
                }

                añadirProductoADevolucion(productId, productName, qty, price, condition);
            });
        });
    }

    function añadirProductoADevolucion(productId, productName, qty, price, condition) {
        const returnLinesContainer = document.getElementById('return-lines-container');
        
        if (!returnLinesContainer) {
            // Crear contenedor si no existe
            const container = document.createElement('div');
            container.id = 'return-lines-container';
            container.innerHTML = `
                <h5>Productos a Devolver</h5>
                <div class="table-responsive">
                    <table class="table table-bordered" id="return-lines-table">
                        <thead>
                            <tr>
                                <th>Producto</th>
                                <th>Cantidad</th>
                                <th>Precio Unit.</th>
                                <th>Subtotal</th>
                                <th>Condición</th>
                                <th>Acción</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                        <tfoot>
                            <tr>
                                <th colspan="3">TOTAL</th>
                                <th id="return-total">0,00 €</th>
                                <th colspan="2"></th>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            `;
            
            document.getElementById('products-container').appendChild(container);
        }

        const tbody = document.querySelector('#return-lines-table tbody');
        const subtotal = qty * price;

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <strong>${escapeHtml(productName)}</strong>
                <input type="hidden" name="return_lines[product_id][]" value="${productId}">
            </td>
            <td>
                <input type="number" name="return_lines[quantity][]" value="${qty}" class="form-control form-control-sm" readonly style="width: 80px;">
            </td>
            <td>
                <input type="number" name="return_lines[price][]" value="${price}" class="form-control form-control-sm" readonly style="width: 100px;">
            </td>
            <td><strong>${subtotal.toFixed(2)} €</strong></td>
            <td>
                <input type="hidden" name="return_lines[condition][]" value="${condition}">
                ${condition}
            </td>
            <td>
                <button type="button" class="btn btn-sm btn-danger remove-return-line">
                    <i class="fa fa-trash"></i>
                </button>
            </td>
        `;

        tbody.appendChild(row);

        // Event listener para eliminar
        row.querySelector('.remove-return-line').addEventListener('click', function() {
            row.remove();
            actualizarTotalDevolucion();
        });

        actualizarTotalDevolucion();
    }

    function actualizarTotalDevolucion() {
        const rows = document.querySelectorAll('#return-lines-table tbody tr');
        let total = 0;

        rows.forEach(row => {
            const qty = parseFloat(row.querySelector('input[name="return_lines[quantity][]"]').value);
            const price = parseFloat(row.querySelector('input[name="return_lines[price][]"]').value);
            total += qty * price;
        });

        const totalElement = document.getElementById('return-total');
        if (totalElement) {
            totalElement.textContent = total.toFixed(2) + ' €';
        }
    }

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

})();
