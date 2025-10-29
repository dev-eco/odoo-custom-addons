# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import math


class PavementCalculatorWizard(models.TransientModel):
    _name = 'pavement.calculator.wizard'
    _description = 'Asistente de Calculadora de Pavimento'

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Presupuesto Existente',
        help="Presupuesto al que se añadirán las líneas si se crea desde un presupuesto existente"
    )
    material_id = fields.Many2one(
        'pavement.material',
        string='Material',
        required=True,
    )
    area = fields.Float(
        'Área (m²)',
        required=True,
        default=1.0,
    )
    thickness = fields.Float(
        'Espesor (mm)',
        required=True,
        default=10.0,
    )
    waste_factor = fields.Float(
        'Factor de Pérdida (%)',
        required=True,
        default=5.0,
    )
    round_to_packages = fields.Boolean(
        'Redondear a Paquetes Completos',
        default=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )

    # Campos calculados
    material_quantity_kg = fields.Float(
        'Cantidad de Material (kg)',
        compute='_compute_quantities',
    )
    resin_quantity_l = fields.Float(
        'Cantidad de Resina (L)',
        compute='_compute_quantities',
    )
    packages_count = fields.Integer(
        'Número de Paquetes',
        compute='_compute_quantities',
    )
    estimated_cost = fields.Float(
        'Coste Estimado (EUR)',
        compute='_compute_costs',
    )
    material_cost = fields.Float(
        'Coste Material (EUR)',
        compute='_compute_costs',
    )
    resin_cost = fields.Float(
        'Coste Resina (EUR)',
        compute='_compute_costs',
    )

    @api.model
    def _compute_domain_material_id(self):
        domain = []
        if self.env.user.has_group('base.group_multi_company'):
            domain = ['|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)]
        return domain

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """Actualizar el dominio del material cuando cambia la compañía"""
        return {'domain': {'material_id': self._compute_domain_material_id()}}

    @api.onchange('material_id')
    def _onchange_material_id(self):
        """Establecer valores por defecto basados en el material seleccionado"""
        if self.material_id:
            self.thickness = self.material_id.min_thickness

    @api.constrains('area', 'thickness', 'waste_factor')
    def _check_input_values(self):
        for record in self:
            if record.area <= 0:
                raise ValidationError(_("El área debe ser mayor que 0"))
            if record.thickness <= 0:
                raise ValidationError(_("El espesor debe ser mayor que 0"))
            if record.waste_factor < 0:
                raise ValidationError(_("El factor de pérdida no puede ser negativo"))

            if record.material_id:
                if record.thickness < record.material_id.min_thickness:
                    raise ValidationError(_("El espesor no puede ser menor que el mínimo recomendado (%s mm)") % record.material_id.min_thickness)
                if record.thickness > record.material_id.max_thickness:
                    raise ValidationError(_("El espesor no puede ser mayor que el máximo recomendado (%s mm)") % record.material_id.max_thickness)

    @api.depends('area', 'thickness', 'waste_factor', 'material_id', 'round_to_packages')
    def _compute_quantities(self):
        for record in self:
            if record.material_id and record.area > 0 and record.thickness > 0:
                # Convertir factor de pérdida de porcentaje a decimal
                waste_factor_decimal = record.waste_factor / 100.0

                # Cálculo de la cantidad de material en kg
                material_quantity = record.area * (record.thickness / 1000) * record.material_id.density * (1 + waste_factor_decimal)

                # Cálculo de la cantidad de resina en litros
                resin_quantity = record.area * record.material_id.resin_consumption * \
                                (record.thickness / record.material_id.reference_thickness) * \
                                (1 + waste_factor_decimal)

                # Cálculo del número de paquetes
                if record.round_to_packages and record.material_id.pack_size > 0:
                    packages = math.ceil(material_quantity / record.material_id.pack_size)
                    if packages > 0:
                        # Si redondeamos a paquetes completos, recalcular la cantidad real
                        material_quantity = packages * record.material_id.pack_size
                else:
                    packages = material_quantity / record.material_id.pack_size if record.material_id.pack_size > 0 else 0

                record.material_quantity_kg = material_quantity
                record.resin_quantity_l = resin_quantity
                record.packages_count = int(packages)
            else:
                record.material_quantity_kg = 0.0
                record.resin_quantity_l = 0.0
                record.packages_count = 0

    @api.depends('material_quantity_kg', 'resin_quantity_l', 'material_id')
    def _compute_costs(self):
        for record in self:
            if record.material_id:
                material_cost = record.material_quantity_kg * record.material_id.price_per_kg
                resin_cost = record.resin_quantity_l * record.material_id.resin_price_per_l

                record.material_cost = material_cost
                record.resin_cost = resin_cost
                record.estimated_cost = material_cost + resin_cost
            else:
                record.material_cost = 0.0
                record.resin_cost = 0.0
                record.estimated_cost = 0.0

    def action_calculate(self):
        """Recalcular cuando se hace clic en el botón Calcular"""
        return {
            'name': _('Calculadora de Pavimento'),
            'type': 'ir.actions.act_window',
            'res_model': 'pavement.calculator.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_save(self):
        """Guardar el cálculo como un registro permanente"""
        self.ensure_one()

        calc = self.env['pavement.calculator'].create({
            'partner_id': self.partner_id.id,
            'material_id': self.material_id.id,
            'area': self.area,
            'thickness': self.thickness,
            'waste_factor': self.waste_factor,
            'round_to_packages': self.round_to_packages,
            'company_id': self.company_id.id,
        })

        return {
            'name': _('Calculadora de Pavimento'),
            'type': 'ir.actions.act_window',
            'res_model': 'pavement.calculator',
            'view_mode': 'form',
            'res_id': calc.id,
        }

    def action_create_sale_order(self):
        """Crear un presupuesto directamente desde el asistente"""
        self.ensure_one()

        if not self.material_id.product_id or not self.material_id.resin_product_id:
            raise ValidationError(_("Debe configurar los productos asociados al material y a la resina"))

        # Usar presupuesto existente o crear uno nuevo
        if self.sale_order_id:
            sale_order = self.sale_order_id
        else:
            # Crear el presupuesto
            sale_order = self.env['sale.order'].create({
                'partner_id': self.partner_id.id,
                'date_order': fields.Datetime.now(),
                'user_id': self.env.user.id,
                'company_id': self.company_id.id,
                'origin': _("Calculadora de Pavimento"),
            })

        # Crear línea para el material
        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.material_id.product_id.id,
            'product_uom_qty': self.material_quantity_kg,
            'name': _("Material: %s - Espesor: %s mm - Área: %s m²") % (
                self.material_id.name, self.thickness, self.area),
        })

        # Crear línea para la resina
        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.material_id.resin_product_id.id,
            'product_uom_qty': self.resin_quantity_l,
            'name': _("Resina para %s - Espesor: %s mm - Área: %s m²") % (
                self.material_id.name, self.thickness, self.area),
        })

        # También guardar el cálculo como registro permanente
        calc = self.env['pavement.calculator'].create({
            'partner_id': self.partner_id.id,
            'material_id': self.material_id.id,
            'area': self.area,
            'thickness': self.thickness,
            'waste_factor': self.waste_factor,
            'round_to_packages': self.round_to_packages,
            'company_id': self.company_id.id,
            'sale_order_id': sale_order.id,
            'state': 'sale_order',
        })

        return {
            'name': _('Presupuesto Generado'),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'type': 'ir.actions.act_window',
        }
