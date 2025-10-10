// document_preview.js
/** @odoo-module */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { BinaryField } from "@web/views/fields/binary/binary_field";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class DocumentPreviewField extends BinaryField {
    setup() {
        super.setup();
        this.state = useState({
            previewEnabled: true,
            documentType: 'unknown'
        });
        this.rootRef = useRef("root");
        this.dialogService = useService("dialog");

        onMounted(() => {
            this._determineDocumentType();
            this._addPreviewButton();
        });
    }

    _determineDocumentType() {
        const filename = this.props.record.data.filename || '';
        if (filename) {
            const extension = filename.split('.').pop().toLowerCase();
            if (['pdf'].includes(extension)) {
                this.state.documentType = 'pdf';
            } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(extension)) {
                this.state.documentType = 'image';
            }
        }
    }

    _addPreviewButton() {
        if (this.props.value && this.state.previewEnabled && 
            (this.state.documentType === 'pdf' || this.state.documentType === 'image')) {
            const button = document.createElement('button');
            button.className = 'btn btn-sm btn-primary o_document_preview_button ms-2';
            button.textContent = _t('Vista previa');
            button.addEventListener('click', this._onClickPreview.bind(this));
            
            const clearButton = this.rootRef.el.querySelector('.o_clear_file_button');
            if (clearButton) {
                clearButton.parentNode.insertBefore(button, clearButton.nextSibling);
            }
        }
    }

    _onClickPreview(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        
        const fileData = this.props.value;
        if (!fileData) {
            return;
        }
        
        let content = document.createElement('div');
        content.className = 'o_document_preview_container';
        
        if (this.state.documentType === 'pdf') {
            const embed = document.createElement('embed');
            embed.src = 'data:application/pdf;base64,' + fileData;
            embed.type = 'application/pdf';
            embed.style.width = '100%';
            embed.style.height = '500px';
            content.appendChild(embed);
        } else if (this.state.documentType === 'image') {
            const img = document.createElement('img');
            img.src = 'data:image;base64,' + fileData;
            img.className = 'img-fluid';
            img.alt = this.props.record.data.filename || 'Imagen';
            content.appendChild(img);
        }
        
        this.dialogService.add(Dialog, {
            title: _t('Previsualización: ') + (this.props.record.data.filename || ''),
            size: 'large',
            body: content,
            buttons: [{
                text: _t('Cerrar'),
                close: true
            }]
        });
    }
}

DocumentPreviewField.template = "document_automation.DocumentPreviewField";
DocumentPreviewField.props = {
    ...standardFieldProps,
};

registry.category("fields").add("document_preview", DocumentPreviewField);
