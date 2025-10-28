# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError
import math


class TestPavementCalculator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Crear material de prueba
        cls.test_material = cls.env['pavement.material'].create({
            'name': 'Material Prueba',
            'material_type': 'sbr',
            'density': 600,
            'resin_consumption': 0.5,
            'reference_thickness': 10,
            'pack_size': 25,
            'price_per_kg': 0.5,
            'resin_price_per_l': 2.0,
            'min_thickness': 10,
            'max_thickness': 100,
        })
        
        # Crear partner de prueba
        cls.test_partner = cls.env['res.partner'].create({
            'name': 'Cliente Prueba',
            'email': 'test@example.com',
        })
        
        # Crear productos para usar en presupuestos
        cls.material_product = cls.env['product.product'].create({
            'name': 'Granza SBR',
            'type': 'product',
            'list_price': 0.5,
        })
        
        cls.resin_product = cls.env['product.product'].create({
            'name': 'Resina PU',
            'type': 'product',
            'list_price': 2.0,
        })
        
        # Asignar productos al material
        cls.test_material.write({
            'product_id': cls.material_product.id,
            'resin_product_id': cls.resin_product.id,
        })
    
    def test_calculator_computation(self):
        """Prueba el cálculo correcto de cantidades y costos"""
        # Caso de prueba: Área 10 m², espesor 20 mm
        calc = self.env['pavement.calculator'].create({
            'partner_id': self.test_partner.id,
            'material_id': self.test_material.id,
            'area': 10,
            'thickness': 20,
            'waste_factor': 5,
            'round_to_packages': False,
        })
        
        # Verificar cálculos (formula manual vs calculado por el modelo)
        waste_factor_decimal = 5 / 100.0
        
        # Material: area * (thickness/1000) * density * (1 + waste_factor)
        expected_material = 10 * (20/1000) * 600 * (1 + waste_factor_decimal)
        self.assertAlmostEqual(calc.material_quantity_kg, expected_material, places=2)
        
        # Resina: area * resin_consumption * (thickness/reference_thickness) * (1 + waste_factor)
        expected_resin = 10 * 0.5 * (20/10) * (1 + waste_factor_decimal)
        self.assertAlmostEqual(calc.resin_quantity_l, expected_resin, places=2)
        
        # Costos: material * precio + resina * precio
        expected_material_cost = expected_material * 0.5
        expected_resin_cost = expected_resin * 2.0
        expected_total = expected_material_cost + expected_resin_cost
        
        self.assertAlmostEqual(calc.material_cost, expected_material_cost, places=2)
        self.assertAlmostEqual(calc.resin_cost, expected_resin_cost, places=2)
        self.assertAlmostEqual(calc.estimated_cost, expected_total, places=2)
    
    def test_round_to_packages(self):
        """Prueba el redondeo a paquetes completos"""
        # Caso de prueba: Área 10 m², espesor 20 mm, con redondeo a paquetes
        calc = self.env['pavement.calculator'].create({
            'partner_id': self.test_partner.id,
            'material_id': self.test_material.id,
            'area': 10,
            'thickness': 20,
            'waste_factor': 5,
            'round_to_packages': True,
        })
        
        # Verificar que la cantidad de material se ha redondeado a paquetes completos
        waste_factor_decimal = 5 / 100.0
        expected_material = 10 * (20/1000) * 600 * (1 + waste_factor_decimal)
        expected_packages = math.ceil(expected_material / self.test_material.pack_size)
        expected_rounded_material = expected_packages * self.test_material.pack_size
        
        self.assertEqual(calc.packages_count, expected_packages)
        self.assertEqual(calc.material_quantity_kg, expected_rounded_material)
    
    def test_sale_order_generation(self):
        """Prueba la generación de presupuestos"""
        calc = self.env['pavement.calculator'].create({
            'partner_id': self.test_partner.id,
            'material_id': self.test_material.id,
            'area': 10,
            'thickness': 20,
            'waste_factor': 5,
        })
        
        # Generar presupuesto
        result = calc.action_create_sale_order()
        
        # Verificar que se creó el presupuesto
        self.assertTrue(calc.sale_order_id, "No se ha creado el presupuesto")
        self.assertEqual(calc.state, 'sale_order', "El estado no se ha actualizado a 'sale_order'")
        
        # Verificar las líneas del presupuesto
        self.assertEqual(len(calc.sale_order_id.order_line), 2, "El presupuesto debe tener 2 líneas")
        
        # Verificar que las cantidades coinciden
        material_line = calc.sale_order_id.order_line.filtered(lambda l: l.product_id == self.material_product)
        resin_line = calc.sale_order_id.order_line.filtered(lambda l: l.product_id == self.resin_product)
        
        self.assertEqual(material_line.product_uom_qty, calc.material_quantity_kg)
        self.assertEqual(resin_line.product_uom_qty, calc.resin_quantity_l)
