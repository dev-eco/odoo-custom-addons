# -*- coding: utf-8 -*-

import logging
from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestSaleOrderTemplate(TransactionCase):
    """Tests para modelo sale.order.template"""

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'is_distributor': True,
        })
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'list_price': 100.0,
        })

    def test_01_create_template(self):
        """Test creación de plantilla"""
        template = self.env['sale.order.template'].create({
            'name': 'Test Template',
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5,
            })],
        })
        
        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(len(template.line_ids), 1)
        self.assertTrue(template.active)

    def test_02_cron_get_templates_to_process(self):
        """Test obtener templates para procesar"""
        today = fields.Date.today()
        
        # Template que debe procesarse
        template1 = self.env['sale.order.template'].create({
            'name': 'Template 1',
            'partner_id': self.partner.id,
            'recurrence_enabled': True,
            'recurrence_active': True,
            'recurrence_next_date': today,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5,
            })],
        })
        
        # Template que NO debe procesarse (fecha futura)
        template2 = self.env['sale.order.template'].create({
            'name': 'Template 2',
            'partner_id': self.partner.id,
            'recurrence_enabled': True,
            'recurrence_active': True,
            'recurrence_next_date': today + timedelta(days=5),
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5,
            })],
        })
        
        templates = self.env['sale.order.template']._get_templates_to_process()
        
        self.assertIn(template1, templates)
        self.assertNotIn(template2, templates)

    def test_03_cron_validate_template(self):
        """Test validación de template"""
        # Template válido
        template_valid = self.env['sale.order.template'].create({
            'name': 'Valid Template',
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5,
            })],
        })
        
        # Template sin líneas (inválido)
        template_invalid = self.env['sale.order.template'].create({
            'name': 'Invalid Template',
            'partner_id': self.partner.id,
        })
        
        self.assertTrue(template_valid._validate_template(template_valid))
        self.assertFalse(template_invalid._validate_template(template_invalid))

    def test_04_cron_create_order_from_template(self):
        """Test creación de pedido desde template"""
        template = self.env['sale.order.template'].create({
            'name': 'Test Template',
            'partner_id': self.partner.id,
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5,
            })],
        })
        
        order = template._create_order_from_template(template)
        
        self.assertEqual(order.partner_id, self.partner)
        self.assertTrue(order.is_recurring)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line[0].product_id, self.product)

    def test_05_cron_update_next_date(self):
        """Test actualización de próxima fecha"""
        today = fields.Date.today()
        template = self.env['sale.order.template'].create({
            'name': 'Test Template',
            'partner_id': self.partner.id,
            'recurrence_interval': 30,
            'recurrence_next_date': today,
        })
        
        template._update_template_next_date(template)
        
        expected_date = today + timedelta(days=30)
        self.assertEqual(template.recurrence_next_date, expected_date)
