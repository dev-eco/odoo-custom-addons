/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * Widget para visualizar y procesar documentos escaneados
 */
export class DocumentWidget extends Component {
    setup() {
        this.state = useState({
            isLoading: false,
            document: null,
            previewUrl: null,
        });
        
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        onWillStart(async () => {
            if (this.props.record.data.document_scan_id) {
                await this.loadDocumentData();
            }
        });
    }
    
    /**
     * Carga los datos del documento escaneado
     */
    async loadDocumentData() {
        this.state.isLoading = true;
        try {
            const result = await this.rpc("/document_automation/document_data", {
                document_id: this.props.record.data.document_scan_id,
            });
            
            if (result) {
                this.state.document = result;
                this.state.previewUrl = result.preview_url || null;
            }
        } catch (error) {
            this.notification.add(
                this.env._t("No se pudo cargar la información del documento"),
                { type: "danger" }
            );
            console.error("Error cargando datos del documento:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
    
    /**
     * Procesa el documento manualmente
     */
    async processDocument() {
        if (!this.props.record.data.document_scan_id) {
            return;
        }
        
        this.state.isLoading = true;
        try {
            const result = await this.rpc("/document_automation/process_document", {
                document_id: this.props.record.data.document_scan_id,
            });
            
            if (result.success) {
                this.notification.add(
                    this.env._t("Documento procesado correctamente"),
                    { type: "success" }
                );
                await this.loadDocumentData();
            } else {
                this.notification.add(
                    this.env._t("Error al procesar el documento: ") + result.error,
                    { type: "danger" }
                );
            }
        } catch (error) {
            this.notification.add(
                this.env._t("Error al procesar el documento"),
                { type: "danger" }
            );
            console.error("Error procesando documento:", error);
        } finally {
            this.state.isLoading = false;
        }
    }
}

DocumentWidget.template = "document_automation.DocumentWidget";
DocumentWidget.props = {
    ...standardFieldProps,
    string: { type: String, optional: true },
};

registry.category("fields").add("document_widget", DocumentWidget);
