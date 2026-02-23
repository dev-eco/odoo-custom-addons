# -*- coding: utf-8 -*-

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class DistributorAPI(http.Controller):
    """API JSON para widgets y funcionalidades del portal."""
    
    # ========== CRÉDITO ==========
    
    @http.route('/api/distributor/credit_status', type='json', auth='user', website=True)
    def get_credit_status(self):
        """
        Obtener estado del crédito del distribuidor actual.
        
        Returns:
            dict: Estado del crédito con límite, usado, disponible, pendiente
        """
        try:
            partner = request.env.user.partner_id
            
            if not hasattr(partner, 'is_distributor') or not partner.is_distributor:
                return {
                    'success': False,
                    'error': _('Usuario no autorizado')
                }
            
            # Calcular pedidos pendientes (borradores y enviados)
            pending_orders = request.env['sale.order'].search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['draft', 'sent'])
            ])
            pending_amount = sum(pending_orders.mapped('amount_total'))
            
            credit_limit = float(partner.credit_limit or 0.0)
            credit_used = float(partner.credit or 0.0)
            available = credit_limit - credit_used - pending_amount
            percentage_used = (credit_used / credit_limit * 100) if credit_limit > 0 else 0
            
            return {
                'success': True,
                'data': {
                    'limit': credit_limit,
                    'used': credit_used,
                    'available': available,
                    'pending': pending_amount,
                    'percentage_used': percentage_used,
                    'currency_symbol': '€',
                }
            }
            
        except Exception as e:
            _logger.error(f"Error getting credit status: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========== NOTIFICACIONES ==========
    
    @http.route('/api/notifications/list', type='json', auth='user', website=True)
    def get_notifications(self, limit=20):
        """
        Obtener notificaciones del usuario.
        
        Args:
            limit: Número máximo de notificaciones
        
        Returns:
            dict: Lista de notificaciones y contador de no leídas
        """
        try:
            partner = request.env.user.partner_id
            
            notifications = request.env['portal.notification'].search([
                ('partner_id', '=', partner.id),
            ], limit=limit, order='create_date desc')
            
            unread_count = request.env['portal.notification'].search_count([
                ('partner_id', '=', partner.id),
                ('is_read', '=', False),
            ])
            
            return {
                'success': True,
                'notifications': [{
                    'id': n.id,
                    'title': n.title,
                    'message': n.message,
                    'type': n.notification_type,
                    'is_read': n.is_read,
                    'date': n.create_date.strftime('%d/%m/%Y %H:%M'),
                    'action_url': n.action_url or '#',
                } for n in notifications],
                'unread_count': unread_count,
            }
            
        except Exception as e:
            _logger.error(f"Error getting notifications: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/api/notifications/mark_read', type='json', auth='user', website=True)
    def mark_notification_read(self, notification_id):
        """
        Marcar notificación como leída.
        
        Args:
            notification_id: ID de la notificación
        
        Returns:
            dict: Resultado de la operación
        """
        try:
            notification = request.env['portal.notification'].browse(notification_id)
            
            if not notification.exists():
                return {
                    'success': False,
                    'error': _('Notificación no encontrada')
                }
            
            if notification.partner_id != request.env.user.partner_id:
                return {
                    'success': False,
                    'error': _('No autorizado')
                }
            
            notification.action_mark_read()
            
            return {'success': True}
            
        except Exception as e:
            _logger.error(f"Error marking notification as read: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========== PRODUCTOS ==========
    
    @http.route('/api/productos/<int:product_id>/info', type='json', auth='user', website=True)
    def get_product_info(self, product_id):
        """
        Obtener información completa de un producto.
        
        Args:
            product_id: ID del producto
        
        Returns:
            dict: Información del producto con disponibilidad
        """
        try:
            partner = request.env.user.partner_id
            
            if not hasattr(partner, 'is_distributor') or not partner.is_distributor:
                return {
                    'success': False,
                    'error': _('Usuario no autorizado')
                }
            
            product = request.env['product.template'].browse(product_id)
            
            if not product.exists():
                return {
                    'success': False,
                    'error': _('Producto no encontrado')
                }
            
            # Obtener precio según tarifa del distribuidor
            pricelist = partner.obtener_tarifa_aplicable() if hasattr(partner, 'obtener_tarifa_aplicable') else None
            
            if pricelist:
                price = pricelist._get_product_price(
                    product.product_variant_id,
                    1.0,
                    partner=partner
                )
            else:
                price = product.list_price
            
            return {
                'success': True,
                'data': {
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code or '',
                    'price': float(price),
                }
            }
            
        except Exception as e:
            _logger.error(f"Error getting product info: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    # ========== ESTADÍSTICAS ==========
    
    @http.route('/api/distributor/dashboard', type='json', auth='user', website=True)
    def get_dashboard_data(self, period='month'):
        """
        Obtener datos para el dashboard del distribuidor.
        
        Args:
            period: 'week', 'month', 'quarter', 'year'
        
        Returns:
            dict: Datos del dashboard
        """
        try:
            partner = request.env.user.partner_id
            
            if not hasattr(partner, 'is_distributor') or not partner.is_distributor:
                return {
                    'success': False,
                    'error': _('Usuario no autorizado')
                }
            
            # Calcular fechas según período
            from datetime import datetime, timedelta
            today = datetime.today().date()
            
            if period == 'week':
                start_date = today - timedelta(days=7)
            elif period == 'month':
                start_date = today - timedelta(days=30)
            elif period == 'quarter':
                start_date = today - timedelta(days=90)
            elif period == 'year':
                start_date = today - timedelta(days=365)
            else:
                start_date = today - timedelta(days=30)
            
            # Buscar o crear estadísticas
            stats_model = request.env['distributor.statistics']
            stats = stats_model.search([
                ('partner_id', '=', partner.id),
                ('period_start', '=', start_date),
                ('period_end', '=', today)
            ], limit=1)
            
            if not stats:
                stats = stats_model.create({
                    'partner_id': partner.id,
                    'period_start': start_date,
                    'period_end': today
                })
            
            dashboard_data = stats.get_statistics_for_portal()
            
            return {
                'success': True,
                'data': dashboard_data
            }
            
        except Exception as e:
            _logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
