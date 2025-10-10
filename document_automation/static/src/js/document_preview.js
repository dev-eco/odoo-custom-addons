odoo.define('document_automation.preview', function (require) {
    "use strict";

    const AbstractField = require('web.AbstractField');
    const core = require('web.core');
    const registry = require('web.field_registry');
    const Dialog = require('web.Dialog');
    const _t = core._t;

    const DocumentPreviewField = AbstractField.extend({
        className: 'o_field_document_preview',
        supportedFieldTypes: ['binary'],
        
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            this.previewEnabled = true;
            this.documentType = 'unknown';
            this.filename = record.data.filename || '';
            
            if (this.filename) {
                const extension = this.filename.split('.').pop().toLowerCase();
                if (['pdf'].includes(extension)) {
                    this.documentType = 'pdf';
                } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(extension)) {
                    this.documentType = 'image';
                }
            }
        },
        
        _renderReadonly: function () {
            this.$el.empty();
            if (!this.value) {
                return;
            }
            
            // Crear enlace de descarga
            const $link = $('<a>', {
                href: 'data:application/octet-stream;base64,' + this.value,
                download: this.filename || '',
                class: 'o_form_uri o_field_widget',
                html: $('<i>', {class: 'fa fa-download'}).prop('outerHTML') + ' ' + (this.filename || this.name),
            });
            
            // Crear botón de vista previa
            if (this.previewEnabled && (this.documentType === 'pdf' || this.documentType === 'image')) {
                const $previewButton = $('<button>', {
                    class: 'btn btn-sm btn-primary ms-2',
                    text: _t('Vista previa')
                });
                $previewButton.on('click', this._onClickPreview.bind(this));
                
                this.$el.append($link, $previewButton);
            } else {
                this.$el.append($link);
            }
        },
        
        _onClickPreview: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            
            if (!this.value) {
                return;
            }
            
            const $content = $('<div>', {
                class: 'o_document_preview_container'
            });
            
            if (this.documentType === 'pdf') {
                $content.append($('<embed>', {
                    src: 'data:application/pdf;base64,' + this.value,
                    type: 'application/pdf',
                    width: '100%',
                    height: '500px'
                }));
            } else if (this.documentType === 'image') {
                $content.append($('<img>', {
                    src: 'data:image;base64,' + this.value,
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
    
    registry.add('document_preview', DocumentPreviewField);
    
    return DocumentPreviewField;
});
