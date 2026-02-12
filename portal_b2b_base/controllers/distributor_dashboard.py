# -*- coding: utf-8 -*-

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class DistributorDashboard(http.Controller):
    """Controlador unificado para el dashboard del distribuidor."""
    
    @http.route(['/api/distributor/dashboard'], type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self, **kw):
        """
        API unificada para obtener TODOS los datos del distribuidor.
        
        Returns:
            dict: Datos completos del distribuidor
        """
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            # Recopilar TODA la información en una sola llamada
            data = {
                'distributor': {
                    'name': partner.name,
                    'email': partner.email,
                    'phone': partner.phone,
                    'credit_limit': float(partner.credit_limit),
                    'available_credit': float(partner.available_credit),
                    'total_invoiced_year': float(partner.total_invoiced_year),
                },
                'stats': {
                    'pending_orders': request.env['sale.order'].search_count([
                        ('partner_id', '=', partner.id),
                        ('state', 'in', ['draft', 'sent'])
                    ]),
                    'confirmed_orders': request.env['sale.order'].search_count([
                        ('partner_id', '=', partner.id),
                        ('state', '=', 'sale')
                    ]),
                    'unpaid_invoices': request.env['account.move'].search_count([
                        ('partner_id', '=', partner.id),
                        ('move_type', '=', 'out_invoice'),
                        ('payment_state', '!=', 'paid')
                    ]),
                },
                'recent_orders': [],
                'delivery_addresses': [],
                'distributor_labels': [],
            }
            
            # Pedidos recientes
            recent_orders = request.env['sale.order'].search([
                ('partner_id', '=', partner.id)
            ], limit=5, order='date_order desc')
            
            for order in recent_orders:
                data['recent_orders'].append({
                    'id': order.id,
                    'name': order.name,
                    'date': order.date_order.strftime('%d/%m/%Y'),
                    'state': order.state,
                    'total': float(order.amount_total),
                })
            
            # Direcciones si el módulo está instalado
            try:
                addresses = request.env['delivery.address'].search([
                    ('partner_id', '=', partner.id),
                    ('active', '=', True)
                ])
                for addr in addresses:
                    data['delivery_addresses'].append({
                        'id': addr.id,
                        'name': addr.name,
                        'full_address': addr.full_address,
                        'is_default': addr.is_default,
                    })
            except Exception as e:
                _logger.debug(f"Módulo delivery_addresses no disponible: {str(e)}")
            
            # Etiquetas si están disponibles
            try:
                labels = request.env['distributor.label'].search([
                    ('partner_id', '=', partner.id),
                    ('active', '=', True)
                ])
                for label in labels:
                    data['distributor_labels'].append({
                        'id': label.id,
                        'name': label.name,
                        'customer_name': label.customer_name,
                    })
            except Exception as e:
                _logger.debug(f"Módulo distributor_label no disponible: {str(e)}")
            
            return {'success': True, 'data': data}
            
        except Exception as e:
            _logger.error(f"Error obteniendo dashboard: {str(e)}")
            return {'error': str(e)}
