/**
 * Módulo de Previsualización de Documentos
 */
odoo.define('document_automation.preview', [
    'web.core',
    'web.Widget',
    'web.basic_fields',
    'web.field_registry',
    'web.utils',
    'web.Dialog'
], function (require) {
    "use strict";

    // Importamos las dependencias necesarias de Odoo
    var core = require('web.core');
    var Widget = require('web.Widget');
    var FieldBinary = require('web.basic_fields').FieldBinary;
    var registry = require('web.field_registry');
    var utils = require('web.utils');
    var Dialog = require('web.Dialog');
    
    // Traducción
    var _t = core._t;
    var QWeb = core.qweb;

    /**
     * Widget de Previsualización de Documentos
     */
    var DocumentPreviewWidget = FieldBinary.extend({
        template: 'DocumentPreview',
        supportedTypes: ['application/pdf', 'image/jpeg', 'image/png', 'image/gif', 'image/tiff'],
        events: _.extend({}, FieldBinary.prototype.events, {
            'click .o_document_preview_button': '_onClickPreview',
        }),
        
        /**
         * Inicializa el widget de previsualización.
         */
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            this.previewEnabled = true;
            this.documentType = 'unknown';
            this.filename = record.data.filename || '';
            
            // Determina el tipo de documento basado en la extensión del archivo
            if (this.filename) {
                var extension = this.filename.split('.').pop().toLowerCase();
                if (['pdf'].includes(extension)) {
                    this.documentType = 'pdf';
                } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(extension)) {
                    this.documentType = 'image';
                }
            }
        },
        
        /**
         * Renderiza el widget y añade botones de previsualización cuando es aplicable.
         */
        _render: function () {
            // Primero renderizamos el campo binario normal
            this._super.apply(this, arguments);
            
            // Si tenemos un valor y es un tipo que podemos previsualizar
            if (this.value && this.previewEnabled && (this.documentType === 'pdf' || this.documentType === 'image')) {
                // Añadimos el botón de previsualización después del botón de descarga
                var $previewButton = $('<button>', {
                    class: 'btn btn-sm btn-primary o_document_preview_button ml-2',
                    type: 'button',
                    text: _t('Vista previa')
                });
                
                this.$el.find('.o_clear_file_button').after($previewButton);
            }
        },
        
        /**
         * Maneja el evento de clic en el botón de previsualización.
         */
        _onClickPreview: function () {
            var self = this;
            var fileData = this.value;
            
            if (!fileData) {
                return; // No hay datos para previsualizar
            }
            
            // Creamos el diálogo modal que contendrá la previsualización
            var $content = $('<div>', {
                class: 'o_document_preview_container'
            });
            
            // Diferentes manejos según el tipo de documento
            if (this.documentType === 'pdf') {
                // Para PDF, creamos un objeto embed
                $content.append($('<embed>', {
                    src: 'data:application/pdf;base64,' + fileData,
                    type: 'application/pdf',
                    width: '100%',
                    height: '500px'
                }));
            } else if (this.documentType === 'image') {
                // Para imágenes, usamos una etiqueta img
                $content.append($('<img>', {
                    src: 'data:image;base64,' + fileData,
                    class: 'img-fluid',
                    alt: this.filename
                }));
            }
            
            // Creamos y abrimos el diálogo modal
            var dialog = new Dialog(this, {
                title: _t('Previsualización: ') + this.filename,
                size: 'large',
                $content: $content,
                buttons: [{
                    text: _t('Cerrar'),
                    close: true
                }]
            });
            
            dialog.open();
        }
    });
    
    // Registramos nuestro widget para que esté disponible en las vistas
    registry.add('document_preview', DocumentPreviewWidget);
    
    /**
     * Widget para la vista Kanban que muestra miniaturas de documentos
     */
    var DocumentKanbanPreview = Widget.extend({
        template: 'DocumentKanbanPreview',
        events: {
            'click .o_document_kanban_preview': '_onClickPreview',
        },
        
        /**
         * Inicializa el widget para la vista Kanban
         */
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.document = options.document || {};
        },
        
        /**
         * Abre la previsualización cuando se hace clic en la miniatura
         */
        _onClickPreview: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            
            // Aquí podríamos implementar una previsualización en miniatura para la vista Kanban
        }
    });
    
    // Exportamos los widgets para su uso en otras partes del módulo
    return {
        DocumentPreviewWidget: DocumentPreviewWidget,
        DocumentKanbanPreview: DocumentKanbanPreview,
    };
});
