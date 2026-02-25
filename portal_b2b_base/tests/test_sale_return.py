# -*- coding: utf-8 -*-

import logging
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestSaleReturn(TransactionCase):
    """Tests para modelo sale.return"""

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
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 10,
            })],
        })

    def test_01_create_return(self):
        """Test creación de devolución"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'reason_description': 'Producto defectuoso',
        })
        
        self.assertEqual(return_obj.partner_id, self.partner)
        self.assertEqual(return_obj.state, 'draft')
        self.assertEqual(return_obj.reason, 'defective')

    def test_02_submit_return(self):
        """Test enviar devolución"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': 100.0,
            })],
        })
        
        return_obj.action_submit()
        self.assertEqual(return_obj.state, 'submitted')

    def test_03_approve_return(self):
        """Test aprobar devolución"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': 100.0,
            })],
        })
        
        return_obj.action_submit()
        return_obj.action_approve()
        
        self.assertEqual(return_obj.state, 'approved')
        self.assertTrue(return_obj.approval_user_id)

    def test_04_reject_return(self):
        """Test rechazar devolución"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': 100.0,
            })],
        })
        
        return_obj.action_submit()
        return_obj.action_reject('No cumple criterios')
        
        self.assertEqual(return_obj.state, 'rejected')
        self.assertEqual(return_obj.rejection_reason, 'No cumple criterios')

    def test_05_process_return(self):
        """Test procesar devolución"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'refund_method': 'credit_note',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': 100.0,
            })],
        })
        
        return_obj.action_submit()
        return_obj.action_approve()
        return_obj.action_process()
        
        self.assertEqual(return_obj.state, 'processed')

    def test_06_close_return(self):
        """Test cerrar devolución (CRÍTICO: debe usar 'processed')"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2,
                'unit_price': 100.0,
            })],
        })
        
        return_obj.action_submit()
        return_obj.action_approve()
        return_obj.action_close()
        
        # CRÍTICO: Debe ser 'processed', NO 'closed'
        self.assertEqual(return_obj.state, 'processed')

    def test_07_compute_total_amount(self):
        """Test cálculo de total"""
        return_obj = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': self.order.id,
            'reason': 'defective',
            'line_ids': [
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 2,
                    'unit_price': 100.0,
                }),
                (0, 0, {
                    'product_id': self.product.id,
                    'quantity': 3,
                    'unit_price': 50.0,
                }),
            ],
        })
        
        expected_total = (2 * 100.0) + (3 * 50.0)
        self.assertEqual(return_obj.total_amount, expected_total)
