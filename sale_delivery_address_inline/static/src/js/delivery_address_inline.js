odoo.define('sale_delivery_address_inline.delivery_address', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;
    var _ = require('web.core')._; // Añadir la dependencia de underscore

    var SaleOrderFormController = FormController.extend({
        /**
         * Gestiona eventos específicos del formulario de pedidos con direcciones inline
         *
         * @override
         */
        _onFieldChanged: function (event) {
            var self = this;
            var fieldName = event.name.split('.').pop();
            
            // Si cambia la selección de dirección, actualizar los campos inline
            if (fieldName === 'selected_delivery_partner_id' || fieldName === 'partner_shipping_id') {
                this._super.apply(this, arguments).then(function () {
                    self.trigger_up('reload', {});
                });
                return;
            }
            
            this._super.apply(this, arguments);
        },
        
        /**
         * Confirma antes de cambiar la dirección en un pedido ya confirmado
         */
        _onButtonClicked: function (event) {
            var self = this;
            var state = this.model.get(this.handle).data.state;
            var buttonName = event.data.attrs.name;
            
            // Si es el botón para crear dirección y el pedido está confirmado
            if (buttonName === 'action_create_delivery_address' && ['sale', 'done'].includes(state)) {
                this.displayNotification({
                    title: _t("Advertencia"),
                    message: _t("El pedido ya está confirmado. ¿Seguro que desea crear/modificar la dirección de entrega?"),
                    type: 'warning',
                    sticky: false,
                    buttons: [{
                        text: _t("Cancelar"),
                        click: function () { return; }
                    }, {
                        text: _t("Continuar"),
                        primary: true,
                        click: function () {
                            self.trigger_up('button_clicked', event.data);
                        }
                    }]
                });
                return;
            }
            
            this._super.apply(this, arguments);
        },
    });

    // Registrar el controlador personalizado
    var SaleOrderFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: SaleOrderFormController,
        }),
    });

    // Registrar solo para el modelo sale.order
    viewRegistry.add('sale_order_delivery_address_form', SaleOrderFormView);
});
