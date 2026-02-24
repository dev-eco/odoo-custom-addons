# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestPortalChatter(TransactionCase):

    def setUp(self):
        super().setUp()

        # Crear partner distribuidor
        self.partner_portal = self.env['res.partner'].create({
            'name': 'Distribuidor Portal Test',
            'email': 'distribuidor@test.com',
        })

        # Crear usuario portal para el distribuidor
        self.user_portal = self.env['res.users'].create({
            'name': 'Usuario Portal Test',
            'login': 'portal_user',
            'email': 'portal@test.com',
            'partner_id': self.partner_portal.id,
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        # Crear pedido de venta para el distribuidor
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_portal.id,
            'state': 'draft',
        })

        # Crear otro partner y pedido (que NO pertenece al usuario portal)
        self.other_partner = self.env['res.partner'].create({
            'name': 'Otro Cliente',
        })
        self.other_order = self.env['sale.order'].create({
            'partner_id': self.other_partner.id,
        })

    def test_01_portal_user_can_read_own_order_messages(self):
        """Test: Usuario portal puede leer mensajes de SU pedido"""
        # Crear mensaje en el pedido del usuario portal
        message = self.sale_order.message_post(
            body="Mensaje de prueba en el pedido",
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        # Cambiar a contexto de usuario portal
        message_as_portal = message.with_user(self.user_portal)

        # Debe poder leer el mensaje
        self.assertTrue(message_as_portal.body)
        self.assertEqual(message_as_portal.model, 'sale.order')

    def test_02_portal_user_cannot_read_other_order_messages(self):
        """Test: Usuario portal NO puede leer mensajes de pedidos de otros"""
        # Crear mensaje en pedido de otro cliente
        message = self.other_order.message_post(
            body="Mensaje en pedido de otro",
            message_type='comment',
        )

        # Buscar mensajes como usuario portal
        messages_portal = self.env['mail.message'].with_user(self.user_portal).search([
            ('id', '=', message.id)
        ])

        # NO debe encontrar el mensaje
        self.assertEqual(len(messages_portal), 0)

    def test_03_portal_user_can_create_message_in_own_order(self):
        """Test: Usuario portal puede crear mensajes en SU pedido"""
        # Como usuario portal, crear mensaje
        self.sale_order.with_user(self.user_portal).message_post(
            body="Consulta del distribuidor",
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        # Verificar que el mensaje se creó
        messages = self.sale_order.message_ids.filtered(
            lambda m: m.body == "<p>Consulta del distribuidor</p>"
        )
        self.assertEqual(len(messages), 1)

    def test_04_portal_user_cannot_create_message_in_other_order(self):
        """Test: Usuario portal NO puede crear mensajes en pedidos de otros"""
        with self.assertRaises(AccessError):
            self.other_order.with_user(self.user_portal).message_post(
                body="Intento de mensaje en pedido ajeno",
                message_type='comment',
            )

    def test_05_internal_user_can_send_message_to_portal(self):
        """Test: Usuario interno puede enviar mensaje que el portal verá"""
        # Usuario interno (admin) envía mensaje
        message = self.sale_order.message_post(
            body="Número de seguimiento: ABC123",
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

        # Usuario portal debe poder verlo
        messages_portal = self.env['mail.message'].with_user(self.user_portal).search([
            ('id', '=', message.id)
        ])
        self.assertEqual(len(messages_portal), 1)
        self.assertIn('ABC123', messages_portal.body)

    def test_06_portal_user_cannot_see_internal_notes(self):
        """Test: Usuario portal NO ve notas internas"""
        # Crear nota interna (message_type='comment' con subtype interno)
        message = self.sale_order.message_post(
            body="Nota interna confidencial",
            message_type='comment',
            subtype_xmlid='mail.mt_note',  # Nota interna
        )

        # Buscar como usuario portal
        messages_portal = self.env['mail.message'].with_user(self.user_portal).search([
            ('id', '=', message.id)
        ])

        # NO debe verla (depende de la configuración del subtype)
        # Nota: Puede requerir ajuste en record rules
        self.assertEqual(len(messages_portal), 0)

    def test_07_portal_user_cannot_delete_messages(self):
        """Test: Usuario portal NO puede eliminar mensajes"""
        message = self.sale_order.message_post(
            body="Mensaje a eliminar",
            message_type='comment',
        )

        with self.assertRaises(AccessError):
            message.with_user(self.user_portal).unlink()
