# -*- coding: utf-8 -*-

import logging
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestResPartner(TransactionCase):
    """Tests para modelo res.partner"""

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'is_distributor': True,
            'credit_limit': 10000.0,
        })

    def test_01_get_child_categories(self):
        """Test recursión de categorías"""
        # Crear estructura de categorías
        cat_parent = self.env['product.category'].create({
            'name': 'Parent Category',
        })
        cat_child1 = self.env['product.category'].create({
            'name': 'Child 1',
            'parent_id': cat_parent.id,
        })
        cat_child2 = self.env['product.category'].create({
            'name': 'Child 2',
            'parent_id': cat_parent.id,
        })
        cat_grandchild = self.env['product.category'].create({
            'name': 'Grandchild',
            'parent_id': cat_child1.id,
        })
        
        # Obtener todas las categorías hijas
        all_ids = self.partner._get_child_categories([cat_parent.id])
        
        # Debe incluir padre, hijos y nietos
        self.assertIn(cat_parent.id, all_ids)
        self.assertIn(cat_child1.id, all_ids)
        self.assertIn(cat_child2.id, all_ids)
        self.assertIn(cat_grandchild.id, all_ids)

    def test_02_get_child_categories_max_depth(self):
        """Test límite de profundidad en recursión"""
        # Crear cadena profunda de categorías
        categories = []
        parent = None
        
        for i in range(15):  # Más que max_depth=10
            cat = self.env['product.category'].create({
                'name': f'Category Level {i}',
                'parent_id': parent.id if parent else False,
            })
            categories.append(cat)
            parent = cat
        
        # Obtener categorías con límite de profundidad
        all_ids = self.partner._get_child_categories([categories[0].id], max_depth=5)
        
        # Debe incluir solo hasta profundidad 5
        self.assertIn(categories[0].id, all_ids)
        self.assertIn(categories[4].id, all_ids)
        # No debe incluir más allá de profundidad 5
        self.assertNotIn(categories[10].id, all_ids)

    def test_03_compute_available_credit(self):
        """Test cálculo de crédito disponible"""
        self.partner.credit = 3000.0  # Deuda pendiente
        
        # Forzar recálculo
        self.partner._compute_available_credit()
        
        expected_available = 10000.0 - 3000.0
        self.assertEqual(self.partner.available_credit, expected_available)

    def test_04_validar_credito_disponible(self):
        """Test validación de crédito"""
        self.partner.credit = 3000.0
        
        # Debe permitir monto dentro del límite
        self.assertTrue(self.partner.validar_credito_disponible(5000.0))
        
        # No debe permitir monto que exceda el límite
        self.assertFalse(self.partner.validar_credito_disponible(8000.0))
