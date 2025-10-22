# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestSaleDeliveryAddress(TransactionCase):

    def setUp(self):
        super(TestSaleDeliveryAddress, self).setUp()
        
        # Empresa de test
        self.company = self.env.ref('base.main_company')
        
        # Cliente normal (no distribuidor)
        self.partner_normal = self.env['res.partner'].create({
            'name': 'Cliente Normal de Prueba',
            'street': 'Calle Test 123',
            'city': 'Ciudad Test',
            'zip': '12345',
            'country_id': self.env.ref('base.es').id,
            'is_company': True,
            'is_distributor': False,
        })
        
        # Cliente distribuidor
        self.partner_distributor = self.env['res.partner'].create({
            'name': 'Distribuidor de Prueba',
            'street': 'Avenida Distribuidor 456',
            'city': 'Ciudad Distribución',
            'zip': '54321',
            'country_id': self.env.ref('base.es').id,
            'is_company': True,
            'is_distributor': True,
            'distributor_type': 'regional',
        })
        
        # Direcciones de entrega para el distribuidor
        self.delivery_address_1 = self.env['res.partner'].create({
            'name': 'Almacén Central',
            'parent_id': self.partner_distributor.id,
            'type': 'delivery',
            'street': 'Polígono Industrial 1, Nave 5',
            'city': 'Población Logística',
            'zip': '28000',
            'country_id': self.env.ref('base.es').id,
            'phone': '+34 666 555 444',
        })
        
        self.delivery_address_2 = self.env['res.partner'].create({
            'name': 'Punto de Venta Norte',
            'parent_id': self.partner_distributor.id,
            'type': 'delivery',
            'street': 'Calle Comercio 78',
            'city': 'Ciudad Norte',
            'zip': '08000',
            'country_id': self.env.ref('base.es').id,
            'phone': '+34 666 777 888',
        })
        
        # Producto para los pedidos
        self.product = self.env['product.product'].create({
            'name': 'Producto de Prueba',
            'type': 'product',
            'list_price': 100.00,
        })

    def test_inline_delivery_address_creation(self):
        """Test creación de dirección de entrega desde campos inline"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
        })
        
        # Establecer datos de dirección inline
        address_data = {
            'name': 'Nueva Dirección Test',
            'street': 'New Address Street 999',
            'city': 'New City',
            'zip': '99999',
            'phone': '+34 999 888 777',
            'email': 'test@newaddress.com',
        }
        
        # Crear nueva dirección
        new_address = order._create_new_delivery_address(address_data)
        
        # Verificar que se creó correctamente
        self.assertEqual(new_address.name, 'Nueva Dirección Test')
        self.assertEqual(new_address.parent_id, self.partner_normal)
        self.assertEqual(new_address.type, 'delivery')
        self.assertEqual(new_address.street, 'New Address Street 999')
        self.assertEqual(new_address.city, 'New City')
        
        # Verificar que el pedido está vinculado a la nueva dirección
        self.assertEqual(order.partner_shipping_id, new_address)

    def test_delivery_address_update_and_logging(self):
        """Test actualización de dirección y logging en chatter"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_distributor.id,
            'partner_shipping_id': self.delivery_address_1.id,
        })
        
        # Contar mensajes iniciales
        initial_message_count = len(order.message_ids)
        
        # Cambiar campos inline
        order.delivery_street = 'Updated Warehouse Street'
        order.delivery_phone = '+34 111 222 333'
        
        # Verificar que se actualizó la dirección
        self.assertEqual(self.delivery_address_1.street, 'Updated Warehouse Street')
        self.assertEqual(self.delivery_address_1.phone, '+34 111 222 333')
        
        # Verificar que no se registró cambio en chatter (porque el pedido está en borrador)
        final_message_count = len(order.message_ids)
        self.assertEqual(initial_message_count, final_message_count)
        
        # Confirmar pedido
        order.write({
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.00,
            })],
        })
        order.action_confirm()
        
        # Cambiar dirección después de confirmar
        order.delivery_city = 'Ciudad Actualizada'
        
        # Verificar que se registró el cambio en chatter
        final_message_count = len(order.message_ids)
        self.assertGreater(final_message_count, initial_message_count)
        
        # Verificar que se marcó como modificada
        self.assertTrue(order.delivery_address_modified)

    def test_distributor_workflow(self):
        """Test flujo de trabajo para distribuidores"""
        
        # Crear un pedido para distribuidor
        order = self.env['sale.order'].create({
            'partner_id': self.partner_distributor.id,
        })
        
        # Verificar que se detecta como distribuidor
        self.assertTrue(order.is_distributor_customer)
        
        # Activar dirección alternativa
        order.use_alternative_delivery = True
        
        # Verificar que se sugiere una dirección por defecto
        self.assertTrue(order.partner_shipping_id)
        self.assertTrue(order.partner_shipping_id in [self.delivery_address_1, self.delivery_address_2])
        
        # Seleccionar otra dirección específica
        order.selected_delivery_partner_id = self.delivery_address_2
        
        # Verificar que se actualizó la dirección de envío
        self.assertEqual(order.partner_shipping_id, self.delivery_address_2)
        
        # Desactivar uso de dirección alternativa
        order.use_alternative_delivery = False
        
        # Verificar que volvió a la dirección principal
        self.assertEqual(order.partner_shipping_id, self.partner_distributor)

    def test_validation_constraints(self):
        """Test restricciones y validaciones"""
        
        # Probar crear distribuidor como contacto (no debería permitirse)
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Invalid Distributor',
                'parent_id': self.partner_distributor.id,
                'is_distributor': True,
            })
        
        # Probar crear dirección sin datos mínimos
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
        })
        
        with self.assertRaises(UserError):
            order._create_new_delivery_address({
                'name': '',  # Falta nombre
                'street': 'Test Street',
            })
            
        with self.assertRaises(UserError):
            order._create_new_delivery_address({
                'name': 'Test Name',
                'street': '',  # Falta dirección
            })

    def test_multicompany(self):
        """Test funcionamiento multiempresa"""
        
        # Crear segunda empresa
        company2 = self.env['res.company'].create({
            'name': 'Test Company 2',
        })
        
        # Crear cliente en segunda empresa
        partner_company2 = self.env['res.partner'].with_context(company_id=company2.id).create({
            'name': 'Partner Company 2',
            'company_id': company2.id,
            'is_distributor': True,
        })
        
        # Dirección de entrega para segunda empresa
        delivery_company2 = self.env['res.partner'].with_context(company_id=company2.id).create({
            'name': 'Delivery Company 2',
            'parent_id': partner_company2.id,
            'type': 'delivery',
            'company_id': company2.id,
        })
        
        # Comprobar que cada empresa ve solo sus datos
        partners_company1 = self.env['res.partner'].with_context(company_id=self.company.id).search([
            ('is_distributor', '=', True)
        ])
        self.assertIn(self.partner_distributor, partners_company1)
        self.assertNotIn(partner_company2, partners_company1)
        
        partners_company2 = self.env['res.partner'].with_context(company_id=company2.id).search([
            ('is_distributor', '=', True)
        ])
        self.assertIn(partner_company2, partners_company2)
        
        # Comprobar que las direcciones son independientes
        order_company2 = self.env['sale.order'].with_context(company_id=company2.id).create({
            'partner_id': partner_company2.id,
            'company_id': company2.id,
        })
        
        self.assertTrue(order_company2.is_distributor_customer)
        order_company2.use_alternative_delivery = True
        self.assertEqual(order_company2.partner_shipping_id, delivery_company2)
