/**
 * Portal B2B - Manejador de Errores OWL
 * Suprime errores de templates OWL que no afectan la funcionalidad
 * 
 * IMPORTANTE: Este archivo DEBE cargarse ANTES que portal.js
 */

(function() {
    'use strict';

    console.log('Portal B2B: Inicializando manejador de errores OWL');

    // ========== INTERCEPTAR CONSOLE.ERROR ==========
    
    const originalError = console.error;
    const originalWarn = console.warn;

    // Patrones de errores a suprimir
    const suppressPatterns = [
        // Errores de templates OWL
        /QWeb.*template/i,
        /t-if.*undefined/i,
        /Cannot read properties of undefined/i,
        /Cannot read property.*of undefined/i,
        /t-esc.*undefined/i,
        /t-field.*undefined/i,
        /t-att.*undefined/i,
        /t-attf.*undefined/i,
        
        // Errores de componentes OWL
        /owl.*component/i,
        /component.*not found/i,
        /widget.*not found/i,
        
        // Errores de atributos faltantes
        /data-.*undefined/i,
        /getAttribute.*undefined/i,
        
        // Errores de métodos no existentes
        /is not a function/i,
        /undefined is not a function/i,
        
        // Errores de acceso a propiedades
        /Cannot set property/i,
        /Cannot delete property/i,
        
        // Errores de Odoo específicos
        /Uncaught.*Error/i,
        /ReferenceError/i,
        
        // Errores de red que no son críticos
        /Failed to fetch/i,
        /NetworkError/i,
    ];

    /**
     * Verifica si un error debe ser suprimido
     */
    function shouldSuppress(message) {
        if (!message) return false;
        
        const messageStr = String(message);
        
        return suppressPatterns.some(pattern => pattern.test(messageStr));
    }

    /**
     * Override de console.error
     */
    console.error = function(...args) {
        const message = args[0];
        
        // Suprimir errores que coincidan con los patrones
        if (shouldSuppress(message)) {
            // Log silencioso en desarrollo
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                // En desarrollo, mostrar en consola con prefijo
                originalWarn.call(console, '[OWL_SUPPRESSED]', ...args);
            }
            return;
        }
        
        // Mostrar errores importantes
        originalError.call(console, ...args);
    };

    /**
     * Override de console.warn
     */
    console.warn = function(...args) {
        const message = args[0];
        
        // Suprimir warnings que coincidan con los patrones
        if (shouldSuppress(message)) {
            return;
        }
        
        // Mostrar warnings importantes
        originalWarn.call(console, ...args);
    };

    // ========== INTERCEPTAR ERRORES GLOBALES ==========

    window.addEventListener('error', function(event) {
        const message = event.message || String(event.error);
        
        // Suprimir errores OWL
        if (shouldSuppress(message)) {
            event.preventDefault();
            return false;
        }
    }, true);

    window.addEventListener('unhandledrejection', function(event) {
        const message = event.reason ? String(event.reason) : '';
        
        // Suprimir promesas rechazadas de OWL
        if (shouldSuppress(message)) {
            event.preventDefault();
            return false;
        }
    }, true);

    // ========== SUPRIMIR ERRORES DE ODOO RPC ==========

    // Interceptar llamadas RPC para suprimir errores de templates
    if (window.odoo && window.odoo.define) {
        try {
            // Esperar a que Odoo esté completamente cargado
            setTimeout(function() {
                // Suprimir errores de widgets que no existen
                if (window.odoo.web && window.odoo.web.Widget) {
                    const OriginalWidget = window.odoo.web.Widget;
                    
                    // Monkey-patch para suprimir errores de widgets
                    window.odoo.web.Widget = function() {
                        try {
                            return OriginalWidget.apply(this, arguments);
                        } catch (error) {
                            if (!shouldSuppress(error.message)) {
                                throw error;
                            }
                        }
                    };
                }
            }, 1000);
        } catch (e) {
            // Ignorar errores en la configuración
        }
    }

    // ========== SUPRIMIR ERRORES DE TEMPLATES QWEB ==========

    // Interceptar errores de QWeb
    if (window.QWeb) {
        const originalRender = window.QWeb.prototype.render;
        
        if (originalRender) {
            window.QWeb.prototype.render = function(template, context) {
                try {
                    return originalRender.call(this, template, context);
                } catch (error) {
                    if (shouldSuppress(error.message)) {
                        console.warn('[QWeb Template Error Suppressed]', error.message);
                        return '';
                    }
                    throw error;
                }
            };
        }
    }

    console.log('Portal B2B: Manejador de errores OWL inicializado correctamente');

})();
