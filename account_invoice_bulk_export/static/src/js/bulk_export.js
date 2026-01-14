/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

export class BulkExportProgress extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            progress: 0,
            message: "",
            isProcessing: false,
        });

        this.intervalId = null;

        onMounted(() => {
            if (this.props.wizardId && this.props.autoStart) {
                this.startPolling();
            }
        });

        onWillUnmount(() => {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
        });
    }

    startPolling() {
        this.state.isProcessing = true;
        this.intervalId = setInterval(() => {
            this.checkProgress();
        }, 2000); // Verificar cada 2 segundos
    }

    async checkProgress() {
        try {
            const result = await this.rpc("/bulk_export/status/" + this.props.wizardId);

            if (result.error) {
                this.notification.add(result.error, { type: "danger" });
                this.stopPolling();
                return;
            }

            this.state.progress = result.progress_percentage || 0;
            this.state.message = result.progress_message || "";

            if (result.state === 'done') {
                this.state.isProcessing = false;
                this.stopPolling();

                if (result.download_url) {
                    this.notification.add(
                        "Exportación completada. Descargando archivo...",
                        { type: "success" }
                    );
                    window.location.href = result.download_url;
                }
            } else if (result.state === 'error') {
                this.state.isProcessing = false;
                this.stopPolling();
                this.notification.add(
                    "Error en la exportación. Revise los logs.",
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error checking progress:", error);
            this.stopPolling();
        }
    }

    stopPolling() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
}

BulkExportProgress.template = "account_invoice_bulk_export.ProgressTemplate";
BulkExportProgress.props = {
    wizardId: Number,
    autoStart: { type: Boolean, optional: true },
};

BulkExportProgress.template = `
<div class="bulk-export-progress" t-if="state.isProcessing">
    <div class="progress mb-3">
        <div class="progress-bar" 
             t-att-style="'width: ' + state.progress + '%'"
             t-att-aria-valuenow="state.progress"
             aria-valuemin="0" 
             aria-valuemax="100">
            <t t-esc="state.progress"/>%
        </div>
    </div>
    <p t-if="state.message" class="text-muted">
        <t t-esc="state.message"/>
    </p>
</div>
`;

registry.category("components").add("BulkExportProgress", BulkExportProgress);
