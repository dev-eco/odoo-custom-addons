# -*- coding: utf-8 -*-

import base64
import json
import logging
from werkzeug.exceptions import NotFound, Forbidden
from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class PortalOrderController(http.Controller):
    """Controlador para gestión de pedidos desde el portal B2B."""

    @http.route('/crear-pedido', type='http', auth='user', website=True)
    def portal_create_order(self, **kwargs):
        """Formulario de creación de pedido."""
        user = request.env.user
        partner = user.partner_id
        
        # Verificar que es distribuidor B2B
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Obtener datos necesarios
        addresses = request.env['delivery.address'].search([
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ])
        
        labels = request.env['distributor.label'].search([
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ])
        
        # Obtener productos disponibles (según configuración)
        products = request.env['product.product'].search([
            ('sale_ok', '=', True),
            ('active', '=', True)
        ])
        
        # Pre-seleccionar etiqueta si viene en parámetros
        selected_label_id = kwargs.get('label_id')
        selected_label = None
        if selected_label_id:
            selected_label = request.env['distributor.label'].browse(int(selected_label_id))
            if selected_label.partner_id != partner:
                selected_label = None
        
        values = {
            'partner': partner,
            'addresses': addresses,
            'labels': labels,
            'products': products,
            'selected_label': selected_label,
            'page_name': 'create_order',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_pedido', values)

    @http.route('/crear-pedido/submit', type='json', auth='user', methods=['POST'], csrf=True)
    def portal_submit_order(self, **post):
        """Procesa la creación del pedido desde el portal."""
        try:
            user = request.env.user
            partner = user.partner_id
            
            if not partner.is_distributor:
                return {'error': _('Acceso denegado')}
            
            # Validar datos requeridos
            if not post.get('order_lines'):
                return {'error': _('Debe añadir al menos un producto')}
            
            # Preparar valores del pedido
            order_vals = {
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                'date_order': fields.Datetime.now(),
                'origin': 'Portal B2B',
            }
            
            # Dirección de entrega
            if post.get('delivery_address_id'):
                order_vals['delivery_address_id'] = int(post['delivery_address_id'])
            
            # Etiqueta cliente final
            if post.get('distributor_label_id'):
                order_vals['distributor_label_id'] = int(post['distributor_label_id'])
            
            # Referencia cliente
            if post.get('customer_delivery_reference'):
                order_vals['customer_delivery_reference'] = post['customer_delivery_reference']
            
            # Notas del distribuidor
            if post.get('distributor_notes'):
                order_vals['distributor_notes'] = post['distributor_notes']
            
            # Crear pedido
            order = request.env['sale.order'].sudo().create(order_vals)
            
            # Añadir líneas de pedido
            for line_data in post['order_lines']:
                line_vals = {
                    'order_id': order.id,
                    'product_id': int(line_data['product_id']),
                    'product_uom_qty': float(line_data['quantity']),
                    'price_unit': float(line_data.get('price_unit', 0)),
                }
                request.env['sale.order.line'].sudo().create(line_vals)
            
            # Procesar archivos adjuntos
            attachments_created = []
            
            # Albaranes cliente final
            if post.get('customer_delivery_notes'):
                for file_data in post['customer_delivery_notes']:
                    attachment = self._create_attachment(
                        file_data,
                        order,
                        'Albarán Cliente Final'
                    )
                    if attachment:
                        attachments_created.append(attachment.id)
                        order.sudo().write({
                            'customer_delivery_note_ids': [(4, attachment.id)]
                        })
            
            # Etiquetas personalizadas
            if post.get('customer_labels'):
                for file_data in post['customer_labels']:
                    attachment = self._create_attachment(
                        file_data,
                        order,
                        'Etiqueta Personalizada'
                    )
                    if attachment:
                        attachments_created.append(attachment.id)
                        order.sudo().write({
                            'customer_label_ids': [(4, attachment.id)]
                        })
            
            _logger.info(f"Pedido {order.name} creado desde portal por {partner.name}")
            
            return {
                'success': True,
                'order_id': order.id,
                'order_name': order.name,
                'message': _('Pedido creado correctamente: %s') % order.name,
                'redirect': f'/mis-pedidos/{order.id}'
            }
            
        except Exception as e:
            _logger.error(f"Error creando pedido desde portal: {str(e)}", exc_info=True)
            return {'error': _('Error al crear el pedido: %s') % str(e)}

    def _create_attachment(self, file_data, order, description):
        """Crea un adjunto desde datos del formulario."""
        try:
            if not file_data.get('content') or not file_data.get('filename'):
                return None
            
            # Decodificar contenido base64
            file_content = base64.b64decode(file_data['content'])
            
            # Validar tamaño (máximo 10MB)
            if len(file_content) > 10 * 1024 * 1024:
                _logger.warning(f"Archivo {file_data['filename']} excede 10MB")
                return None
            
            attachment_vals = {
                'name': file_data['filename'],
                'datas': file_data['content'],
                'res_model': 'sale.order',
                'res_id': order.id,
                'description': description,
                'type': 'binary',
            }
            
            attachment = request.env['ir.attachment'].sudo().create(attachment_vals)
            _logger.info(f"Adjunto creado: {attachment.name} para pedido {order.name}")
            
            return attachment
            
        except Exception as e:
            _logger.error(f"Error creando adjunto: {str(e)}")
            return None
