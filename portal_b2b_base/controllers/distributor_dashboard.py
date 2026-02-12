# -*- coding: utf-8 -*-

import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class DistributorDashboard(http.Controller):
    """Controlador unificado para el dashboard del distribuidor."""
    
    @http.route(['/api/distributor/credit_status'], type='json', auth='user', methods=['POST'])
    def get_credit_status(self, **kw):
        """
        API para obtener el estado de crédito del distribuidor.
        
        Usado por el widget flotante de crédito.
        
        Returns:
            dict: Estado de crédito formateado para el widget
        """
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            credit_data = partner.obtener_estado_credito_widget()
            
            return {
                'success': True,
                'data': credit_data
            }
            
        except Exception as e:
            _logger.error(f"Error obteniendo estado de crédito: {str(e)}")
            return {'error': str(e)}

    @http.route(['/api/productos/<int:product_id>/stock'], type='json', auth='user', methods=['POST'])
    def get_product_stock(self, product_id, **kw):
        """
        API para obtener información de stock de un producto.
        
        Args:
            product_id: ID del producto
            
        Returns:
            dict: Información de stock del producto
        """
        try:
            product = request.env['product.template'].browse(product_id)
            
            if not product.exists():
                return {'error': _('Producto no encontrado')}
            
            # Verificar acceso
            partner = request.env.user.partner_id
            if not partner.is_distributor:
                return {'error': _('No autorizado')}
            
            stock_info = product.get_stock_info_for_portal()
            
            return {
                'success': True,
                'data': stock_info
            }
            
        except Exception as e:
            _logger.error(f"Error obteniendo stock del producto {product_id}: {str(e)}")
            return {'error': str(e)}

    @http.route(['/api/productos/buscar'], type='json', auth='user', methods=['POST'])
    def search_products(self, query='', limit=10, **kw):
        """
        API para búsqueda de productos con información de stock.
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
            
        Returns:
            dict: Lista de productos con stock
        """
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            # Buscar productos
            domain = [
                '|', '|',
                ('name', 'ilike', query),
                ('default_code', 'ilike', query),
                ('barcode', 'ilike', query),
                ('sale_ok', '=', True),
            ]
            
            products = request.env['product.template'].search(domain, limit=limit)
            
            # Obtener tarifa del distribuidor
            pricelist = partner.obtener_tarifa_aplicable()
            
            products_data = []
            for product in products:
                # Calcular precio según tarifa
                price = pricelist._get_product_price(
                    product.product_variant_id,
                    1.0,
                    partner=partner
                ) if pricelist else product.list_price
                
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code or '',
                    'list_price': float(price),
                    'qty_available': float(product.available_qty_for_portal),
                    'stock_status': product.stock_status,
                    'stock_status_label': dict(product._fields['stock_status'].selection).get(product.stock_status),
                    'estimated_restock_date': product.estimated_restock_date.strftime('%d/%m/%Y') if product.estimated_restock_date else None,
                    'is_make_to_order': product._is_make_to_order(),
                })
            
            return {
                'success': True,
                'products': products_data
            }
            
        except Exception as e:
            _logger.error(f"Error buscando productos: {str(e)}")
            return {'error': str(e)}

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
