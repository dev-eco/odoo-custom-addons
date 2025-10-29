odoo.define('pavement_calculator.calculator', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var _t = core._t;

    var PavementCalculator = Widget.extend({
        template: 'PavementCalculatorWidget',
        events: {
            'change .calculator-input': '_onInputChange',
            'click .calculate-button': '_onCalculateClick',
            'change #material_id': '_onMaterialChange',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.options = options || {};
            this.materials = [];
            this.currentMaterial = null;
            this.results = null;
        },

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return rpc.query({
                    route: '/pavement_calculator/calculator',
                    params: {},
                }).then(function (data) {
                    self.materials = data.materials || [];
                });
            });
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._initializeForm();
            });
        },

        _initializeForm: function () {
            var $materialSelect = this.$('#material_id');
            $materialSelect.empty();
            $materialSelect.append($('<option>', {
                value: '',
                text: _t('Seleccione un material')
            }));

            _.each(this.materials, function (material) {
                $materialSelect.append($('<option>', {
                    value: material.id,
                    text: material.name
                }));
            });

            // Inicializar valores por defecto
            this.$('#area').val(1);
            this.$('#thickness').val(10);
            this.$('#waste_factor').val(5);
            this.$('#round_to_packages').prop('checked', true);
        },

        _onInputChange: function () {
            // Limpiar resultados cuando cambian los inputs
            this._clearResults();
        },

        _onMaterialChange: function () {
            var materialId = parseInt(this.$('#material_id').val());
            this.currentMaterial = _.findWhere(this.materials, {id: materialId});

            if (this.currentMaterial) {
                // Actualizar el rango de espesor permitido
                this.$('#thickness_range').text(
                    _t('Rango permitido: ') +
                    this.currentMaterial.min_thickness + ' - ' +
                    this.currentMaterial.max_thickness + ' mm'
                );

                // Establecer el espesor mínimo como valor por defecto
                this.$('#thickness').val(this.currentMaterial.min_thickness);
            } else {
                this.$('#thickness_range').text('');
            }

            this._clearResults();
        },

        _onCalculateClick: function () {
            var self = this;
            var materialId = this.$('#material_id').val();
            var area = this.$('#area').val();
            var thickness = this.$('#thickness').val();
            var wasteFactor = this.$('#waste_factor').val();
            var roundToPackages = this.$('#round_to_packages').prop('checked');

            if (!materialId) {
                this._showError(_t('Por favor seleccione un material'));
                return;
            }

            if (!area || !thickness || !wasteFactor) {
                this._showError(_t('Todos los campos son obligatorios'));
                return;
            }

            rpc.query({
                route: '/pavement_calculator/calculate',
                params: {
                    material_id: materialId,
                    area: area,
                    thickness: thickness,
                    waste_factor: wasteFactor,
                    round_to_packages: roundToPackages
                },
            }).then(function (result) {
                if (result.error) {
                    self._showError(result.error);
                } else {
                    self._displayResults(result);
                }
            }).guardedCatch(function (error) {
                self._showError(_t('Error al realizar el cálculo'));
            });
        },

        _displayResults: function (results) {
            this.results = results;

            this.$('#result_material').text(results.material_quantity.toFixed(2) + ' kg');
            this.$('#result_resin').text(results.resin_quantity.toFixed(2) + ' L');
            this.$('#result_packages').text(results.packages);
            this.$('#result_material_cost').text(results.material_cost.toFixed(2) + ' €');
            this.$('#result_resin_cost').text(results.resin_cost.toFixed(2) + ' €');
            this.$('#result_total_cost').text(results.total_cost.toFixed(2) + ' €');

            this.$('.calculator-results').removeClass('d-none');
        },

        _clearResults: function () {
            this.results = null;
            this.$('.calculator-results').addClass('d-none');
        },

        _showError: function (message) {
            Dialog.alert(this, {
                title: _t('Error'),
                message: message,
            });
        }
    });

    core.action_registry.add('pavement_calculator.calculator', PavementCalculator);

    return PavementCalculator;
});
