# -*- coding: utf-8 -*-

import logging
from odoo.tests.common import HttpCase

_logger = logging.getLogger(__name__)


class TestAPI(HttpCase):
    """Tests para API del portal"""

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Distributor',
            'is_distributor': True,
            'credit_limit': 10000.0,
        })
        self.user = self.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal@test.com',
            'partner_id': self.partner.id,
            'groups_id': [(6, 0, [
                self.env.ref('base.group_portal').id,
                self.env.ref('portal_b2b_base.group_portal_b2b').id,
            ])],
        })

    def test_01_get_notifications_with_limit(self):
        """Test API de notificaciones con límite"""
        # Crear 150 notificaciones
        for i in range(150):
            self.env['portal.notification'].sudo().create({
                'partner_id': self.partner.id,
                'title': f'Notificación {i}',
                'message': f'Mensaje {i}',
                'notification_type': 'info',
            })
        
        # Autenticar como usuario portal
        self.authenticate(self.user.login, self.user.login)
        
        # Llamar API con límite alto
        response = self.url_open(
            '/api/notifications/list',
            data={'limit': 200},  # Intentar obtener 200
        )
        
        # Debe respetar límite máximo de 100
        data = response.json()
        self.assertTrue(data['success'])
        self.assertLessEqual(len(data['notifications']), 100)

    def test_02_get_credit_status_with_limit(self):
        """Test API de crédito con límite en búsquedas"""
        # Crear muchos pedidos pendientes
        for i in range(1500):
            self.env['sale.order'].sudo().create({
                'partner_id': self.partner.id,
                'state': 'draft',
            })
        
        # Autenticar como usuario portal
        self.authenticate(self.user.login, self.user.login)
        
        # Llamar API
        response = self.url_open('/api/distributor/credit_status')
        
        # Debe funcionar sin timeout (límite de 1000 aplicado)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
