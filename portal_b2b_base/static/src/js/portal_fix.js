/**
 * Portal B2B Theme - Fix Mínimo
 * Solo previene errores críticos de elementos null
 */

(function() {
    'use strict';

    console.log('[Portal B2B Fix] Inicializando protecciones mínimas');

    // Proteger getElementById para evitar errores con elementos inexistentes
    const originalGetElementById = document.getElementById;
    document.getElementById = function(id) {
        try {
            return originalGetElementById.call(this, id);
        } catch (e) {
            console.warn('[Portal B2B Fix] Error en getElementById:', id, e);
            return null;
        }
    };

    // Proteger querySelector
    const originalQuerySelector = Document.prototype.querySelector;
    Document.prototype.querySelector = function(selector) {
        try {
            return originalQuerySelector.call(this, selector);
        } catch (e) {
            console.warn('[Portal B2B Fix] Error en querySelector:', selector, e);
            return null;
        }
    };

    // Proteger querySelectorAll
    const originalQuerySelectorAll = Document.prototype.querySelectorAll;
    Document.prototype.querySelectorAll = function(selector) {
        try {
            return originalQuerySelectorAll.call(this, selector);
        } catch (e) {
            console.warn('[Portal B2B Fix] Error en querySelectorAll:', selector, e);
            return [];
        }
    };

    console.log('[Portal B2B Fix] Protecciones aplicadas correctamente');

})();
