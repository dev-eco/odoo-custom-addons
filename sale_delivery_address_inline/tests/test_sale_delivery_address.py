# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch


class TestSaleDeliveryAddress(TransactionCase):
    
    def setUp(self):
        super(TestSaleDeliveryAddress, self).setUp()
        
        # Crear datos de prueba
        self.partner_normal = self.env['res.partner'].create({
            'name': 'Cliente Normal Test',
            'is_company': True,
            'is_distributor': False,
            'street': 'Test Street 123',
            'city': 'Test City',
            'zip': '12345',
            'country_id': self.env.ref('base.es').id,
        })
        
        self.partner_distributor = self.env['res.partner'].create({
            'name': 'Distribuidor Test',
            'is_company': True,
            'is_distributor': True,
            'street': 'Distributor Street 456',
            'city': 'Distributor City',
            'zip': '67890',
            'country_id': self.env.ref('base.es').id,
        })
        
        # Direcciones de entrega para distribuidor
        self.delivery_address_1 = self.env['res.partner'].create({
            'name': 'Almacén A',
            'parent_id': self.partner_distributor.id,
            'type': 'delivery',
            'street': 'Warehouse Street 1',
            'city': 'Warehouse City A',
            'zip': '11111',
            'country_id': self.env.ref('base.es').id,
        })
        
        self.delivery_address_2 = self.env['res.partner'].create({
            'name': 'Almacén B',
            'parent_id': self.partner_distributor.id,
            'type': 'delivery',
            'street': 'Warehouse Street 2',
            'city': 'Warehouse City B',
            'zip': '22222',
            'country_id': self.env.ref('base.es').id,
        })
        
        # Producto de prueba
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'list_price': 100.0,
        })
        
        # Usuarios de prueba
        self.sale_user = self.env.ref('base.user_demo')  # Usuario normal de ventas
        self.sale_manager = self.env.ref('base.user_admin')  # Manager

    def test_partner_distributor_fields(self):
        """Test que los campos de distribuidor funcionan correctamente"""
        
        # Verificar que el distribuidor tiene el flag correcto
        self.assertTrue(self.partner_distributor.is_distributor)
        self.assertFalse(self.partner_normal.is_distributor)
        
        # Verificar contador de direcciones de entrega
        self.assertEqual(self.partner_distributor.delivery_address_count, 2)
        self.assertEqual(self.partner_normal.delivery_address_count, 0)

    def test_sale_order_distributor_auto_detection(self):
        """Test que el sistema detecta automáticamente distribuidores"""
        
        # Crear pedido con distribuidor
        order_dist = self.env['sale.order'].create({
            'partner_id': self.partner_distributor.id,
        })
        
        # Verificar que se activa automáticamente el modo distribuidor
        self.assertTrue(order_dist.use_alternative_delivery)
        
        # Crear pedido con cliente normal
        order_normal = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
        })
        
        # Verificar que NO se activa el modo distribuidor
        self.assertFalse(order_normal.use_alternative_delivery)

    def test_sale_order_delivery_address_selection(self):
        """Test selección de dirección de entrega para distribuidores"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_distributor.id,
        })
        
        # Seleccionar una dirección de entrega específica
        order.selected_delivery_partner_id = self.delivery_address_1
        
        # Verificar que los campos inline reflejan la dirección seleccionada
        order._compute_delivery_fields()
        self.assertEqual(order.delivery_street, 'Warehouse Street 1')
        self.assertEqual(order.delivery_city, 'Warehouse City A')
        
        # Cambiar a otra dirección
        order.selected_delivery_partner_id = self.delivery_address_2
        order._compute_delivery_fields()
        self.assertEqual(order.delivery_street, 'Warehouse Street 2')
        self.assertEqual(order.delivery_city, 'Warehouse City B')

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
            'selected_delivery_partner_id': self.delivery_address_1.id,
        })
        
        # Contar mensajes iniciales
        initial_message_count = len(order.message_ids)
        
        # Actualizar dirección
        update_data = {
            'street': 'Updated Warehouse Street',
            'phone': '+34 111 222 333',
        }
        
        order._update_delivery_address(update_data)
        
        # Verificar que se actualizó la dirección
        self.assertEqual(self.delivery_address_1.street, 'Updated Warehouse Street')
        self.assertEqual(self.delivery_address_1.phone, '+34 111 222 333')
        
        # Verificar que se registró el cambio en chatter
        final_message_count = len(order.message_ids)
        self.assertGreater(final_message_count, initial_message_count)

    def test_permission_controls_draft_state(self):
        """Test controles de permisos en estado borrador"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
            'state': 'draft',
        })
        
        # En estado borrador, el usuario debe poder editar
        with patch.object(self.env.user, 'has_group') as mock_has_group:
            mock_has_group.return_value = True  # Simular que tiene permisos de ventas
            order._compute_can_edit_delivery()
            self.assertTrue(order.can_edit_delivery)

    def test_permission_controls_confirmed_state(self):
        """Test controles de permisos después de confirmación"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
            'state': 'sale',  # Estado confirmado
        })
        
        # Usuario normal NO debe poder editar después de confirmación
        with patch.object(self.env.user, 'has_group') as mock_has_group:
            mock_has_group.side_effect = lambda group: group == 'sales_team.group_sale_salesman'
            order._compute_can_edit_delivery()
            self.assertFalse(order.can_edit_delivery)
        
        # Sales Manager SÍ debe poder editar después de confirmación
        with patch.object(self.env.user, 'has_group') as mock_has_group:
            mock_has_group.side_effect = lambda group: group == 'sales_team.group_sale_manager'
            order._compute_can_edit_delivery()
            self.assertTrue(order.can_edit_delivery)

    def test_delivery_address_creation_validation(self):
        """Test validaciones en creación de direcciones de entrega"""
        
        # Test con partner inexistente
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create_delivery_address(99999, {
                'name': 'Test Address',
                'street': 'Test Street',
            })

    def test_distributor_consistency_validation(self):
        """Test validación de consistencia para distribuidores"""
        
        # Un contacto hijo no puede ser distribuidor
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Invalid Distributor',
                'parent_id': self.partner_distributor.id,
                'is_distributor': True,
            })

    def test_get_delivery_addresses_for_selection(self):
        """Test obtención de direcciones para widget de selección"""
        
        # Para distribuidor
        addresses = self.partner_distributor.get_delivery_addresses_for_selection()
        self.assertEqual(len(addresses), 3)  # Principal + 2 delivery
        
        # Verificar formato de tuplas (id, display_name)
        for addr_id, display_name in addresses:
            self.assertTrue(isinstance(addr_id, int))
            self.assertTrue(isinstance(display_name, str))
        
        # Para cliente normal
        addresses_normal = self.partner_normal.get_delivery_addresses_for_selection()
        self.assertEqual(len(addresses_normal), 1)  # Solo principal

    def test_action_create_delivery_address(self):
        """Test acción para crear dirección de entrega"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
        })
        
        # Establecer campos inline
        order.delivery_name = 'Action Test Address'
        order.delivery_street = 'Action Test Street'
        order.delivery_city = 'Action Test City'
        
        # Ejecutar acción
        result = order.action_create_delivery_address()
        
        # Verificar que devuelve notificación de éxito
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'success')
        
        # Verificar que se creó la dirección
        delivery_addresses = self.env['res.partner'].search([
            ('parent_id', '=', self.partner_normal.id),
            ('type', '=', 'delivery'),
            ('name', '=', 'Action Test Address'),
        ])
        self.assertEqual(len(delivery_addresses), 1)

    def test_onchange_methods(self):
        """Test métodos onchange"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_distributor.id,
        })
        
        # Test onchange de selected_delivery_partner_id
        order.selected_delivery_partner_id = self.delivery_address_1
        order._onchange_selected_delivery_partner()
        self.assertEqual(order.partner_shipping_id, self.delivery_address_1)
        
        # Test onchange de partner_id
        order.partner_id = self.partner_normal
        order._onchange_partner_id_delivery()
        self.assertFalse(order.use_alternative_delivery)
        self.assertFalse(order.selected_delivery_partner_id)

    def test_write_permission_validation(self):
        """Test validación de permisos en método write"""
        
        order = self.env['sale.order'].create({
            'partner_id': self.partner_normal.id,
            'state': 'sale',  # Estado confirmado
        })
        
        # Simular usuario sin permisos de manager
        with patch.object(self.env.user, 'has_group') as mock_has_group:
            mock_has_group.side_effect = lambda group: group == 'sales_team.group_sale_salesman'
            
            # Intentar modificar campo de entrega debe fallar
            with self.assertRaises(UserError):
                order.write({'delivery_street': 'New Street'})

    def test_multi_company_support(self):
        """Test soporte multi-empresa"""
        
        # Crear empresa adicional
        company2 = self.env['res.company'].create({
            'name': 'Test Company 2',
        })
        
        # Crear partner en empresa 2
        partner_company2 = self.env['res.partner'].create({
            'name': 'Partner Company 2',
            'company_id': company2.id,
        })
        
        # Crear dirección de entrega
        delivery_data = {
            'name': 'Multi Company Delivery',
            'street': 'Multi Company Street',
            'city': 'Multi Company City',
        }
        
        delivery_address = self.env['res.partner'].create_delivery_address(
            partner_company2.id, 
            delivery_data
        )
        
        # Verificar que se asignó la empresa correcta
        self.assertEqual(delivery_address.company_id, company2)

    def tearDown(self):
        super(TestSaleDeliveryAddress, self).tearDown()
