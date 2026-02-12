/**
 * Portal B2B Theme - Redirecciones de Rutas
 * Redirige automáticamente rutas en inglés a rutas en español
 * Se ejecuta ANTES que otros scripts
 */

(function() {
    'use strict';

    console.log('[Portal B2B Theme] portal_redirect.js cargado');

    // Mapeo de rutas en inglés a español
    const rutasRedireccion = {
        '/my': '/mi-portal',
        '/my/home': '/mi-portal',
        '/my/orders': '/mis-pedidos',
        '/my/invoices': '/mis-facturas',
        '/my/account': '/mi-cuenta',
        '/my/purchase': '/mis-pedidos',
    };

    // Función para redirigir si es necesario
    function verificarYRedirigir() {
        const rutaActual = window.location.pathname;
        
        console.log(`[Portal B2B Theme] Ruta actual: ${rutaActual}`);
        
        // Verificar si la ruta actual necesita redirección EXACTA
        for (const [rutaIngles, rutaEspanol] of Object.entries(rutasRedireccion)) {
            if (rutaActual === rutaIngles || rutaActual.startsWith(rutaIngles + '/')) {
                // Construir la nueva URL manteniendo query string y hash
                const queryString = window.location.search;
                const hash = window.location.hash;
                const nuevaRuta = rutaActual.replace(rutaIngles, rutaEspanol);
                const nuevaURL = nuevaRuta + queryString + hash;
                
                console.log(`[Portal B2B Theme] Redirigiendo de ${rutaActual} a ${nuevaURL}`);
                window.location.replace(nuevaURL);
                return;
            }
        }
    }

    // Ejecutar verificación INMEDIATAMENTE
    verificarYRedirigir();

    // También ejecutar cuando el DOM esté listo (por si acaso)
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', verificarYRedirigir);
    }

    // Interceptar clics en enlaces con rutas en inglés
    function interceptarEnlaces() {
        document.querySelectorAll('a[href^="/my"]').forEach(function(link) {
            const href = link.getAttribute('href');
            if (!href) return;

            try {
                const url = new URL(href, window.location.origin);
                const path = url.pathname;

                if (rutasRedireccion[path]) {
                    // Reemplazar href con versión en español
                    const newPath = rutasRedireccion[path];
                    const newHref = newPath + url.search + url.hash;
                    link.setAttribute('href', newHref);
                    console.log(`[Portal B2B Theme] Enlace actualizado: ${href} → ${newHref}`);
                }
            } catch (e) {
                console.warn(`[Portal B2B Theme] Error procesando enlace: ${href}`, e);
            }
        });
    }

    // Ejecutar interceptación cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', interceptarEnlaces);
    } else {
        interceptarEnlaces();
    }

    // Re-ejecutar interceptación cada vez que se añadan elementos al DOM
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length > 0) {
                interceptarEnlaces();
            }
        });
    });

    // Observar cambios en el body
    if (document.body) {
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        });
    }

})();
