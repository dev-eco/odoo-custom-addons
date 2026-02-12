# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
import logging

_logger = logging.getLogger(__name__)


class TestPortalB2BModels(TransactionCase):
    """Tests para modelos del Portal B2B."""
    
    def setUp(self):
        super().setUp()
        
        # Crear partner distribuidor
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distribuidor',
            'email': 'test@distribuidor.com',
            'credit_limit': 10000.0,
        })
        
        # Crear producto
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'sale_ok': True,
            'list_price': 100.0,
        })
    
    def test_portal_message_creation(self):
        """Test creación de mensaje en portal."""
        message = self.env['portal.message'].create({
            'partner_id': self.partner.id,
            'subject': 'Test Message',
            'message': 'This is a test message',
            'sender_type': 'company',
        })
        
        self.assertTrue(message.exists())
        self.assertEqual(message.subject, 'Test Message')
        self.assertFalse(message.is_read)
    
    def test_portal_message_mark_read(self):
        """Test marcar mensaje como leído."""
        message = self.env['portal.message'].create({
            'partner_id': self.partner.id,
            'subject': 'Test Message',
            'message': 'This is a test message',
            'sender_type': 'company',
        })
        
        message.action_mark_read()
        
        self.assertTrue(message.is_read)
        self.assertIsNotNone(message.read_date)
    
    def test_sale_return_creation(self):
        """Test creación de devolución."""
        # Crear pedido
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
            })],
        })
        
        # Crear devolución
        return_record = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': order.id,
            'reason': 'defective',
            'description': 'Test return',
        })
        
        self.assertTrue(return_record.exists())
        self.assertNotEqual(return_record.name, 'Nuevo')
        self.assertEqual(return_record.state, 'draft')
    
    def test_sale_return_line_creation(self):
        """Test creación de línea de devolución."""
        # Crear pedido
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
            })],
        })
        
        # Crear devolución
        return_record = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': order.id,
            'reason': 'defective',
        })
        
        # Crear línea
        line = self.env['sale.return.line'].create({
            'return_id': return_record.id,
            'product_id': self.product.id,
            'quantity': 2.0,
            'price_unit': 100.0,
        })
        
        self.assertTrue(line.exists())
        self.assertEqual(line.subtotal, 200.0)
    
    def test_sale_return_total_amount(self):
        """Test cálculo de total en devolución."""
        # Crear pedido
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
            })],
        })
        
        # Crear devolución
        return_record = self.env['sale.return'].create({
            'partner_id': self.partner.id,
            'order_id': order.id,
            'reason': 'defective',
        })
        
        # Crear líneas
        self.env['sale.return.line'].create({
            'return_id': return_record.id,
            'product_id': self.product.id,
            'quantity': 2.0,
            'price_unit': 100.0,
        })
        
        self.env['sale.return.line'].create({
            'return_id': return_record.id,
            'product_id': self.product.id,
            'quantity': 3.0,
            'price_unit': 50.0,
        })
        
        self.assertEqual(return_record.total_amount, 350.0)
    
    def test_audit_log_creation(self):
        """Test creación de log de auditoría."""
        log = self.env['portal.audit.log'].log_action(
            action='test_action',
            model_name='sale.order',
            record_id=1,
            description='Test log entry'
        )
        
        # Verificar que se creó
        logs = self.env['portal.audit.log'].search([
            ('action', '=', 'test_action')
        ])
        
        self.assertTrue(len(logs) > 0)
