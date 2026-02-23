/**
 * Portal B2B Theme - Gestión de Preferencias
 * Maneja modo oscuro, accesibilidad y preferencias de usuario
 */

(function() {
    'use strict';

    console.log('[Portal B2B Preferences] Inicializando gestión de preferencias');

    // ========== CONSTANTES ==========

    const STORAGE_KEY = 'portal_b2b_preferences';
    const PREFERENCES_API = '/api/preferencias';

    // ========== CLASE PREFERENCES MANAGER ==========

    class PreferencesManager {
        constructor() {
            this.preferences = this.loadPreferences();
            this.init();
        }

        /**
         * Carga preferencias desde localStorage o servidor
         */
        loadPreferences() {
            // Intentar cargar del localStorage primero
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                try {
                    return JSON.parse(stored);
                } catch (e) {
                    console.warn('[Preferences] Error parsing stored preferences:', e);
                }
            }

            // Preferencias por defecto
            return {
                theme_mode: 'light',
                high_contrast: false,
                large_text: false,
                reduce_motion: false,
                screen_reader_mode: false,
                dashboard_layout: 'cards',
                orders_per_page: 20,
            };
        }

        /**
         * Guarda preferencias en localStorage y servidor
         */
        savePreferences() {
            // Guardar en localStorage
            localStorage.setItem(STORAGE_KEY, JSON.stringify(this.preferences));

            // Guardar en servidor (async)
            this.syncWithServer();
        }

        /**
         * Sincroniza preferencias con el servidor
         */
        syncWithServer() {
            fetch(PREFERENCES_API + '/actualizar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify(this.preferences),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('[Preferences] Preferencias sincronizadas con servidor');
                }
            })
            .catch(error => {
                console.warn('[Preferences] Error sincronizando con servidor:', error);
            });
        }

        /**
         * Obtiene token CSRF
         */
        getCsrfToken() {
            const name = 'csrf_token=';
            const decodedCookie = decodeURIComponent(document.cookie);
            const cookieArray = decodedCookie.split(';');
            
            for (let cookie of cookieArray) {
                cookie = cookie.trim();
                if (cookie.indexOf(name) === 0) {
                    return cookie.substring(name.length);
                }
            }
            
            // Alternativa: buscar en meta tag
            const meta = document.querySelector('meta[name="csrf_token"]');
            return meta ? meta.getAttribute('content') : '';
        }

        /**
         * Inicializa el gestor de preferencias
         */
        init() {
            this.applyPreferences();
            this.setupToggleButtons();
            this.setupSettingsPanel();
            this.detectSystemPreferences();
        }

        /**
         * Aplica las preferencias al DOM
         */
        applyPreferences() {
            const html = document.documentElement;
            const body = document.body;

            // Limpiar clases anteriores
            html.className = html.className
                .replace(/theme-\w+/g, '')
                .replace(/high-contrast/g, '')
                .replace(/large-text/g, '')
                .replace(/reduce-motion/g, '')
                .replace(/screen-reader-mode/g, '')
                .trim();

            // Aplicar tema
            if (this.preferences.theme_mode === 'auto') {
                html.classList.add('theme-auto');
            } else if (this.preferences.theme_mode === 'dark') {
                html.classList.add('theme-dark');
            } else {
                html.classList.add('theme-light');
            }

            // Aplicar accesibilidad
            if (this.preferences.high_contrast) {
                html.classList.add('high-contrast');
            }

            if (this.preferences.large_text) {
                html.classList.add('large-text');
            }

            if (this.preferences.reduce_motion) {
                html.classList.add('reduce-motion');
            }

            if (this.preferences.screen_reader_mode) {
                html.classList.add('screen-reader-mode');
            }

            // Aplicar layout dashboard
            html.setAttribute('data-dashboard-layout', this.preferences.dashboard_layout);

            console.log('[Preferences] Preferencias aplicadas:', this.preferences);
        }

        /**
         * Configura botones de toggle rápido
         */
        setupToggleButtons() {
            // Toggle tema oscuro
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.addEventListener('click', () => {
                    this.toggleTheme();
                });
                this.updateThemeToggleButton();
            }

            // Toggle alto contraste
            const contrastToggle = document.getElementById('contrast-toggle');
            if (contrastToggle) {
                contrastToggle.addEventListener('click', () => {
                    this.toggleHighContrast();
                });
            }

            // Toggle texto grande
            const textToggle = document.getElementById('text-size-toggle');
            if (textToggle) {
                textToggle.addEventListener('click', () => {
                    this.toggleLargeText();
                });
            }

            // Toggle reducir animaciones
            const motionToggle = document.getElementById('motion-toggle');
            if (motionToggle) {
                motionToggle.addEventListener('click', () => {
                    this.toggleReduceMotion();
                });
            }
        }

        /**
         * Configura panel de configuración
         */
        setupSettingsPanel() {
            const settingsBtn = document.getElementById('settings-btn');
            const settingsPanel = document.getElementById('settings-panel');
            const closeBtn = document.getElementById('settings-close-btn');
            const saveBtn = document.getElementById('save-preferences-btn');
            const resetBtn = document.getElementById('reset-preferences-btn');

            if (!settingsBtn || !settingsPanel) {
                console.warn('[Preferences] Panel de configuración no encontrado en el DOM');
                return;
            }

            console.log('[Preferences] Panel de configuración encontrado, configurando eventos');

            // Abrir panel
            settingsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.openPanel();
                
                // ✅ CARGAR CONTROLES DESPUÉS DE ABRIR
                setTimeout(() => {
                    this.setupSettingControls();
                }, 50);
            });

            // Cerrar panel con botón X
            if (closeBtn) {
                closeBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.closePanel();
                });
            }

            // Guardar preferencias
            if (saveBtn) {
                saveBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.savePreferencesFromPanel();
                    this.showNotification('Preferencias guardadas correctamente', 'success');
                    this.closePanel();
                });
            }

            // Resetear preferencias
            if (resetBtn) {
                resetBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.resetPreferences();
                });
            }

            // Cerrar al hacer clic fuera
            document.addEventListener('click', (e) => {
                if (!settingsBtn.contains(e.target) && 
                    !settingsPanel.contains(e.target) &&
                    settingsPanel.classList.contains('show')) {
                    this.closePanel();
                }
            });

            // Prevenir que clics dentro del panel lo cierren
            settingsPanel.addEventListener('click', (e) => {
                e.stopPropagation();
            });

            // Cerrar con tecla ESC
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && settingsPanel.classList.contains('show')) {
                    this.closePanel();
                }
            });
            
            console.log('[Preferences] Panel de configuración completamente configurado');
        }

        /**
         * Abre el panel de configuración
         */
        openPanel() {
            const panel = document.getElementById('settings-panel');
            if (panel) {
                panel.classList.remove('hiding');
                panel.classList.add('show');
                panel.style.display = 'block';
                console.log('[Preferences] Panel abierto');
            }
        }

        /**
         * Cierra el panel de configuración
         */
        closePanel() {
            const panel = document.getElementById('settings-panel');
            if (panel) {
                panel.classList.add('hiding');
                panel.classList.remove('show');
                
                // Esperar a que termine la animación antes de ocultar
                setTimeout(() => {
                    if (panel.classList.contains('hiding')) {
                        panel.style.display = 'none';
                        panel.classList.remove('hiding');
                    }
                }, 300);
                
                console.log('[Preferences] Panel cerrado');
            }
        }

        /**
         * Muestra notificación temporal
         */
        showNotification(message, type = 'info') {
            // Crear notificación
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} position-fixed shadow-lg`;
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            notification.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fa fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    <span>${message}</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Animar entrada
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }, 10);
            
            // Eliminar después de 3 segundos
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }

        /**
         * Abre el panel de configuración
         */
        openPanel() {
            const panel = document.getElementById('settings-panel');
            if (panel) {
                panel.classList.remove('hiding');
                panel.classList.add('show');
                panel.style.display = 'block';
                console.log('[Preferences] Panel abierto');
            }
        }

        /**
         * Cierra el panel de configuración
         */
        closePanel() {
            const panel = document.getElementById('settings-panel');
            if (panel) {
                panel.classList.add('hiding');
                panel.classList.remove('show');
                
                // Esperar a que termine la animación antes de ocultar
                setTimeout(() => {
                    if (panel.classList.contains('hiding')) {
                        panel.style.display = 'none';
                        panel.classList.remove('hiding');
                    }
                }, 300);
                
                console.log('[Preferences] Panel cerrado');
            }
        }

        /**
         * Muestra notificación temporal
         */
        showNotification(message, type = 'info') {
            // Crear notificación
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} position-fixed shadow-lg`;
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            notification.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fa fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    <span>${message}</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Animar entrada
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }, 10);
            
            // Eliminar después de 3 segundos
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }

        /**
         * Configura controles del panel de configuración
         * Solo carga los valores actuales (sin event listeners)
         */
        setupSettingControls() {
            console.log('[Preferences] Cargando valores actuales en controles...');
            
            // Tema
            const themeSelect = document.getElementById('theme-select');
            if (themeSelect) {
                themeSelect.value = this.preferences.theme_mode;
                console.log('[Preferences] Tema cargado:', this.preferences.theme_mode);
            }

            // Alto contraste
            const contrastCheck = document.getElementById('contrast-check');
            if (contrastCheck) {
                contrastCheck.checked = this.preferences.high_contrast;
                console.log('[Preferences] Alto contraste cargado:', this.preferences.high_contrast);
            }

            // Texto grande
            const textCheck = document.getElementById('text-check');
            if (textCheck) {
                textCheck.checked = this.preferences.large_text;
                console.log('[Preferences] Texto grande cargado:', this.preferences.large_text);
            }

            // Reducir animaciones
            const motionCheck = document.getElementById('motion-check');
            if (motionCheck) {
                motionCheck.checked = this.preferences.reduce_motion;
                console.log('[Preferences] Reducir movimiento cargado:', this.preferences.reduce_motion);
            }

            // Modo lector de pantalla
            const screenReaderCheck = document.getElementById('screen-reader-check');
            if (screenReaderCheck) {
                screenReaderCheck.checked = this.preferences.screen_reader_mode;
                console.log('[Preferences] Modo lector cargado:', this.preferences.screen_reader_mode);
            }

            // Layout dashboard
            const layoutSelect = document.getElementById('layout-select');
            if (layoutSelect) {
                layoutSelect.value = this.preferences.dashboard_layout;
                console.log('[Preferences] Layout cargado:', this.preferences.dashboard_layout);
            }

            // Pedidos por página
            const perPageSelect = document.getElementById('per-page-select');
            if (perPageSelect) {
                perPageSelect.value = this.preferences.orders_per_page;
                console.log('[Preferences] Por página cargado:', this.preferences.orders_per_page);
            }
            
            console.log('[Preferences] Todos los controles cargados correctamente');
        }

        /**
         * Guarda preferencias desde el panel
         */
        savePreferencesFromPanel() {
            console.log('[Preferences] Guardando preferencias desde panel...');
            
            // Leer valores del panel
            const themeSelect = document.getElementById('theme-select');
            const contrastCheck = document.getElementById('contrast-check');
            const textCheck = document.getElementById('text-check');
            const motionCheck = document.getElementById('motion-check');
            const screenReaderCheck = document.getElementById('screen-reader-check');
            const layoutSelect = document.getElementById('layout-select');
            const perPageSelect = document.getElementById('per-page-select');
            
            if (themeSelect) {
                this.preferences.theme_mode = themeSelect.value;
                console.log('[Preferences] Tema:', themeSelect.value);
            }
            
            if (contrastCheck) {
                this.preferences.high_contrast = contrastCheck.checked;
                console.log('[Preferences] Alto contraste:', contrastCheck.checked);
            }
            
            if (textCheck) {
                this.preferences.large_text = textCheck.checked;
                console.log('[Preferences] Texto grande:', textCheck.checked);
            }
            
            if (motionCheck) {
                this.preferences.reduce_motion = motionCheck.checked;
                console.log('[Preferences] Reducir movimiento:', motionCheck.checked);
            }
            
            if (screenReaderCheck) {
                this.preferences.screen_reader_mode = screenReaderCheck.checked;
                console.log('[Preferences] Modo lector:', screenReaderCheck.checked);
            }
            
            if (layoutSelect) {
                this.preferences.dashboard_layout = layoutSelect.value;
                console.log('[Preferences] Layout:', layoutSelect.value);
            }
            
            if (perPageSelect) {
                this.preferences.orders_per_page = parseInt(perPageSelect.value);
                console.log('[Preferences] Por página:', perPageSelect.value);
            }
            
            // Aplicar y guardar
            this.applyPreferences();
            this.savePreferences();
            
            console.log('[Preferences] Preferencias guardadas:', this.preferences);
        }

        /**
         * Alterna entre tema claro y oscuro
         */
        toggleTheme() {
            if (this.preferences.theme_mode === 'light') {
                this.setTheme('dark');
            } else {
                this.setTheme('light');
            }
        }

        /**
         * Establece el tema
         */
        setTheme(mode) {
            this.preferences.theme_mode = mode;
            this.applyPreferences();
            this.savePreferences();
            this.updateThemeToggleButton();
        }

        /**
         * Actualiza el icono del botón de tema
         */
        updateThemeToggleButton() {
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                const icon = themeToggle.querySelector('i');
                if (icon) {
                    if (this.preferences.theme_mode === 'dark') {
                        icon.className = 'fa fa-sun';
                        themeToggle.title = 'Cambiar a modo claro';
                    } else {
                        icon.className = 'fa fa-moon';
                        themeToggle.title = 'Cambiar a modo oscuro';
                    }
                }
            }
        }

        /**
         * Alterna alto contraste
         */
        toggleHighContrast() {
            this.preferences.high_contrast = !this.preferences.high_contrast;
            this.applyPreferences();
            this.savePreferences();
        }

        /**
         * Alterna texto grande
         */
        toggleLargeText() {
            this.preferences.large_text = !this.preferences.large_text;
            this.applyPreferences();
            this.savePreferences();
        }

        /**
         * Alterna reducir animaciones
         */
        toggleReduceMotion() {
            this.preferences.reduce_motion = !this.preferences.reduce_motion;
            this.applyPreferences();
            this.savePreferences();
        }

        /**
         * Detecta preferencias del sistema
         */
        detectSystemPreferences() {
            // Si está en modo automático, detectar preferencia del sistema
            if (this.preferences.theme_mode === 'auto') {
                const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
                
                darkModeQuery.addEventListener('change', (e) => {
                    this.applyPreferences();
                });
            }

            // Detectar preferencia de reducir movimiento
            const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
            if (motionQuery.matches && !this.preferences.reduce_motion) {
                console.log('[Preferences] Sistema prefiere reducir movimiento');
                this.preferences.reduce_motion = true;
                this.applyPreferences();
            }
        }

        /**
         * Resetea preferencias a valores por defecto
         */
        resetPreferences() {
            if (confirm('¿Está seguro de que desea resetear todas las preferencias a los valores por defecto?')) {
                this.preferences = {
                    theme_mode: 'light',
                    high_contrast: false,
                    large_text: false,
                    reduce_motion: false,
                    screen_reader_mode: false,
                    dashboard_layout: 'cards',
                    orders_per_page: 20,
                };
                
                // Actualizar controles del panel
                const themeSelect = document.getElementById('theme-select');
                const contrastCheck = document.getElementById('contrast-check');
                const textCheck = document.getElementById('text-check');
                const motionCheck = document.getElementById('motion-check');
                const screenReaderCheck = document.getElementById('screen-reader-check');
                const layoutSelect = document.getElementById('layout-select');
                const perPageSelect = document.getElementById('per-page-select');
                
                if (themeSelect) themeSelect.value = 'light';
                if (contrastCheck) contrastCheck.checked = false;
                if (textCheck) textCheck.checked = false;
                if (motionCheck) motionCheck.checked = false;
                if (screenReaderCheck) screenReaderCheck.checked = false;
                if (layoutSelect) layoutSelect.value = 'cards';
                if (perPageSelect) perPageSelect.value = '20';
                
                this.applyPreferences();
                this.savePreferences();
                this.showNotification('Preferencias reseteadas correctamente', 'success');
                
                console.log('[Preferences] Preferencias reseteadas');
            }
        }
    }

    // ========== INICIALIZACIÓN ==========

    // Función de inicialización con retry
    function initializePreferences() {
        const settingsBtn = document.getElementById('settings-btn');
        const settingsPanel = document.getElementById('settings-panel');
        
        if (settingsBtn && settingsPanel) {
            console.log('[Preferences] Elementos encontrados, inicializando...');
            window.preferencesManager = new PreferencesManager();
        } else {
            console.warn('[Preferences] Elementos no encontrados aún, reintentando en 500ms...');
            setTimeout(initializePreferences, 500);
        }
    }

    // Esperar a que el DOM esté completamente listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializePreferences);
    } else if (document.readyState === 'interactive') {
        // DOM está listo pero recursos externos pueden estar cargando
        setTimeout(initializePreferences, 100);
    } else {
        // DOM completamente cargado
        initializePreferences();
    }

    // Exponer métodos globales
    window.toggleTheme = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleTheme();
        }
    };

    window.toggleHighContrast = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleHighContrast();
        }
    };

    window.toggleLargeText = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleLargeText();
        }
    };

    window.toggleReduceMotion = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleReduceMotion();
        }
    };

    window.resetPreferences = () => {
        if (window.preferencesManager) {
            window.preferencesManager.resetPreferences();
        }
    };

    // Exponer métodos globales
    window.toggleTheme = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleTheme();
        }
    };

    window.toggleHighContrast = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleHighContrast();
        }
    };

    window.toggleLargeText = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleLargeText();
        }
    };

    window.toggleReduceMotion = () => {
        if (window.preferencesManager) {
            window.preferencesManager.toggleReduceMotion();
        }
    };

    window.resetPreferences = () => {
        if (window.preferencesManager) {
            window.preferencesManager.resetPreferences();
        }
    };

})();
