/** 
 * JavaScript para mejorar la experiencia de usuario en facturas
 * © 2025 Tu Empresa - https://www.tuempresa.com
 * License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)
 */

odoo.define('facturas_personalizadas.account_invoice', function (require) {
    "use strict";
    
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;
    
    // Extender el controlador del formulario para facturas
    var InvoiceFormController = FormController.extend({
        /**
         * Extender la función de renderizado para añadir advertencias cuando falte
         * información personalizada importante
         */
        _update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var record = self.model.get(self.handle);
                
                // Solo aplicar a facturas de cliente
                if (record.data.model === 'account.move' && 
                    ['out_invoice', 'out_refund'].includes(record.data.move_type) &&
                    record.data.state === 'draft') {
                    
                    // Verificar si falta la referencia del cliente
                    if (!record.data.referencia_cliente && record.data.partner_id) {
                        self.displayNotification({
                            title: _t('Sugerencia'),
                            message: _t('No se ha especificado una referencia de cliente. ' +
                                     'Esto puede ser útil para que el cliente identifique la factura fácilmente.'),
                            type: 'info',
                        });
                    }
                }
            });
        },
        
        /**
         * Mostrar un mensaje cuando se guarda una factura con campos personalizados
         */
        saveRecord: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function (result) {
                var record = self.model.get(self.handle);
                
                // Comprobar si tiene campos personalizados después de guardar
                if (record.data.model === 'account.move' && record.data.tiene_campos_personalizados) {
                    self.displayNotification({
                        title: _t('Factura personalizada'),
                        message: _t('La factura se ha guardado con campos personalizados adicionales.'),
                        type: 'success',
                    });
                }
                
                return result;
            });
        },
    });
    
    // Crear una vista de formulario personalizada para facturas
    var InvoiceFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: InvoiceFormController,
        }),
    });
    
    // Registrar la vista personalizada
    viewRegistry.add('invoice_form_enhanced', InvoiceFormView);
    
    return {
        InvoiceFormController: InvoiceFormController,
        InvoiceFormView: InvoiceFormView,
    };
});
