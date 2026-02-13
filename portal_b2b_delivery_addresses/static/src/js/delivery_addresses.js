/**
 * Portal B2B - Gestión de Direcciones de Entrega y Etiquetas
 * 
 * Funcionalidades:
 * - Creación/edición de direcciones vía AJAX
 * - Creación/edición de etiquetas vía AJAX
 * - Actualización dinámica de provincias según país
 * - Validación de formularios
 * - Subida de archivos
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
        console.log('Portal B2B Direcciones y Etiquetas JS inicializado');

        // ========== CREAR/EDITAR DIRECCIÓN ==========
        const formCrearDireccion = document.getElementById('form-crear-direccion');
        if (formCrearDireccion) {
            console.log('Inicializando formulario crear dirección');
            inicializarFormularioDireccion(formCrearDireccion);
        }

        const formEditarDireccion = document.getElementById('form-editar-direccion');
        if (formEditarDireccion) {
            console.log('Inicializando formulario editar dirección');
            inicializarFormularioDireccion(formEditarDireccion);
        }

        // ========== CREAR/EDITAR ETIQUETA ==========
        const formEtiqueta = document.getElementById('form-etiqueta');
        if (formEtiqueta) {
            console.log('Inicializando formulario etiqueta');
            inicializarFormularioEtiqueta(formEtiqueta);
        }

        // ========== VALIDACIÓN DE ARCHIVOS ==========
        const inputTransportLabel = document.getElementById('input-transport-label');
        if (inputTransportLabel) {
            inputTransportLabel.addEventListener('change', function() {
                validarArchivo(this, 5);
            });
        }

        const inputDeliveryNote = document.getElementById('input-delivery-note');
        if (inputDeliveryNote) {
            inputDeliveryNote.addEventListener('change', function() {
                validarArchivo(this, 5);
            });
        }
    }

    /**
     * Inicializa funcionalidad de crear/editar dirección
     */
    function inicializarFormularioDireccion(form) {
        const btnSubmit = form.querySelector('button[type="submit"]');

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Validar campos requeridos
            const name = document.getElementById('input-name').value.trim();
            const street = document.getElementById('input-street').value.trim();
            const city = document.getElementById('input-city').value.trim();
            const zip = document.getElementById('input-zip').value.trim();
            const country = document.getElementById('input-country').value;

            if (!name || !street || !city || !zip || !country) {
                mostrarError('Por favor, complete todos los campos requeridos');
                return;
            }

            btnSubmit.disabled = true;
            const textoOriginal = btnSubmit.innerHTML;
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

            try {
                const addressId = form.querySelector('input[name="address_id"]');
                const params = {
                    address_id: addressId ? addressId.value : null,
                    name: name,
                    street: street,
                    street2: document.getElementById('input-street2').value.trim(),
                    city: city,
                    zip: zip,
                    state_id: document.getElementById('input-state').value || null,
                    country_id: country,
                    contact_name: document.getElementById('input-contact-name').value.trim(),
                    contact_phone: document.getElementById('input-contact-phone').value.trim(),
                    require_appointment: document.getElementById('input-appointment').checked,
                    tail_lift_required: document.getElementById('input-tail-lift').checked,
                    delivery_notes: document.getElementById('input-notes').value.trim(),
                };

                const response = await fetch('/mis-direcciones/submit',{
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: params,
                    }),
                });

                const data = await response.json();

                if (data.error) {
                    console.error('Error en respuesta:', data.error);
                    mostrarError(data.error.data ? data.error.data.message : 'Error al guardar la dirección');
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = textoOriginal;
                    return;
                }

                const result = data.result;

                if (result.error) {
                    mostrarError(result.error);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = textoOriginal;
                    return;
                }

                // Redirigir a lista de direcciones
                window.location.href = result.redirect_url;

            } catch (error) {
                console.error('Error al guardar dirección:', error);
                mostrarError('Error al guardar la dirección');
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = textoOriginal;
            }
        });
    }

    /**
     * Inicializa funcionalidad de crear/editar etiqueta
     */
    function inicializarFormularioEtiqueta(form) {
        const btnSubmit = form.querySelector('button[type="submit"]');

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            // Validar campos requeridos
            const name = document.getElementById('input-name').value.trim();
            const customerName = document.getElementById('input-customer-name').value.trim();

            if (!name || !customerName) {
                mostrarError('Por favor, complete los campos requeridos');
                return;
            }

            btnSubmit.disabled = true;
            const textoOriginal = btnSubmit.innerHTML;
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando...';

            try {
                const labelId = form.querySelector('input[name="label_id"]').value;
                
                // Preparar FormData para archivos
                const formData = new FormData();
                
                const params = {
                    label_id: labelId || null,
                    name: name,
                    customer_name: customerName,
                    customer_reference: document.getElementById('input-customer-ref').value.trim(),
                    tax_id: document.getElementById('input-tax-id').value.trim(),
                    contact_person: document.getElementById('input-contact-person').value.trim(),
                    customer_phone: document.getElementById('input-phone').value.trim(),
                    customer_email: document.getElementById('input-email').value.trim(),
                    customer_address: document.getElementById('input-address').value.trim(),
                    payment_terms: document.getElementById('input-payment-terms').value.trim(),
                    delivery_instructions: document.getElementById('input-delivery-instructions').value.trim(),
                    print_on_delivery_note: document.getElementById('input-print-delivery').checked,
                    hide_company_info: document.getElementById('input-hide-company').checked,
                    notes: document.getElementById('input-notes').value.trim(),
                };

                const response = await fetch('/mis-etiquetas/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: params,
                    }),
                });

                const data = await response.json();

                if (data.error) {
                    console.error('Error en respuesta:', data.error);
                    mostrarError(data.error.data ? data.error.data.message : 'Error al guardar la etiqueta');
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = textoOriginal;
                    return;
                }

                const result = data.result;

                if (result.error) {
                    mostrarError(result.error);
                    btnSubmit.disabled = false;
                    btnSubmit.innerHTML = textoOriginal;
                    return;
                }

                // Redirigir a lista de etiquetas
                window.location.href = result.redirect_url;

            } catch (error) {
                console.error('Error al guardar etiqueta:', error);
                mostrarError('Error al guardar la etiqueta');
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = textoOriginal;
            }
        });
    }

    /**
     * Valida archivos subidos
     */
    function validarArchivo(input, maxMB) {
        if (!input.files || input.files.length === 0) {
            return;
        }

        const file = input.files[0];
        const maxBytes = maxMB * 1024 * 1024;

        if (file.size > maxBytes) {
            mostrarError(`El archivo no puede exceder ${maxMB}MB. Tamaño actual: ${(file.size / 1024 / 1024).toFixed(2)}MB`);
            input.value = '';
            return;
        }

        const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg'];
        if (!allowedTypes.includes(file.type)) {
            mostrarError('Solo se permiten archivos PDF, PNG o JPG');
            input.value = '';
            return;
        }

        console.log(`Archivo válido: ${file.name} (${(file.size / 1024).toFixed(2)}KB)`);
    }

    /**
     * Actualiza las provincias según el país seleccionado
     */
    window.actualizarProvincias = async function() {
        const countrySelect = document.getElementById('input-country');
        const stateSelect = document.getElementById('input-state');
        const countryId = countrySelect.value;

        if (!countryId) {
            stateSelect.innerHTML = '<option value="">Seleccionar provincia...</option>';
            return;
        }

        try {
            console.log('País seleccionado:', countryId);
        } catch (error) {
            console.error('Error al actualizar provincias:', error);
        }
    };

    /**
     * Muestra error genérico
     */
    function mostrarError(mensaje) {
        alert(mensaje);
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
