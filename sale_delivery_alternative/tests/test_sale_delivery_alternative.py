# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestSaleDeliveryAlternative(TransactionCase):

    def setUp(self):
        super().setUp()
        self.customer = self.env['res.partner'].create({
            'name': 'Distribuidor Test',
            'email': 'distribuidor@test.com',
        })
        self.end_customer = self.env['res.partner'].create({
            'name': 'Cliente Final',
            'email': 'cliente@final.com',
            'street': 'Calle Final 123',
            'city': 'Ciudad Final',
            'is_public_delivery_address': True,
        })
        self.product = self.env['product.product'].create({
            'name': 'Producto Test',
            'type': 'product',
            'list_price': 100,
        })

    def test_alternative_delivery_address(self):
        """Verificar que la dirección alternativa se propaga correctamente al albarán"""
        # Crear pedido con dirección alternativa
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'use_alternative_delivery': True,
            'alternative_delivery_partner_id': self.end_customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })

        # Confirmar pedido
        order.action_confirm()

        # Verificar que el albarán tiene la dirección alternativa
        self.assertEqual(len(order.picking_ids), 1)
        picking = order.picking_ids[0]
        self.assertEqual(picking.partner_id, self.end_customer)
        self.assertEqual(picking.original_partner_id, self.customer)
        self.assertTrue(picking.is_alternative_delivery)

        # Verificar que la factura mantiene el cliente original
        invoice = order._create_invoices()
        self.assertEqual(invoice.partner_id, self.customer)

    def test_save_as_usual_address(self):
        """Verificar que se guarda correctamente la dirección como habitual"""
        # Crear pedido con dirección alternativa
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'use_alternative_delivery': True,
            'alternative_delivery_partner_id': self.end_customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
            })],
        })

        # Guardar como dirección habitual
        order.action_save_as_usual_address()

        # Verificar que se ha guardado correctamente
        self.assertIn(self.end_customer, self.customer.alternative_delivery_for_partner_ids)
