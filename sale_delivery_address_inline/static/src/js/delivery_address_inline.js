/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { FormView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

class SaleOrderDeliveryFormController extends FormController {
    /**
     * Setup del controlador
     */
    setup() {
        super.setup();
        this.env.bus.on("FIELD_CHANGED", this, this._onFieldChanged);
    }

    /**
     * Maneja cambios en campos
     */
    _onFieldChanged(event) {
        const fieldName = event.detail.fieldName;
        
        // Recargar si cambian direcciones
        if (fieldName === 'selected_delivery_partner_id' || 
            fieldName === 'partner_shipping_id' ||
            fieldName === 'use_alternative_delivery') {
            this.model.load();
        }
    }
    
    /**
     * Confirmación para cambios en pedidos confirmados
     */
    async onButtonClicked(params) {
        const record = await this.model.root.data;
        const state = record.state;
        const buttonName = params.name;
        
        // Confirmar si se crea dirección en pedido confirmado
        if (buttonName === 'action_create_delivery_address' && 
            ['sale', 'done'].includes(state)) {
            const confirmed = await this.env.services.dialog.confirm(
                _t("El pedido está confirmado. ¿Crear/modificar dirección de entrega?"),
                {
                    title: _t("Advertencia"),
                    confirmLabel: _t("Continuar"),
                    cancelLabel: _t("Cancelar"),
                }
            );
            
            if (!confirmed) {
                return;
            }
        }
        
        return super.onButtonClicked(params);
    }
}

// Registrar controlador personalizado
registry.category("views").add("sale_order_delivery_address_form", {
    ...FormView,
    Controller: SaleOrderDeliveryFormController,
});
