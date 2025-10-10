odoo.define('document_automation.preview', function(require) {
    "use strict";

    // Importamos solo las dependencias esenciales
    var core = require('web.core');
    var _t = core._t;
    var QWeb = core.qweb;
    var FieldBinary = require('web.basic_fields').FieldBinary;
    var registry = require('web.field_registry');
    var Dialog = require('web.Dialog');

    /**
     * Widget de Previsualización de Documentos
     */
    var DocumentPreviewWidget = FieldBinary.extend({
        description: _t("Campo binario con vista previa"),
        supportedTypes: ['application/pdf', 'image/jpeg', 'image/png', 'image/gif', 'image/tiff'],
        events: _.extend({}, FieldBinary.prototype.events, {
            'click .o_document_preview_button': '_onClickPreview',
        }),
        
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            this.previewEnabled = true;
            this.documentType = 'unknown';
            this.filename = record.data.filename || '';
            
            if (this.filename) {
                var extension = this.filename.split('.').pop().toLowerCase();
                if (['pdf'].includes(extension)) {
                    this.documentType = 'pdf';
                } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(extension)) {
                    this.documentType = 'image';
                }
            }
        },
        
        _render: function () {
            this._super.apply(this, arguments);
            
            if (this.value && this.previewEnabled && (this.documentType === 'pdf' || this.documentType === 'image')) {
                var $previewButton = $('<button>', {
                    class: 'btn btn-sm btn-primary o_document_preview_button ms-2',  // ms-2 en lugar de ml-2 para BS5
                    type: 'button',
                    text: _t('Vista previa')
                });
                
                this.$el.find('.o_clear_file_button').after($previewButton);
            }
        },
        
        _onClickPreview: function () {
            var fileData = this.value;
            
            if (!fileData) {
                return;
            }
            
            var $content = $('<div>', {
                class: 'o_document_preview_container'
            });
            
            if (this.documentType === 'pdf') {
                $content.append($('<embed>', {
                    src: 'data:application/pdf;base64,' + fileData,
                    type: 'application/pdf',
                    width: '100%',
                    height: '500px'
                }));
            } else if (this.documentType === 'image') {
                $content.append($('<img>', {
                    src: 'data:image;base64,' + fileData,
                    class: 'img-fluid',
                    alt: this.filename || 'Imagen'
                }));
            }
            
            new Dialog(this, {
                title: _t('Previsualización: ') + (this.filename || ''),
                size: 'large',
                $content: $content,
                buttons: [{
                    text: _t('Cerrar'),
                    close: true
                }]
            }).open();
        }
    });
    
    // Registramos el widget
    registry.add('document_preview', DocumentPreviewWidget);
    
    // Simplificamos la exportación para enfocarnos en el widget principal
    return DocumentPreviewWidget;
});
