# -*- coding: utf-8 -*-

import base64
import json
import logging
from werkzeug.exceptions import NotFound, Forbidden
from werkzeug.utils import redirect as werkzeug_redirect
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class PortalOrderController(http.Controller):
    """Controlador para gestión de documentos de pedidos desde el portal B2B."""

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
        
        return request.render('portal_b2b_base.portal_crear_pedido', values)

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
                'redirect': f'/my/orders/{order.id}'
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

    @http.route('/mis-pedidos/<int:order_id>/subir-documento', 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_upload_document(self, order_id, document_type, **post):
        """Sube un documento al pedido."""
        try:
            order = request.env['sale.order'].browse(order_id)
            
            if not order.exists():
                return werkzeug_redirect(f'/mis-pedidos', code=303)
            
            partner = request.env.user.partner_id
            if order.partner_id.commercial_partner_id != partner.commercial_partner_id:
                return werkzeug_redirect(f'/mis-pedidos', code=303)

            uploaded_file = request.httprequest.files.get('file')
            
            if not uploaded_file:
                return werkzeug_redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=no_file',
                    code=303
                )

            uploaded_file.seek(0, 2)
            file_size = uploaded_file.tell()
            uploaded_file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                return werkzeug_redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=file_too_large',
                    code=303
                )

            filename = uploaded_file.filename
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
                return werkzeug_redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=invalid_format',
                    code=303
                )

            file_content = uploaded_file.read()
            file_base64 = base64.b64encode(file_content)

            doc_type_names = {
                'delivery_note': 'Albarán Cliente Final',
                'invoice': 'Factura Cliente Final',
                'label': 'Etiqueta Envío',
                'transport': 'Factura Transporte',
                'other': 'Documento',
            }
            
            doc_name = f"{doc_type_names.get(document_type, 'Documento')} - {filename}"

            attachment = request.env['ir.attachment'].sudo().create({
                'name': doc_name,
                'datas': file_base64,
                'res_model': 'sale.order',
                'res_id': order_id,
                'type': 'binary',
                'description': f'Subido por {partner.name} desde portal',
            })

            field_mapping = {
                'delivery_note': 'distributor_delivery_note_ids',
                'invoice': 'distributor_invoice_ids',
                'label': 'distributor_label_ids',
                'transport': 'distributor_transport_invoice_ids',
                'other': 'distributor_other_docs_ids',
            }
            
            field_name = field_mapping.get(document_type, 'distributor_other_docs_ids')
            
            order.sudo().write({
                field_name: [(4, attachment.id)],
                'distributor_documents_reviewed': False,
            })

            order.message_post(
                body=f"📎 Documento subido desde portal: {doc_name}",
                subject="Nuevo Documento Distribuidor",
                message_type='notification',
            )

            _logger.info(
                f"Documento '{doc_name}' subido al pedido {order.name} "
                f"por {partner.name}"
            )

            return werkzeug_redirect(
                f'/mis-pedidos/{order_id}/documentos?uploaded=success',
                code=303
            )

        except Exception as e:
            _logger.error(f"Error al subir documento: {str(e)}", exc_info=True)
            return werkzeug_redirect(
                f'/mis-pedidos/{order_id}/documentos?error=upload_failed',
                code=303
            )

    @http.route('/mis-pedidos/<int:order_id>/eliminar-documento/<int:attachment_id>',
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_delete_document(self, order_id, attachment_id, **kw):
        """Elimina un documento del pedido."""
        try:
            order = request.env['sale.order'].browse(order_id)
            
            if not order.exists():
                return werkzeug_redirect('/mis-pedidos', code=303)
            
            partner = request.env.user.partner_id
            if order.partner_id.commercial_partner_id != partner.commercial_partner_id:
                return werkzeug_redirect('/mis-pedidos', code=303)

            attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
            
            if not attachment.exists():
                return werkzeug_redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=not_found',
                    code=303
                )

            if attachment.res_model != 'sale.order' or attachment.res_id != order_id:
                return werkzeug_redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=unauthorized',
                    code=303
                )

            doc_name = attachment.name
            attachment.unlink()

            order.message_post(
                body=f"🗑️ Documento eliminado desde portal: {doc_name}",
                subject="Documento Eliminado",
                message_type='notification',
            )

            _logger.info(
                f"Documento '{doc_name}' eliminado del pedido {order.name} "
                f"por {partner.name}"
            )

            return werkzeug_redirect(
                f'/mis-pedidos/{order_id}/documentos?deleted=success',
                code=303
            )

        except Exception as e:
            _logger.error(f"Error al eliminar documento: {str(e)}", exc_info=True)
            return werkzeug_redirect(
                f'/mis-pedidos/{order_id}/documentos?error=delete_failed',
                code=303
            )

    # ========== RUTAS DE DIRECCIONES DE ENTREGA ==========

    @http.route(['/mis-direcciones', '/mis-direcciones/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_mis_direcciones(self, page=1, search=None, **kw):
        """Lista de direcciones de entrega del distribuidor."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Domain base
        domain = [
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ]
        
        # Búsqueda
        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('city', 'ilike', search),
                ('street', 'ilike', search)
            ]
        
        # Contar direcciones
        DeliveryAddress = request.env['delivery.address']
        address_count = DeliveryAddress.search_count(domain)
        
        # Paginación
        from odoo.addons.portal.controllers.portal import pager as portal_pager
        pager = portal_pager(
            url='/mis-direcciones',
            url_args={'search': search},
            total=address_count,
            page=page,
            step=20,
        )
        
        # Obtener direcciones
        addresses = DeliveryAddress.search(
            domain,
            limit=20,
            offset=pager['offset'],
            order='is_default desc, name asc'
        )
        
        # Obtener países para el formulario
        countries = request.env['res.country'].search([])
        default_country = request.env.ref('base.es', raise_if_not_found=False)
        
        values = {
            'addresses': addresses,
            'page_name': 'mis_direcciones',
            'pager': pager,
            'search': search,
            'countries': countries,
            'default_country': default_country,
            'states': [],
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_mis_direcciones', values)

    @http.route(['/mis-direcciones/crear'], type='http', auth='user', website=True)
    def portal_crear_direccion(self, redirect=None, **kw):
        """Formulario para crear nueva dirección."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Obtener países
        countries = request.env['res.country'].search([])
        default_country = request.env.ref('base.es', raise_if_not_found=False)
        
        # Obtener provincias de España por defecto
        states = []
        if default_country:
            states = request.env['res.country.state'].search([
                ('country_id', '=', default_country.id)
            ], order='name')
        
        values = {
            'page_name': 'crear_direccion',
            'countries': countries,
            'default_country': default_country,
            'states': states,
            'redirect_url': redirect or '/mis-direcciones',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_direccion', values)

    @http.route(['/mis-direcciones/<int:address_id>/editar'], 
                type='http', auth='user', website=True)
    def portal_editar_direccion(self, address_id, **kw):
        """Formulario para editar dirección."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Obtener dirección
        address = request.env['delivery.address'].browse(address_id)
        
        if not address.exists() or address.partner_id != partner:
            return request.redirect('/mis-direcciones')
        
        # Obtener países
        countries = request.env['res.country'].search([])
        
        # Obtener provincias del país de la dirección
        states = []
        if address.country_id:
            states = request.env['res.country.state'].search([
                ('country_id', '=', address.country_id.id)
            ], order='name')
        
        values = {
            'address': address,
            'page_name': 'editar_direccion',
            'countries': countries,
            'states': states,
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_editar_direccion', values)

    @http.route(['/mis-direcciones/submit'], type='json', auth='user', 
                methods=['POST'], csrf=True)
    def portal_direccion_submit(self, **post):
        """Procesa creación/edición de dirección."""
        try:
            partner = request.env.user.partner_id
            
            if not partner.is_distributor:
                return {'error': _('No autorizado')}
            
            # Validar campos requeridos
            required_fields = ['name', 'street', 'city', 'zip', 'country_id']
            for field in required_fields:
                if not post.get(field):
                    return {'error': _('Faltan campos requeridos')}
            
            # Preparar valores
            vals = {
                'partner_id': partner.id,
                'name': post['name'],
                'street': post['street'],
                'street2': post.get('street2', ''),
                'city': post['city'],
                'zip': post['zip'],
                'country_id': int(post['country_id']),
                'state_id': int(post['state_id']) if post.get('state_id') else False,
                'contact_name': post.get('contact_name', ''),
                'contact_phone': post.get('contact_phone', ''),
                'require_appointment': post.get('require_appointment', False),
                'tail_lift_required': post.get('tail_lift_required', False),
                'delivery_notes': post.get('delivery_notes', ''),
            }
            
            # Crear o actualizar
            if post.get('address_id'):
                # Editar
                address = request.env['delivery.address'].browse(int(post['address_id']))
                if address.exists() and address.partner_id == partner:
                    address.sudo().write(vals)
                    message = _('Dirección actualizada correctamente')
                else:
                    return {'error': _('Dirección no encontrada')}
            else:
                # Crear
                address = request.env['delivery.address'].sudo().create(vals)
                message = _('Dirección creada correctamente')
            
            return {
                'success': True,
                'message': message,
                'redirect_url': '/mis-direcciones',
            }
            
        except Exception as e:
            _logger.error(f"Error al guardar dirección: {str(e)}", exc_info=True)
            return {'error': _('Error al guardar la dirección')}

    @http.route(['/mis-direcciones/<int:address_id>/eliminar'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_direccion_eliminar(self, address_id, **kw):
        """Desactiva una dirección."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        address = request.env['delivery.address'].browse(address_id)
        
        if not address.exists() or address.partner_id != partner:
            return request.redirect('/mis-direcciones')
        
        try:
            address.sudo().write({'active': False})
            return werkzeug_redirect('/mis-direcciones?deleted=success', code=303)
        except Exception as e:
            _logger.error(f"Error al eliminar dirección: {str(e)}")
            return werkzeug_redirect('/mis-direcciones?error=delete_failed', code=303)

    @http.route(['/mis-direcciones/<int:address_id>/por-defecto'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_direccion_por_defecto(self, address_id, **kw):
        """Marca una dirección como predeterminada."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        address = request.env['delivery.address'].browse(address_id)
        
        if not address.exists() or address.partner_id != partner:
            return request.redirect('/mis-direcciones')
        
        try:
            address.sudo().write({'is_default': True})
            return werkzeug_redirect('/mis-direcciones?default=success', code=303)
        except Exception as e:
            _logger.error(f"Error al marcar como predeterminada: {str(e)}")
            return werkzeug_redirect('/mis-direcciones?error=default_failed', code=303)

    # ========== RUTAS DE ETIQUETAS CLIENTE FINAL ==========

    @http.route(['/mis-etiquetas', '/mis-etiquetas/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_mis_etiquetas(self, page=1, search=None, **kw):
        """Lista de etiquetas de cliente final."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Domain base
        domain = [
            ('partner_id', '=', partner.id),
            ('active', '=', True)
        ]
        
        # Búsqueda
        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('customer_name', 'ilike', search),
                ('customer_reference', 'ilike', search)
            ]
        
        # Contar etiquetas
        DistributorLabel = request.env['distributor.label']
        label_count = DistributorLabel.search_count(domain)
        
        # Paginación
        from odoo.addons.portal.controllers.portal import pager as portal_pager
        pager = portal_pager(
            url='/mis-etiquetas',
            url_args={'search': search},
            total=label_count,
            page=page,
            step=20,
        )
        
        # Obtener etiquetas
        labels = DistributorLabel.search(
            domain,
            limit=20,
            offset=pager['offset'],
            order='name asc'
        )
        
        values = {
            'labels': labels,
            'label_count': label_count,
            'page_name': 'mis_etiquetas',
            'pager': pager,
            'search': search,
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_mis_etiquetas', values)

    @http.route(['/mis-etiquetas/crear'], type='http', auth='user', website=True)
    def portal_crear_etiqueta(self, redirect=None, **kw):
        """Formulario para crear nueva etiqueta."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        values = {
            'label': None,
            'page_name': 'crear_etiqueta',
            'redirect_url': redirect or '/mis-etiquetas',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_etiqueta', values)

    @http.route(['/mis-etiquetas/<int:label_id>/editar'], 
                type='http', auth='user', website=True)
    def portal_editar_etiqueta(self, label_id, **kw):
        """Formulario para editar etiqueta."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Obtener etiqueta
        label = request.env['distributor.label'].browse(label_id)
        
        if not label.exists() or label.partner_id != partner:
            return request.redirect('/mis-etiquetas')
        
        values = {
            'label': label,
            'page_name': 'editar_etiqueta',
        }
        
        return request.render('portal_b2b_delivery_addresses.portal_crear_etiqueta', values)

    @http.route(['/mis-etiquetas/submit'], type='json', auth='user', 
                methods=['POST'], csrf=True)
    def portal_etiqueta_submit(self, **post):
        """Procesa creación/edición de etiqueta."""
        try:
            partner = request.env.user.partner_id
            
            if not partner.is_distributor:
                return {'error': _('No autorizado')}
            
            # Validar campos requeridos
            if not post.get('name') or not post.get('customer_name'):
                return {'error': _('Faltan campos requeridos')}
            
            # Preparar valores
            vals = {
                'partner_id': partner.id,
                'name': post['name'],
                'customer_name': post['customer_name'],
                'customer_reference': post.get('customer_reference', ''),
                'tax_id': post.get('tax_id', ''),
                'contact_person': post.get('contact_person', ''),
                'customer_phone': post.get('customer_phone', ''),
                'customer_email': post.get('customer_email', ''),
                'customer_address': post.get('customer_address', ''),
                'payment_terms': post.get('payment_terms', ''),
                'delivery_instructions': post.get('delivery_instructions', ''),
                'print_on_delivery_note': post.get('print_on_delivery_note', False),
                'hide_company_info': post.get('hide_company_info', False),
                'notes': post.get('notes', ''),
            }
            
            # Crear o actualizar
            if post.get('label_id'):
                # Editar
                label = request.env['distributor.label'].browse(int(post['label_id']))
                if label.exists() and label.partner_id == partner:
                    label.sudo().write(vals)
                    message = _('Etiqueta actualizada correctamente')
                else:
                    return {'error': _('Etiqueta no encontrada')}
            else:
                # Crear
                label = request.env['distributor.label'].sudo().create(vals)
                message = _('Etiqueta creada correctamente')
            
            return {
                'success': True,
                'message': message,
                'redirect_url': '/mis-etiquetas',
            }
            
        except Exception as e:
            _logger.error(f"Error al guardar etiqueta: {str(e)}", exc_info=True)
            return {'error': _('Error al guardar la etiqueta')}

    @http.route(['/mis-etiquetas/<int:label_id>/eliminar'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_etiqueta_eliminar(self, label_id, **kw):
        """Desactiva una etiqueta."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        label = request.env['distributor.label'].browse(label_id)
        
        if not label.exists() or label.partner_id != partner:
            return request.redirect('/mis-etiquetas')
        
        try:
            label.sudo().write({'active': False})
            return werkzeug_redirect('/mis-etiquetas?deleted=success', code=303)
        except Exception as e:
            _logger.error(f"Error al eliminar etiqueta: {str(e)}")
            return werkzeug_redirect('/mis-etiquetas?error=delete_failed', code=303)
