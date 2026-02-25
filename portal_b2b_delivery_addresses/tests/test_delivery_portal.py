# -*- coding: utf-8 -*-

import logging
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TestDeliveryAddress(TransactionCase):
    """Tests para modelo delivery.address"""

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'is_distributor': True,
        })
        self.country_es = self.env.ref('base.es')
        self.state_madrid = self.env['res.country.state'].search([
            ('country_id', '=', self.country_es.id),
            ('code', '=', 'M')
        ], limit=1)

    def test_01_create_delivery_address(self):
        """Test creación de dirección de entrega"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Almacén Principal',
            'street': 'Calle Test 123',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.country_es.id,
        })
        
        self.assertEqual(address.partner_id, self.partner)
        self.assertTrue(address.active)
        self.assertEqual(address.name, 'Almacén Principal')
        self.assertIn('Calle Test 123', address.full_address)

    def test_02_set_default_address(self):
        """Test marcar dirección como predeterminada"""
        address1 = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección 1',
            'street': 'Calle 1',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.country_es.id,
            'is_default': True,
        })
        
        address2 = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección 2',
            'street': 'Calle 2',
            'city': 'Barcelona',
            'zip': '08001',
            'country_id': self.country_es.id,
        })

        # Marcar address2 como default
        address2.write({'is_default': True})

        # Recargar address1 para ver cambios
        address1.invalidate_recordset()

        # Solo address2 debe ser default
        self.assertTrue(address2.is_default)
        self.assertFalse(address1.is_default)

    def test_03_full_address_computed(self):
        """Test campo computed full_address"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Test Address',
            'street': 'Calle Test 123',
            'street2': 'Piso 2',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.country_es.id,
            'state_id': self.state_madrid.id if self.state_madrid else False,
        })
        
        full_address = address.full_address
        self.assertIn('Calle Test 123', full_address)
        self.assertIn('Madrid', full_address)
        self.assertIn('28001', full_address)

    def test_04_require_appointment_flag(self):
        """Test flag de cita previa"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección con cita',
            'street': 'Calle Test',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.country_es.id,
            'require_appointment': True,
        })
        
        self.assertTrue(address.require_appointment)

    def test_05_tail_lift_required_flag(self):
        """Test flag de camión con pluma"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección con pluma',
            'street': 'Calle Test',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.country_es.id,
            'tail_lift_required': True,
        })
        
        self.assertTrue(address.tail_lift_required)


class TestDistributorLabel(TransactionCase):
    """Tests para modelo distributor.label"""

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'is_distributor': True,
        })

    def test_01_create_distributor_label(self):
        """Test creación de etiqueta de cliente final"""
        label = self.env['distributor.label'].create({
            'partner_id': self.partner.id,
            'name': 'Cliente Final 1',
            'customer_name': 'Juan Pérez',
            'customer_reference': 'CF-001',
        })
        
        self.assertEqual(label.partner_id, self.partner)
        self.assertEqual(label.name, 'Cliente Final 1')
        self.assertEqual(label.customer_name, 'Juan Pérez')
        self.assertTrue(label.active)

    def test_02_label_with_tax_id(self):
        """Test etiqueta con NIF/CIF"""
        label = self.env['distributor.label'].create({
            'partner_id': self.partner.id,
            'name': 'Cliente con NIF',
            'customer_name': 'Empresa Test SL',
            'tax_id': 'B12345678',
        })
        
        self.assertEqual(label.tax_id, 'B12345678')

    def test_03_label_print_on_delivery_note(self):
        """Test flag de impresión en albarán"""
        label = self.env['distributor.label'].create({
            'partner_id': self.partner.id,
            'name': 'Cliente con impresión',
            'customer_name': 'Test Customer',
            'print_on_delivery_note': True,
        })
        
        self.assertTrue(label.print_on_delivery_note)

    def test_04_label_hide_company_info(self):
        """Test flag de ocultar info empresa"""
        label = self.env['distributor.label'].create({
            'partner_id': self.partner.id,
            'name': 'Cliente sin info empresa',
            'customer_name': 'Test Customer',
            'hide_company_info': True,
        })
        
        self.assertTrue(label.hide_company_info)


class TestSaleOrderDelivery(TransactionCase):
    """Tests para integración de sale.order con direcciones y etiquetas"""

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'is_distributor': True,
        })
        self.country_es = self.env.ref('base.es')
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'list_price': 100.0,
        })

    def test_01_order_with_delivery_address(self):
        """Test pedido con dirección de entrega"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección Test',
            'street': 'Calle Test 123',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.country_es.id,
        })
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'delivery_address_id': address.id,
        })
        
        self.assertEqual(order.delivery_address_id, address)
        self.assertIn('Calle Test 123', order.delivery_address_display)

    def test_02_order_with_distributor_label(self):
        """Test pedido con etiqueta de cliente final"""
        label = self.env['distributor.label'].create({
            'partner_id': self.partner.id,
            'name': 'Cliente Final Test',
            'customer_name': 'Juan Pérez',
            'customer_reference': 'CF-001',
        })
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'distributor_label_id': label.id,
        })
        
        self.assertEqual(order.distributor_label_id, label)
        self.assertEqual(order.final_customer_name, 'Juan Pérez')

    def test_03_sync_shipping_address(self):
        """Test sincronización de dirección de envío"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección Sync',
            'street': 'Calle Sync 456',
            'city': 'Barcelona',
            'zip': '08001',
            'country_id': self.country_es.id,
        })
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'delivery_address_id': address.id,
        })
        
        # Verificar que se sincronizó partner_shipping_id
        self.assertTrue(order.partner_shipping_id)
        self.assertEqual(order.partner_shipping_id.type, 'delivery')
        self.assertIn('Calle Sync 456', order.partner_shipping_id.street)

    def test_04_order_with_customer_reference(self):
        """Test pedido con referencia de cliente final"""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'customer_delivery_reference': 'ALB-2024-001',
        })
        
        self.assertEqual(order.customer_delivery_reference, 'ALB-2024-001')

    def test_05_final_customer_info_computed(self):
        """Test campos computed de cliente final"""
        label = self.env['distributor.label'].create({
            'partner_id': self.partner.id,
            'name': 'Cliente Computed',
            'customer_name': 'María García',
            'customer_reference': 'CF-002',
        })
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'distributor_label_id': label.id,
            'customer_delivery_reference': 'ALB-2024-002',
        })
        
        self.assertEqual(order.final_customer_name, 'María García')
        self.assertEqual(order.final_customer_reference, 'CF-002')

    def test_06_onchange_delivery_address(self):
        """Test onchange de dirección de entrega"""
        address = self.env['delivery.address'].create({
            'partner_id': self.partner.id,
            'name': 'Dirección Onchange',
            'street': 'Calle Onchange 789',
            'city': 'Valencia',
            'zip': '46001',
            'country_id': self.country_es.id,
            'require_appointment': True,
        })
        
        order = self.env['sale.order'].new({
            'partner_id': self.partner.id,
        })
        
        order.delivery_address_id = address
        order._onchange_delivery_address_id()
        
        # Verificar que se actualizó partner_shipping_id
        self.assertTrue(order.partner_shipping_id)
