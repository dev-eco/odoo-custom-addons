odoo.define('sale_delivery_address_inline.delivery_address', function (require) {
    "use strict";

    const { FormController } = require("@web/views/form/form_controller");
    const { FormView } = require("@web/views/form/form_view");
    const { registry } = require("@web/core/registry");
    const { _t } = require("@web/core/l10n/translation");

    class SaleOrderFormController extends FormController {
        /**
         * Gestiona eventos específicos del formulario de pedidos con direcciones inline
         *
         * @override
         */
        setup() {
            super.setup();
            this.env.bus.on("FIELD_CHANGED", this, this._onFieldChanged);
        }

        /**
         * Maneja cambios en los campos
         */
        _onFieldChanged(event) {
            const fieldName = event.detail.fieldName;
            
            // Si cambia la selección de dirección, actualizar los campos inline
            if (fieldName === 'selected_delivery_partner_id' || fieldName === 'partner_shipping_id') {
                this.model.load();
            }
        }
        
        /**
         * Confirma antes de cambiar la dirección en un pedido ya confirmado
         */
        async onButtonClicked(params) {
            const record = await this.model.root.data;
            const state = record.state;
            const buttonName = params.name;
            
            // Si es el botón para crear dirección y el pedido está confirmado
            if (buttonName === 'action_create_delivery_address' && ['sale', 'done'].includes(state)) {
                const confirmed = await this.env.services.dialog.confirm(
                    _t("El pedido ya está confirmado. ¿Seguro que desea crear/modificar la dirección de entrega?"),
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

    // Registrar el controlador personalizado
    registry.category("views").add("sale_order_delivery_address_form", {
        ...FormView,
        Controller: SaleOrderFormController,
    });
    return SaleOrderFormController;
});
