# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestSaleDeliveryAddress(TransactionCase):

    def setUp(self):
        super(TestSaleDeliveryAddress, self).setUp()

        # Empresa de test
        self.company = self.env.ref('base.main_company')

        # Cliente normal (no distribuidor)
        self.partner_normal = self.env['res.partner'].create({
            'name': 'Cliente Normal de Prueba',
            'street': 'Calle Test 123',
            'city': 'Madrid',
            'zip': '28001',
            'country_id': self.env.ref('base.es').id,
            'email': 'cliente@test.com',
            'phone': '666777888',
            'is_distributor': False,
        })

        # Cliente distribuidor
        self.partner_distributor = self.env['res.partner'].create({
            'name': 'Distribuidor de Prueba',
            'street': 'Avenida Principal 456',
            'city': 'Barcelona',
            'zip': '08001',
            'country_id': self.env.ref('base.es').id,
            'email': 'distribuidor@test.com',
            'phone': '666999000',
            'is_distributor': True,
        })

        # Dirección de entrega para el distribuidor
        self.delivery_address_1 = self.env['res.partner'].create({
            'name': 'Almacén Central',
            'type': 'delivery',
            'parent_id': self.partner_distributor.id,
            'street': 'Polígono Industrial 1',
            'city': 'Valencia',
            'zip': '46001',
            'country_id': self.env.ref('base.es').id,
            'email': 'almacen@test.com',
            'phone': '666111222',
        })

        # Usuario vendedor
        self.user_salesman = self.env['res.users'].create({
            'name': 'Vendedor Test',
            'login': 'vendedor_test',
            'email': 'vendedor@test.com',
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_salesman').id])],
        })

        # Usuario gerente
        self.user_manager = self.env['res.users'].create({
            'name': 'Gerente Test',
            'login': 'gerente_test',
            'email': 'gerente@test.com',
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_manager').id])],
        })

        # Producto para los pedidos
        self.product = self.env['product.product'].create({
            'name': 'Producto Test',
            'type': 'product',
            'list_price': 100.0,
        })

        # Crear pedido para cliente normal
        self.order_normal = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
            'user_id': self.user_salesman.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })

        # Crear pedido para distribuidor
        self.order_distributor = self.env['sale.order'].create({
            'partner_id': self.partner_distributor.id,
            'user_id': self.user_salesman.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })

    def test_inline_delivery_address_creation(self):
        """Probar la creación inline de una dirección de entrega desde el pedido"""
        # Comprobar que el cliente normal no es distribuidor
        self.assertFalse(self.order_normal.is_distributor_customer)

        # Modificar los campos de dirección de entrega
        self.order_normal.write({
            'delivery_name': 'Contacto de Entrega Test',
            'delivery_street': 'Calle Nueva 789',
            'delivery_city': 'Sevilla',
            'delivery_zip': '41001',
            'delivery_country_id': self.env.ref('base.es').id,
            'delivery_phone': '666333444',
            'delivery_email': 'entrega@test.com',
        })

        # Crear una nueva dirección de entrega
        result = self.order_normal.action_create_delivery_address()
        self.assertEqual(result['params']['type'], 'success')

        # Verificar que se ha creado la dirección
        delivery_address = self.env['res.partner'].search([
            ('parent_id', '=', self.partner_normal.id),
            ('type', '=', 'delivery'),
            ('street', '=', 'Calle Nueva 789')
        ])
        self.assertTrue(delivery_address)

        # Verificar que se ha asignado al pedido
        self.assertEqual(self.order_normal.partner_shipping_id, delivery_address)

        # Verificar que se ha registrado en el historial
        messages = self.order_normal.message_ids.filtered(lambda m: 'Nueva dirección de entrega creada' in m.body)
        self.assertTrue(messages)

    def test_delivery_address_update_and_logging(self):
        """Probar la actualización de una dirección de entrega y el registro de cambios"""
        # Confirmar el pedido
        self.order_normal.action_confirm()

        # Cambiar a usuario gerente para poder modificar después de confirmar
        self.order_normal = self.order_normal.with_user(self.user_manager)

        # Modificar la dirección de entrega
        old_city = self.order_normal.delivery_city
        new_city = 'Málaga'
        self.order_normal.delivery_city = new_city

        # Verificar que se ha actualizado
        self.assertEqual(self.order_normal.partner_shipping_id.city, new_city)

        # Verificar que se ha marcado como modificada
        self.assertTrue(self.order_normal.delivery_address_modified)

        # Verificar que se ha registrado en el historial
        messages = self.order_normal.message_ids.filtered(lambda m: 'Dirección de entrega actualizada' in m.body)
        self.assertTrue(messages)
        self.assertTrue(old_city in messages[0].body and new_city in messages[0].body)

    def test_distributor_workflow(self):
        """Probar el flujo de trabajo con distribuidores"""
        # Verificar que el cliente es distribuidor
        self.assertTrue(self.order_distributor.is_distributor_customer)

        # Activar el uso de dirección alternativa
        self.order_distributor.use_alternative_delivery = True

        # Verificar que se ha seleccionado la primera dirección disponible
        self.assertEqual(self.order_distributor.selected_delivery_partner_id, self.delivery_address_1)

        # Crear una nueva dirección de entrega
        self.order_distributor.write({
            'delivery_name': 'Almacén Secundario',
            'delivery_street': 'Polígono Industrial 2',
            'delivery_city': 'Zaragoza',
            'delivery_zip': '50001',
            'delivery_country_id': self.env.ref('base.es').id,
        })

        result = self.order_distributor.action_create_delivery_address()
        self.assertEqual(result['params']['type'], 'success')

        # Verificar que se ha creado la dirección
        delivery_address = self.env['res.partner'].search([
            ('parent_id', '=', self.partner_distributor.id),
            ('type', '=', 'delivery'),
            ('city', '=', 'Zaragoza')
        ])
        self.assertTrue(delivery_address)

        # Verificar que ahora hay dos direcciones de entrega
        delivery_addresses = self.partner_distributor.child_ids.filtered(lambda r: r.type == 'delivery')
        self.assertEqual(len(delivery_addresses), 2)

    @mute_logger('odoo.models.unlink')
    def test_validation_constraints(self):
        """Probar las restricciones de validación y permisos"""
        # Confirmar el pedido
        self.order_normal.action_confirm()

        # Cambiar a usuario vendedor (sin permisos de gerente)
        self.order_normal = self.order_normal.with_user(self.user_salesman)

        # Intentar modificar la dirección de entrega (debería fallar)
        with self.assertRaises(AccessError):
            self.order_normal.delivery_city = 'Ciudad Prohibida'

        # Intentar crear una dirección sin datos obligatorios
        self.order_distributor = self.order_distributor.with_user(self.user_salesman)
        self.order_distributor.delivery_name = ''
        self.order_distributor.delivery_street = ''

        result = self.order_distributor.action_create_delivery_address()
        self.assertEqual(result['params']['type'], 'danger')
        self.assertIn('obligatorios', result['params']['message'])

    def test_multicompany(self):
        """Probar el funcionamiento en entorno multiempresa"""
        # Crear una segunda empresa
        company2 = self.env['res.company'].create({
            'name': 'Empresa Test 2',
            'currency_id': self.env.ref('base.EUR').id,
        })

        # Crear un pedido para la segunda empresa
        order_company2 = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
            'user_id': self.user_manager.id,
            'company_id': company2.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })

        # Modificar los campos de dirección de entrega
        order_company2.write({
            'delivery_name': 'Contacto Empresa 2',
            'delivery_street': 'Calle Empresa 2',
            'delivery_city': 'Ciudad Empresa 2',
        })

        # Crear una nueva dirección de entrega
        result = order_company2.action_create_delivery_address()
        self.assertEqual(result['params']['type'], 'success')

        # Verificar que se ha creado la dirección con la empresa correcta
        delivery_address = self.env['res.partner'].search([
            ('parent_id', '=', self.partner_normal.id),
            ('type', '=', 'delivery'),
            ('street', '=', 'Calle Empresa 2')
        ])
        self.assertTrue(delivery_address)
        self.assertEqual(delivery_address.company_id, company2)
