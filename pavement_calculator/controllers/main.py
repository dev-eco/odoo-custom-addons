# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class PavementCalculatorController(http.Controller):
    @http.route('/pavement_calculator/calculator', type='json', auth='user')
    def get_calculator_data(self, **kw):
        """Endpoint para obtener datos de materiales para la calculadora"""
        materials = request.env['pavement.material'].search_read(
            domain=[('active', '=', True)],
            fields=['id', 'name', 'material_type', 'density', 'resin_consumption',
                   'reference_thickness', 'min_thickness', 'max_thickness']
        )

        return {
            'materials': materials,
        }

    @http.route('/pavement_calculator/calculate', type='json', auth='user')
    def calculate_materials(self, material_id, area, thickness, waste_factor, round_to_packages=True, **kw):
        """Endpoint para realizar cálculos sin crear un registro"""
        material = request.env['pavement.material'].browse(int(material_id))
        if not material.exists():
            return {'error': 'Material no encontrado'}

        try:
            area = float(area)
            thickness = float(thickness)
            waste_factor = float(waste_factor)
        except (ValueError, TypeError):
            return {'error': 'Valores numéricos inválidos'}

        if area <= 0 or thickness <= 0 or waste_factor < 0:
            return {'error': 'Los valores deben ser positivos'}

        if thickness < material.min_thickness or thickness > material.max_thickness:
            return {'error': f'El espesor debe estar entre {material.min_thickness} y {material.max_thickness} mm'}

        # Realizar cálculos
        waste_factor_decimal = waste_factor / 100.0
        material_quantity = area * (thickness / 1000) * material.density * (1 + waste_factor_decimal)
        resin_quantity = area * material.resin_consumption * (thickness / material.reference_thickness) * (1 + waste_factor_decimal)

        packages = material_quantity / material.pack_size if material.pack_size > 0 else 0

        if round_to_packages and material.pack_size > 0:
            import math
            packages = math.ceil(packages)
            material_quantity = packages * material.pack_size

        material_cost = material_quantity * material.price_per_kg
        resin_cost = resin_quantity * material.resin_price_per_l
        total_cost = material_cost + resin_cost

        return {
            'material_quantity': round(material_quantity, 2),
            'resin_quantity': round(resin_quantity, 2),
            'packages': int(packages),
            'material_cost': round(material_cost, 2),
            'resin_cost': round(resin_cost, 2),
            'total_cost': round(total_cost, 2),
        }
