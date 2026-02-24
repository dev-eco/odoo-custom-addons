# -*- coding: utf-8 -*-
{
    'name': 'Portal B2B - Chatter para Distribuidores',
    'version': '17.0.1.0.0',
    'category': 'Portal',
    'summary': 'Habilita chatter en pedidos de venta para usuarios portal (distribuidores)',
    'description': """
        Portal B2B - Chatter
        ====================

        Permite que los usuarios distribuidores (tipo portal) puedan:
        - Ver historial de mensajes en sus pedidos
        - Enviar mensajes/consultas sobre sus pedidos
        - Recibir notificaciones del equipo interno (ej: números de seguimiento)

        Características:
        - Solo ven mensajes de SUS pedidos (seguridad por record rules)
        - Solo ven mensajes públicos (no notas internas)
        - Pueden adjuntar archivos (funcionalidad ya implementada en el core)
        - Arquitectura modular para extender a otros modelos en el futuro
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',

    'depends': [
        'portal_b2b_base',
        'sale',
        'mail',
        'portal',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/portal_b2b_chatter_security.xml',
        'views/portal_sale_order_templates.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'portal_b2b_chatter/static/src/scss/portal_chatter.scss',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
