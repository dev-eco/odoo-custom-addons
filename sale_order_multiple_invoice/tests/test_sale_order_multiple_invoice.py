from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSaleOrderMultipleInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Crear productos
        cls.product1 = cls.env['product.product'].create({
            'name': 'Producto Test 1',
            'type': 'product',
            'list_price': 100.0,
        })
        
        cls.product2 = cls.env['product.product'].create({
            'name': 'Producto Test 2',
            'type': 'product',
            'list_price': 200.0,
        })
        
        # Crear clientes
        cls.partner1 = cls.env['res.partner'].create({
            'name': 'Cliente Test 1',
            'email': 'test1@example.com',
        })
        
        cls.partner2 = cls.env['res.partner'].create({
            'name': 'Cliente Test 2',
            'email': 'test2@example.com',
        })
        
        # Crear pedidos de venta
        cls.order1 = cls.env['sale.order'].create({
            'partner_id': cls.partner1.id,
            'order_line': [
                (0, 0, {
                    'product_id': cls.product1.id,
                    'product_uom_qty': 2.0,
                    'price_unit': 100.0,
                }),
                (0, 0, {
                    'product_id': cls.product2.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 200.0,
                }),
            ],
        })
        
        cls.order2 = cls.env['sale.order'].create({
            'partner_id': cls.partner1.id,
            'order_line': [
                (0, 0, {
                    'product_id': cls.product1.id,
                    'product_uom_qty': 3.0,
                    'price_unit': 100.0,
                }),
            ],
        })
        
        cls.order3 = cls.env['sale.order'].create({
            'partner_id': cls.partner2.id,
            'order_line': [
                (0, 0, {
                    'product_id': cls.product1.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                }),
            ],
        })
        
        # Confirmar pedidos
        cls.order1.action_confirm()
        cls.order2.action_confirm()
        cls.order3.action_confirm()
    
    def test_01_consolidate_two_identical_orders(self):
        """Test consolidar dos pedidos idénticos en producto/qty"""
        # Crear el wizard
        wizard = self.env['sale.order.multiple.invoice.wizard'].with_context(
            active_ids=[self.order1.id, self.order2.id]
        ).create({})
        
        # Verificar que los pedidos sean del mismo cliente
        self.assertEqual(wizard.partner_id, self.partner1)
        
        # Ejecutar el wizard
        result = wizard.action_create_invoice()
        
        # Comprobar que se ha creado una factura
        self.assertTrue(result.get('res_id'))
        
        # Obtener la factura
        invoice = self.env['account.move'].browse(result.get('res_id'))
        
        # Verificar que la factura está asociada a ambos pedidos
        self.assertEqual(len(invoice.sale_order_ids), 2)
        self.assertIn(self.order1, invoice.sale_order_ids)
        self.assertIn(self.order2, invoice.sale_order_ids)
        
        if wizard.consolidation_mode == 'sum_by_product':
            # En modo suma, debe haber 2 líneas (una por cada producto)
            self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: l.product_id)), 2)
            
            # Verificar las cantidades
            line_product1 = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.product1)
            self.assertEqual(line_product1.quantity, 5.0)  # 2 + 3
            
            line_product2 = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.product2)
            self.assertEqual(line_product2.quantity, 1.0)
    
    def test_02_consolidate_with_separate_lines(self):
        """Test consolidar pedidos con líneas separadas"""
        # Crear el wizard
        wizard = self.env['sale.order.multiple.invoice.wizard'].with_context(
            active_ids=[self.order1.id, self.order2.id]
        ).create({
            'consolidation_mode': 'lines_separate',
        })
        
        # Ejecutar el wizard
        result = wizard.action_create_invoice()
        
        # Obtener la factura
        invoice = self.env['account.move'].browse(result.get('res_id'))
        
        # En modo líneas separadas, debe haber 3 líneas (una por cada línea de pedido)
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: l.product_id)), 3)
        
        # Verificar que cada línea tiene su pedido de origen
        self.assertTrue(all(line.sale_order_id for line in invoice.invoice_line_ids.filtered(lambda l: l.product_id)))
    
    def test_03_different_partners_error(self):
        """Test error al intentar consolidar pedidos de distintos clientes"""
        # Intentar crear el wizard con pedidos de distintos clientes
        with self.assertRaises(UserError):
            self.env['sale.order.multiple.invoice.wizard'].with_context(
                active_ids=[self.order1.id, self.order3.id]
            ).create({})
    
    def test_04_idempotency(self):
        """Test de idempotencia: ejecutar el wizard dos veces no debe crear una segunda factura"""
        # Crear el wizard y ejecutarlo
        wizard1 = self.env['sale.order.multiple.invoice.wizard'].with_context(
            active_ids=[self.order1.id, self.order2.id]
        ).create({})
        
        result1 = wizard1.action_create_invoice()
        invoice1 = self.env['account.move'].browse(result1.get('res_id'))
        
        # Crear otro wizard con los mismos pedidos
        wizard2 = self.env['sale.order.multiple.invoice.wizard'].with_context(
            active_ids=[self.order1.id, self.order2.id]
        ).create({})
        
        result2 = wizard2.action_create_invoice()
        invoice2 = self.env['account.move'].browse(result2.get('res_id'))
        
        # Comprobar que ambos wizards devuelven la misma factura
        self.assertEqual(invoice1, invoice2)
        
        # Comprobar que solo hay una relación por pedido-factura
        groups = self.env['sale.order.invoice.group'].search([
            ('sale_order_id', 'in', [self.order1.id, self.order2.id]),
            ('invoice_id', '=', invoice1.id)
        ])
        
        self.assertEqual(len(groups), 2)
