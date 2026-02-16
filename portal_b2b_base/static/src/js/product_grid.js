/**
 * Portal B2B - Gestión de Grid de Productos
 * Versión compatible sin dependencias de Odoo
 */

(function() {
    'use strict';

    console.log('Portal B2B: Inicializando product_grid.js');

    // Esperar a que el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        console.log('Portal B2B: Product Grid inicializado');

        // Inicializar funcionalidades específicas según la página
        const currentPath = window.location.pathname;
        
        if (currentPath.includes('/crear-pedido')) {
            console.log('Portal B2B: Inicializando página crear pedido desde product_grid');
            inicializarCrearPedido();
        }
        
        // Gestión de direcciones de entrega
        inicializarGestionDirecciones();
    }

    /**
     * Inicializa funcionalidad de crear pedido
     */
    function inicializarCrearPedido() {
        const formCrearPedido = document.getElementById('form-crear-pedido');
        if (!formCrearPedido) {
            console.log('Portal B2B: Formulario crear pedido no encontrado');
            return;
        }

        console.log('Portal B2B: Inicializando grid de productos');

        // Variables del grid
        let currentPage = 1;
        let searchTerm = '';
        let categoryId = null;
        let sortBy = 'name';
        let selectedProducts = {};

        console.log('Portal B2B: Inicializando grid de productos');

        // ✅ EXPONER orderLines globalmente para portal.js
        window.orderLines = [];

        // Elementos del DOM
        const productFilter = document.getElementById('product-filter');
        const categoryFilter = document.getElementById('category-filter');
        const sortProducts = document.getElementById('sort-products');
        const productsGrid = document.getElementById('products-grid');
        const productsPagination = document.getElementById('products-pagination');
        const orderLinesBody = document.getElementById('order-lines-body');
        const orderTotal = document.getElementById('order-total');

        // Event listeners
        if (productFilter) {
            productFilter.addEventListener('input', function() {
                clearTimeout(this.filterTimeout);
                const self = this;
                this.filterTimeout = setTimeout(function() {
                    searchTerm = self.value;
                    currentPage = 1;
                    loadProducts();
                }, 500);
            });
        }

        if (categoryFilter) {
            categoryFilter.addEventListener('change', function() {
                categoryId = this.value || null;
                currentPage = 1;
                loadProducts();
            });
        }

        if (sortProducts) {
            sortProducts.addEventListener('change', function() {
                sortBy = this.value;
                currentPage = 1;
                loadProducts();
            });
        }

        // Cargar productos inicial
        loadCategories();
        loadProducts();

        /**
         * Carga categorías
         */
        async function loadCategories() {
            if (!categoryFilter) return;

            try {
                const response = await fetch('/api/productos/categorias', {
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
                
                if (data.result && data.result.categories) {
                    data.result.categories.forEach(function(cat) {
                        const option = document.createElement('option');
                        option.value = cat.id;
                        option.textContent = cat.name + ' (' + cat.product_count + ')';
                        categoryFilter.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Portal B2B: Error cargando categorías:', error);
            }
        }

        /**
         * Carga productos
         */
        async function loadProducts() {
            if (!productsGrid) return;

            productsGrid.innerHTML = '<div class="col-12 text-center py-5"><i class="fa fa-spinner fa-spin fa-3x"></i></div>';

            try {
                const response = await fetch('/api/productos/catalogo', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            page: currentPage,
                            limit: 20,
                            search: searchTerm,
                            category_id: categoryId,
                            sort: sortBy,
                        },
                        id: Math.floor(Math.random() * 1000000),
                    }),
                });

                const data = await response.json();

                if (data.error) {
                    productsGrid.innerHTML = '<div class="col-12 alert alert-danger">' + escapeHtml(data.error.message || 'Error desconocido') + '</div>';
                    return;
                }

                const result = data.result;
                
                if (result.error) {
                    productsGrid.innerHTML = '<div class="col-12 alert alert-danger">' + escapeHtml(result.error) + '</div>';
                    return;
                }

                renderProducts(result.products || []);
                renderPagination(result);

            } catch (error) {
                console.error('Portal B2B: Error cargando productos:', error);
                productsGrid.innerHTML = '<div class="col-12 alert alert-danger">Error de conexión</div>';
            }
        }

        /**
         * Renderiza productos
         */
        function renderProducts(products) {
            if (!productsGrid) return;

            productsGrid.innerHTML = '';

            if (products.length === 0) {
                productsGrid.innerHTML = '<div class="col-12 text-center py-5"><p class="text-muted">No se encontraron productos</p></div>';
                return;
            }

            products.forEach(function(product) {
                const stockClass = product.qty_available > 0 ? 'text-success' : 'text-danger';
                const stockText = product.qty_available > 0 
                    ? 'En stock: ' + product.qty_available 
                    : 'Sin stock';

                const cardDiv = document.createElement('div');
                cardDiv.className = 'col-md-3 col-sm-6 mb-4';
                cardDiv.innerHTML = `
                    <div class="card product-card h-100" data-product-id="${product.id}" style="cursor: pointer;">
                        <img src="${product.image_url}" class="card-img-top" alt="${escapeHtml(product.name)}" style="height: 200px; object-fit: contain; padding: 10px;">
                        <div class="card-body">
                            <h6 class="card-title">${escapeHtml(product.name)}</h6>
                            ${product.default_code ? '<p class="text-muted small mb-1">Ref: ' + escapeHtml(product.default_code) + '</p>' : ''}
                            <p class="card-text">
                                <strong class="text-primary">${product.list_price.toFixed(2)} €</strong>
                                <span class="text-muted">/ ${escapeHtml(product.uom_name)}</span>
                            </p>
                            <p class="small ${stockClass} mb-2">
                                <i class="fa fa-cube"></i> ${stockText}
                            </p>
                            <div class="input-group input-group-sm">
                                <input type="number" 
                                       class="form-control product-qty" 
                                       min="0" 
                                       step="1" 
                                       value="0"
                                       data-product-id="${product.id}"
                                       data-product-name="${escapeHtml(product.name)}"
                                       data-product-price="${product.list_price}">
                                <button class="btn btn-primary btn-add-product" 
                                        type="button"
                                        data-product-id="${product.id}">
                                    <i class="fa fa-plus"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;

                // Event listeners para la card
                const card = cardDiv.querySelector('.product-card');
                const qtyInput = cardDiv.querySelector('.product-qty');
                const addBtn = cardDiv.querySelector('.btn-add-product');

                card.addEventListener('click', function(e) {
                    if (e.target === qtyInput || e.target === addBtn) return;
                    const currentQty = parseInt(qtyInput.value) || 0;
                    qtyInput.value = currentQty + 1;
                });

                qtyInput.addEventListener('click', function(e) {
                    e.stopPropagation();
                });

                addBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const qty = parseFloat(qtyInput.value) || 0;
                    
                    if (qty <= 0) {
                        alert('Por favor, introduce una cantidad válida');
                        return;
                    }

                    addProductToOrder(product.id, product.name, qty, product.list_price);
                    qtyInput.value = 0;

                    // Efecto visual
                    card.classList.add('border-success');
                    setTimeout(function() {
                        card.classList.remove('border-success');
                    }, 1000);
                });

                productsGrid.appendChild(cardDiv);
            });
        }

        /**
         * Renderiza paginación
         */
        function renderPagination(data) {
            if (!productsPagination) return;

            productsPagination.innerHTML = '';

            if (data.total_pages <= 1) return;

            const nav = document.createElement('nav');
            const ul = document.createElement('ul');
            ul.className = 'pagination justify-content-center';

            if (data.has_prev) {
                const li = document.createElement('li');
                li.className = 'page-item';
                li.innerHTML = '<a class="page-link pagination-link" href="#" data-page="' + (data.page - 1) + '">Anterior</a>';
                ul.appendChild(li);
            }

            for (let i = 1; i <= data.total_pages; i++) {
                const li = document.createElement('li');
                li.className = 'page-item' + (i === data.page ? ' active' : '');
                li.innerHTML = '<a class="page-link pagination-link" href="#" data-page="' + i + '">' + i + '</a>';
                ul.appendChild(li);
            }

            if (data.has_next) {
                const li = document.createElement('li');
                li.className = 'page-item';
                li.innerHTML = '<a class="page-link pagination-link" href="#" data-page="' + (data.page + 1) + '">Siguiente</a>';
                ul.appendChild(li);
            }

            nav.appendChild(ul);
            productsPagination.appendChild(nav);

            // Event listeners para paginación
            ul.addEventListener('click', function(e) {
                if (e.target.classList.contains('pagination-link')) {
                    e.preventDefault();
                    currentPage = parseInt(e.target.dataset.page);
                    loadProducts();
                    window.scrollTo(0, 0);
                }
            });
        }

        /**
         * Añade producto al pedido
         */
        function addProductToOrder(productId, productName, qty, price) {
            if (!orderLinesBody) return;

            const emptyMsg = document.getElementById('empty-lines-message');
            if (emptyMsg) emptyMsg.style.display = 'none';

            // ✅ Actualizar window.orderLines (variable global)
            const existingLine = window.orderLines.find(line => line.product_id === productId);

            if (existingLine) {
                existingLine.qty += qty;
            } else {
                window.orderLines.push({
                    product_id: productId,
                    product_name: productName,
                    product_code: '',
                    qty: qty,
                    price: price,
                });
            }

            // Renderizar tabla visual
            renderizarLineasPedido();
        }

        /**
         * Renderiza las líneas del pedido en la tabla
         */
        function renderizarLineasPedido() {
            if (!orderLinesBody) return;

            if (window.orderLines.length === 0) {
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

            window.orderLines.forEach((line, index) => {
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
                        window.orderLines[index].qty = newQty;
                        renderizarLineasPedido();
                    }
                });
            });

            // Event listeners para eliminar
            document.querySelectorAll('.btn-remove-line').forEach(btn => {
                btn.addEventListener('click', function() {
                    const index = parseInt(this.dataset.index);
                    window.orderLines.splice(index, 1);
                    renderizarLineasPedido();
                });
            });

            actualizarTotal();
        }

        /**
         * Actualiza total del pedido
         */
        function actualizarTotal() {
            if (!orderTotal) return;

            const total = window.orderLines.reduce((sum, line) => sum + (line.qty * line.price), 0);
            orderTotal.textContent = total.toFixed(2) + ' €';
        }
    }

    /**
     * Inicializa gestión de direcciones de entrega
     */
    function inicializarGestionDirecciones() {
        console.log('Portal B2B: Inicializando gestión de direcciones');

        // Gestión de opciones de dirección de entrega
        const deliveryOptions = document.querySelectorAll('input[name="delivery_option"]');
        if (deliveryOptions.length > 0) {
            deliveryOptions.forEach(function(radio) {
                radio.addEventListener('change', function() {
                    const option = this.value;
                    
                    const savedSection = document.getElementById('saved-address-section');
                    const newForm = document.getElementById('new-address-form');
                    const preview = document.getElementById('address-preview');
                    
                    if (savedSection) savedSection.style.display = 'none';
                    if (newForm) newForm.style.display = 'none';
                    if (preview) preview.style.display = 'none';
                    
                    if (option === 'saved' && savedSection) {
                        savedSection.style.display = 'block';
                    } else if (option === 'new' && newForm) {
                        newForm.style.display = 'block';
                    }
                });
            });
        }
        
        // Gestión de selector de dirección guardada
        const savedAddressSelect = document.getElementById('saved-address-select');
        if (savedAddressSelect) {
            savedAddressSelect.addEventListener('change', function() {
                const selectedOption = this.options[this.selectedIndex];
                const preview = document.getElementById('address-preview');
                const previewContent = document.getElementById('address-preview-content');
                
                if (!selectedOption || !this.value) {
                    if (preview) preview.style.display = 'none';
                    return;
                }
                
                const fullAddress = selectedOption.getAttribute('data-full-address');
                const requireAppointment = selectedOption.getAttribute('data-require-appointment') === 'True';
                const tailLift = selectedOption.getAttribute('data-tail-lift') === 'True';
                
                if (fullAddress && previewContent) {
                    let html = '<p class="mb-1">' + escapeHtml(fullAddress) + '</p>';
                    
                    if (requireAppointment) {
                        html += '<p class="mb-0"><i class="fa fa-calendar"></i> Requiere cita previa</p>';
                    }
                    if (tailLift) {
                        html += '<p class="mb-0"><i class="fa fa-truck"></i> Requiere camión con pluma</p>';
                    }
                    
                    previewContent.innerHTML = html;
                    if (preview) preview.style.display = 'block';
                } else {
                    if (preview) preview.style.display = 'none';
                }
            });
        }
        
        console.log('Portal B2B: Gestión de direcciones inicializada');
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

})();
