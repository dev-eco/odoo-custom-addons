/**
 * Portal B2B Theme - JavaScript Principal
 * Funcionalidades generales del tema
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
        console.log('Portal B2B Theme JS inicializado');

        // Inicializar tooltips
        inicializarTooltips();

        // Inicializar popovers
        inicializarPopovers();

        // Inicializar smooth scroll
        inicializarSmoothScroll();

        // Inicializar navbar collapse
        inicializarNavbarCollapse();

        // Inicializar lazy loading
        inicializarLazyLoading();

        // Inicializar animaciones en scroll
        inicializarAnimacionesScroll();
    }

    /**
     * Inicializa tooltips de Bootstrap
     */
    function inicializarTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Inicializa popovers de Bootstrap
     */
    function inicializarPopovers() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    /**
     * Inicializa smooth scroll para enlaces internos
     */
    function inicializarSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                
                if (href === '#') {
                    return;
                }

                e.preventDefault();

                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Inicializa colapso de navbar en móvil
     */
    function inicializarNavbarCollapse() {
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');

        if (navbarToggler && navbarCollapse) {
            document.querySelectorAll('.navbar-collapse a').forEach(link => {
                link.addEventListener('click', function() {
                    if (navbarCollapse.classList.contains('show')) {
                        navbarToggler.click();
                    }
                });
            });
        }
    }

    /**
     * Inicializa lazy loading de imágenes
     */
    function inicializarLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.add('loaded');
                        observer.unobserve(img);
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    /**
     * Inicializa animaciones al hacer scroll
     */
    function inicializarAnimacionesScroll() {
        if ('IntersectionObserver' in window) {
            const animationObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                    }
                });
            }, {
                threshold: 0.1
            });

            document.querySelectorAll('[data-animate]').forEach(el => {
                animationObserver.observe(el);
            });
        }
    }

    /**
     * Función global para mostrar notificaciones
     */
    window.mostrarNotificacion = function(mensaje, tipo = 'info', duracion = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${tipo} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${mensaje}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        const container = document.querySelector('.alert-container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);

        if (duracion > 0) {
            setTimeout(() => {
                alertDiv.remove();
            }, duracion);
        }
    };

    /**
     * Función global para confirmar acciones
     */
    window.confirmar = function(mensaje) {
        return confirm(mensaje);
    };

    /**
     * Función global para formatear moneda
     */
    window.formatearMoneda = function(valor, moneda = '€') {
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: moneda === '€' ? 'EUR' : 'USD'
        }).format(valor);
    };

    /**
     * Función global para formatear fecha
     */
    window.formatearFecha = function(fecha, formato = 'es-ES') {
        return new Date(fecha).toLocaleDateString(formato);
    };

})();
