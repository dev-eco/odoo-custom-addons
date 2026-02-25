# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestPortalVisibilityFix(TransactionCase):

    def setUp(self):
        super().setUp()

        # Crear partner sin usuario de portal
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'email': 'test@distributor.com',
            'is_company': True,
        })

        # Crear pedido ANTES de crear usuario
        self.old_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'state': 'sale',
        })

        # Portal group
        self.portal_group = self.env.ref('base.group_portal')
        self.portal_b2b_group = self.env.ref('portal_b2b_base.group_portal_b2b_distributor')

    def test_01_order_invisible_before_portal_user(self):
        """Pedido creado antes del usuario portal tiene portal_visible=False."""
        self.assertFalse(
            self.old_order.portal_visible,
            "Pedido debe tener portal_visible=False antes de crear usuario portal"
        )

    def test_02_order_visible_after_portal_user(self):
        """Pedido debe ser visible después de crear usuario portal."""
        # Crear usuario de portal
        user = self.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal@test.com',
            'partner_id': self.partner.id,
            'groups_id': [(6, 0, [self.portal_group.id, self.portal_b2b_group.id])],
        })

        # Forzar recálculo (simula la acción del fix)
        self.old_order._compute_portal_visible()

        self.assertTrue(
            self.old_order.portal_visible,
            "Pedido debe tener portal_visible=True después de crear usuario portal"
        )

    def test_03_orders_domain_includes_old_orders(self):
        """El domain del portal debe incluir pedidos antiguos."""
        # Crear usuario de portal
        user = self.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal2@test.com',
            'partner_id': self.partner.id,
            'groups_id': [(6, 0, [self.portal_group.id, self.portal_b2b_group.id])],
        })

        # Simular domain del controlador
        commercial_partner = self.partner.commercial_partner_id
        related_partners = self.env['res.partner'].search([
            '|',
            ('id', '=', commercial_partner.id),
            ('commercial_partner_id', '=', commercial_partner.id)
        ])

        domain = [
            ('partner_id', 'in', related_partners.ids),
            ('state', '!=', 'cancel'),
        ]

        orders = self.env['sale.order'].search(domain)

        self.assertIn(
            self.old_order,
            orders,
            "El domain debe incluir el pedido antiguo"
        )

    def test_04_access_token_generation(self):
        """Access token debe generarse para pedidos antiguos."""
        # Pedido antiguo sin token
        old_order_no_token = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'state': 'sale',
            'access_token': False,
        })

        self.assertFalse(old_order_no_token.access_token)

        # Ejecutar fix
        self.env['sale.order']._ensure_access_tokens()

        old_order_no_token.invalidate_recordset()

        self.assertTrue(
            old_order_no_token.access_token,
            "Pedido antiguo debe tener access_token después del fix"
        )

    def test_05_invoice_access_token_generation(self):
        """Access token debe generarse para facturas antiguas."""
        # Crear factura sin token
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'state': 'draft',
            'access_token': False,
        })
        invoice.action_post()

        # Ejecutar fix
        self.env['account.move']._ensure_access_tokens()

        invoice.invalidate_recordset()

        self.assertTrue(
            invoice.access_token,
            "Factura debe tener access_token después del fix"
        )

    def test_06_diagnostic_action(self):
        """La acción de diagnóstico debe ejecutarse sin errores."""
        # Crear usuario
        user = self.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal3@test.com',
            'partner_id': self.partner.id,
            'groups_id': [(6, 0, [self.portal_group.id, self.portal_b2b_group.id])],
        })

        # Ejecutar diagnóstico
        result = self.partner.action_diagnose_portal_orders()

        self.assertEqual(
            result.get('type'),
            'ir.actions.client',
            "Diagnóstico debe retornar una acción client"
        )

    def test_07_child_partner_orders_visible(self):
        """Pedidos de partners hijos deben ser visibles en el portal del padre."""
        # Crear partner hijo
        child_partner = self.env['res.partner'].create({
            'name': 'Child Contact',
            'parent_id': self.partner.id,
            'type': 'contact',
        })

        # Crear pedido en partner hijo
        child_order = self.env['sale.order'].create({
            'partner_id': child_partner.id,
            'state': 'sale',
        })

        # Crear usuario en padre
        user = self.env['res.users'].create({
            'name': 'Portal User Parent',
            'login': 'portal4@test.com',
            'partner_id': self.partner.id,
            'groups_id': [(6, 0, [self.portal_group.id, self.portal_b2b_group.id])],
        })

        # Domain del portal
        commercial_partner = self.partner.commercial_partner_id
        related_partners = self.env['res.partner'].search([
            '|',
            ('id', '=', commercial_partner.id),
            ('commercial_partner_id', '=', commercial_partner.id)
        ])

        domain = [
            ('partner_id', 'in', related_partners.ids),
            ('state', '!=', 'cancel'),
        ]

        orders = self.env['sale.order'].search(domain)

        self.assertIn(
            child_order,
            orders,
            "Pedidos de partners hijos deben ser visibles"
        )
