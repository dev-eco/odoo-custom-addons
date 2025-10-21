/* 
 * Invoice Batch Export - JavaScript Widget
 * =======================================
 * 
 * Funcionalidades JavaScript para mejorar la experiencia de usuario
 * en el módulo de exportación masiva de facturas.
 */

odoo.define('invoice_batch_export.BatchExportWidget', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var QWeb = core.qweb;
var _t = core._t;

/**
 * Widget personalizado para la selección de formato de compresión
 * Mejora la interfaz estándar con cards visuales y información adicional
 */
var CompressionFormatWidget = AbstractField.extend({
    className: 'o_field_compression_format',
    supportedFieldTypes: ['selection'],
    
    events: {
        'click .compression-format-option': '_onFormatClick',
        'keydown .compression-format-option': '_onFormatKeydown',
    },

    /**
     * Inicialización del widget
     */
    init: function () {
        this._super.apply(this, arguments);
        this.formatInfo = {
            'zip_fast': {
                icon: 'fa-archive',
                name: 'ZIP Rápido',
                description: 'Compresión rápida, archivos más grandes',
                color: '#2196F3'
            },
            'zip_balanced': {
                icon: 'fa-archive',
                name: 'ZIP Balanceado',
                description: 'Balance entre velocidad y tamaño',
                color: '#4CAF50'
            },
            'zip_best': {
                icon: 'fa-archive',
                name: 'ZIP Máxima Compresión',
                description: 'Máxima compresión, procesamiento más lento',
                color: '#FF9800'
            },
            '7z_normal': {
                icon: 'fa-file-archive-o',
                name: '7-Zip Normal',
                description: 'Excelente compresión, compatible 7-Zip',
                color: '#9C27B0'
            },
            '7z_ultra': {
                icon: 'fa-file-archive-o',
                name: '7-Zip Ultra',
                description: 'Máxima compresión posible',
                color: '#673AB7'
            },
            'tar_gz': {
                icon: 'fa-file-archive-o',
                name: 'TAR.GZ',
                description: 'Estándar Unix/Linux',
                color: '#795548'
            },
            'zip_password': {
                icon: 'fa-lock',
                name: 'ZIP con Contraseña',
                description: 'ZIP protegido con contraseña',
                color: '#F44336'
            }
        };
    },

    /**
     * Renderizar el widget
     */
    _render: function () {
        var self = this;
        var value = this.value;
        var options = this.field.selection || [];
        
        this.$el.empty();
        
        // Crear contenedor principal
        var $container = $('<div class="compression-format-selector">');
        
        // Renderizar cada opción
        options.forEach(function (option) {
            var optionValue = option[0];
            var optionLabel = option[1];
            var info = self.formatInfo[optionValue] || {
                icon: 'fa-file',
                name: optionLabel,
                description: 'Formato de compresión',
                color: '#666'
            };
            
            var $option = $('<div>')
                .addClass('compression-format-option')
                .attr('data-value', optionValue)
                .attr('tabindex', '0')
                .attr('role', 'button')
                .attr('aria-pressed', value === optionValue ? 'true' : 'false');
            
            if (value === optionValue) {
                $option.addClass('selected');
            }
            
            // Icono
            var $icon = $('<i>')
                .addClass('fa compression-format-icon')
                .addClass(info.icon)
                .css('color', info.color);
            
            // Nombre
            var $name = $('<div>')
                .addClass('compression-format-name')
                .text(info.name);
            
            // Descripción
            var $description = $('<div>')
                .addClass('compression-format-description')
                .text(info.description);
            
            $option.append($icon, $name, $description);
            $container.append($option);
        });
        
        this.$el.append($container);
    },

    /**
     * Manejar click en opción de formato
     */
    _onFormatClick: function (event) {
        event.preventDefault();
        var $target = $(event.currentTarget);
        var value = $target.attr('data-value');
        this._setValue(value);
    },

    /**
     * Manejar navegación con teclado
     */
    _onFormatKeydown: function (event) {
        if (event.which === 13 || event.which === 32) { // Enter o Espacio
            event.preventDefault();
            this._onFormatClick(event);
        }
    },

    /**
     * Establecer valor y actualizar visualización
     */
    _setValue: function (value) {
        this._super(value);
        this.$('.compression-format-option').removeClass('selected');
        this.$('.compression-format-option[data-value="' + value + '"]').addClass('selected');
        
        // Actualizar aria-pressed
        this.$('.compression-format-option').attr('aria-pressed', 'false');
        this.$('.compression-format-option[data-value="' + value + '"]').attr('aria-pressed', 'true');
    }
});

/**
 * Widget para mostrar progreso de exportación en tiempo real
 */
var ExportProgressWidget = AbstractField.extend({
    className: 'o_field_export_progress',
    supportedFieldTypes: ['integer', 'float'],
    
    /**
     * Renderizar la barra de progreso
     */
    _render: function () {
        var progress = Math.min(Math.max(this.value || 0, 0), 100);
        
        this.$el.empty();
        
        var $container = $('<div class="batch-export-progress">');
        var $bar = $('<div class="batch-export-progress-bar">')
            .css('width', progress + '%');
        
        var $text = $('<span class="batch-export-progress-text">')
            .text(Math.round(progress) + '%');
        
        $bar.append($text);
        $container.append($bar);
        this.$el.append($container);
        
        // Animación suave
        if (this._lastProgress !== progress) {
            $bar.addClass('batch-export-fadeIn');
            this._lastProgress = progress;
        }
    }
});

/**
 * Widget para mostrar estadísticas de exportación
 */
var ExportStatsWidget = AbstractField.extend({
    className: 'o_field_export_stats',
    supportedFieldTypes: ['text'],
    
    /**
     * Renderizar las estadísticas
     */
    _render: function () {
        try {
            var stats = JSON.parse(this.value || '{}');
            this.$el.empty();
            
            var $container = $('<div class="batch-export-stats">');
            
            // Facturas procesadas
            this._addStatCard($container, 'Procesadas', stats.processed || 0, 'success');
            
            // Facturas con error
            this._addStatCard($container, 'Errores', stats.errors || 0, 'error');
            
            // Tamaño del archivo
            if (stats.size) {
                this._addStatCard($container, 'Tamaño (MB)', 
                    (stats.size / (1024 * 1024)).toFixed(2), 'info');
            }
            
            // Tiempo de procesamiento
            if (stats.time) {
                this._addStatCard($container, 'Tiempo (s)', 
                    stats.time.toFixed(1), 'warning');
            }
            
            this.$el.append($container);
        } catch (e) {
            console.error('Error parsing export stats:', e);
        }
    },

    /**
     * Añadir tarjeta de estadística
     */
    _addStatCard: function ($container, label, value, type) {
        var $card = $('<div>')
            .addClass('batch-export-stat-card')
            .addClass(type);
        
        var $number = $('<div>')
            .addClass('batch-export-stat-number')
            .text(value);
        
        var $label = $('<div>')
            .addClass('batch-export-stat-label')
            .text(label);
        
        $card.append($number, $label);
        $container.append($card);
    }
});

/**
 * Widget para visualizar el log de procesamiento con formato
 */
var ProcessingLogWidget = AbstractField.extend({
    className: 'o_field_processing_log',
    supportedFieldTypes: ['text'],
    
    /**
     * Renderizar el log con formato
     */
    _render: function () {
        var log = this.value || '';
        
        this.$el.empty();
        
        var $log = $('<div class="batch-export-log">');
        
        // Procesar líneas del log para añadir formato
        var lines = log.split('\n');
        var formattedLog = lines.map(function (line) {
            if (line.startsWith('✓')) {
                return '<span class="log-success">' + line + '</span>';
            } else if (line.startsWith('✗')) {
                return '<span class="log-error">' + line + '</span>';
            } else if (line.startsWith('⚠')) {
                return '<span class="log-warning">' + line + '</span>';
            } else if (line.startsWith('ℹ')) {
                return '<span class="log-info">' + line + '</span>';
            }
            return line;
        }).join('\n');
        
        $log.html(formattedLog);
        this.$el.append($log);
        
        // Auto-scroll al final
        $log.scrollTop($log[0].scrollHeight);
    }
});

// Registrar widgets en el registro de campos
fieldRegistry.add('compression_format', CompressionFormatWidget);
fieldRegistry.add('export_progress', ExportProgressWidget);
fieldRegistry.add('export_stats', ExportStatsWidget);
fieldRegistry.add('processing_log', ProcessingLogWidget);

/**
 * Funciones utilitarias globales
 */
var BatchExportUtils = {
    
    /**
     * Mostrar notificación de éxito
     */
    showSuccess: function (message) {
        this._showNotification(message, 'success');
    },
    
    /**
     * Mostrar notificación de error
     */
    showError: function (message) {
        this._showNotification(message, 'danger');
    },
    
    /**
     * Mostrar notificación de información
     */
    showInfo: function (message) {
        this._showNotification(message, 'info');
    },
    
    /**
     * Mostrar notificación genérica
     */
    _showNotification: function (message, type) {
        var $notification = $('<div>')
            .addClass('alert alert-' + type + ' batch-export-fadeIn')
            .text(message);
        
        $('body').append($notification);
        
        setTimeout(function () {
            $notification.fadeOut(function () {
                $notification.remove();
            });
        }, 5000);
    },
    
    /**
     * Formatear tamaño de archivo
     */
    formatFileSize: function (bytes) {
        if (bytes === 0) return '0 Bytes';
        
        var k = 1024;
        var sizes = ['Bytes', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Formatear duración en segundos
     */
    formatDuration: function (seconds) {
        var hours = Math.floor(seconds / 3600);
        var minutes = Math.floor((seconds % 3600) / 60);
        var secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return hours + 'h ' + minutes + 'm ' + secs + 's';
        } else if (minutes > 0) {
            return minutes + 'm ' + secs + 's';
        } else {
            return secs + 's';
        }
    }
};

// Exponer utilidades globalmente
core.batch_export_utils = BatchExportUtils;

return {
    CompressionFormatWidget: CompressionFormatWidget,
    ExportProgressWidget: ExportProgressWidget,
    ExportStatsWidget: ExportStatsWidget,
    ProcessingLogWidget: ProcessingLogWidget,
    BatchExportUtils: BatchExportUtils
};

});
