/**
 * Portal B2B Theme - Animaciones y Efectos
 * Animaciones CSS y JavaScript para mejorar UX
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
        console.log('Portal B2B Theme Animations inicializado');

        // Agregar estilos de animación
        agregarEstilosAnimacion();

        // Inicializar animaciones de entrada
        inicializarAnimacionesEntrada();

        // Inicializar efectos hover
        inicializarEfectosHover();

        // Inicializar transiciones de página
        inicializarTransicionesPagina();
    }

    /**
     * Agrega estilos de animación al documento
     */
    function agregarEstilosAnimacion() {
        const style = document.createElement('style');
        style.textContent = `
            /* Animaciones de entrada */
            @keyframes fadeIn {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideInLeft {
                from {
                    opacity: 0;
                    transform: translateX(-30px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            @keyframes slideInRight {
                from {
                    opacity: 0;
                    transform: translateX(30px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes slideInDown {
                from {
                    opacity: 0;
                    transform: translateY(-30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes scaleIn {
                from {
                    opacity: 0;
                    transform: scale(0.95);
                }
                to {
                    opacity: 1;
                    transform: scale(1);
                }
            }

            @keyframes pulse {
                0%, 100% {
                    opacity: 1;
                }
                50% {
                    opacity: 0.5;
                }
            }

            @keyframes bounce {
                0%, 100% {
                    transform: translateY(0);
                }
                50% {
                    transform: translateY(-10px);
                }
            }

            /* Clases de animación */
            .animate-in {
                animation: fadeIn 0.6s ease-out forwards;
            }

            .animate-in.slide-left {
                animation: slideInLeft 0.6s ease-out forwards;
            }

            .animate-in.slide-right {
                animation: slideInRight 0.6s ease-out forwards;
            }

            .animate-in.slide-up {
                animation: slideInUp 0.6s ease-out forwards;
            }

            .animate-in.slide-down {
                animation: slideInDown 0.6s ease-out forwards;
            }

            .animate-in.scale {
                animation: scaleIn 0.6s ease-out forwards;
            }

            .pulse {
                animation: pulse 2s ease-in-out infinite;
            }

            .bounce {
                animation: bounce 1s ease-in-out infinite;
            }

            /* Transiciones suaves */
            .transition-all {
                transition: all 0.3s ease-in-out;
            }

            .transition-colors {
                transition: background-color 0.3s ease, color 0.3s ease;
            }

            .transition-transform {
                transition: transform 0.3s ease;
            }

            /* Efectos de hover */
            .hover-lift {
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }

            .hover-lift:hover {
                transform: translateY(-4px);
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            }

            .hover-scale {
                transition: transform 0.3s ease;
            }

            .hover-scale:hover {
                transform: scale(1.05);
            }

            .hover-glow {
                transition: box-shadow 0.3s ease;
            }

            .hover-glow:hover {
                box-shadow: 0 0 20px rgba(0, 102, 204, 0.3);
            }

            /* Carga */
            .loading {
                position: relative;
                pointer-events: none;
                opacity: 0.6;
            }

            .loading::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 20px;
                height: 20px;
                margin: -10px 0 0 -10px;
                border: 2px solid #0066CC;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }

            @keyframes spin {
                to {
                    transform: rotate(360deg);
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Inicializa animaciones de entrada para elementos
     */
    function inicializarAnimacionesEntrada() {
        const elementos = document.querySelectorAll('[data-animate]');
        
        elementos.forEach((el, index) => {
            const animacion = el.dataset.animate || 'fadeIn';
            const delay = el.dataset.delay || index * 100;
            
            el.style.animationDelay = `${delay}ms`;
            el.classList.add('animate-in', animacion);
        });
    }

    /**
     * Inicializa efectos hover en elementos
     */
    function inicializarEfectosHover() {
        // Efecto lift en cards
        document.querySelectorAll('.card').forEach(card => {
            card.classList.add('hover-lift');
        });

        // Efecto scale en botones
        document.querySelectorAll('.btn').forEach(btn => {
            btn.classList.add('transition-all');
        });

        // Efecto glow en elementos destacados
        document.querySelectorAll('[data-hover-glow]').forEach(el => {
            el.classList.add('hover-glow');
        });
    }

    /**
     * Inicializa transiciones de página
     */
    function inicializarTransicionesPagina() {
        // Agregar clase de carga al hacer clic en enlaces
        document.querySelectorAll('a:not([target="_blank"]):not([href^="#"])').forEach(link => {
            link.addEventListener('click', function(e) {
                // No aplicar si es un enlace de descarga o tiene clase especial
                if (this.hasAttribute('download') || this.classList.contains('no-transition')) {
                    return;
                }

                // Agregar efecto de carga
                const body = document.body;
                body.style.opacity = '0.8';
                body.style.transition = 'opacity 0.3s ease';
            });
        });

        // Restaurar opacidad cuando la página carga
        window.addEventListener('load', function() {
            document.body.style.opacity = '1';
        });
    }

    /**
     * Función para agregar animación a un elemento
     */
    window.animar = function(elemento, animacion = 'fadeIn', duracion = 600) {
        if (typeof elemento === 'string') {
            elemento = document.querySelector(elemento);
        }

        if (!elemento) return;

        elemento.style.animation = `${animacion} ${duracion}ms ease-out forwards`;
    };

    /**
     * Función para agregar efecto de carga
     */
    window.mostrarCarga = function(elemento) {
        if (typeof elemento === 'string') {
            elemento = document.querySelector(elemento);
        }

        if (elemento) {
            elemento.classList.add('loading');
        }
    };

    /**
     * Función para ocultar efecto de carga
     */
    window.ocultarCarga = function(elemento) {
        if (typeof elemento === 'string') {
            elemento = document.querySelector(elemento);
        }

        if (elemento) {
            elemento.classList.remove('loading');
        }
    };

})();
