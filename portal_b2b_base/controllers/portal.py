# -*- coding: utf-8 -*-

import logging
import json
import base64
from werkzeug.exceptions import NotFound, Forbidden
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
from odoo.tools import groupby as groupbyelem
from operator import itemgetter

_logger = logging.getLogger(__name__)


class PortalB2B(CustomerPortal):
    """
    Controlador principal del portal B2B para distribuidores.
    
    Hereda de CustomerPortal (portal base de Odoo) y añade:
    - Rutas en español (/mi-portal, /mis-pedidos, etc.)
    - Redirecciones automáticas de /my a /mi-portal para distribuidores
    - Funcionalidades específicas B2B
    """

    # ========== MÉTODO HELPER PARA VALORES SEGUROS ==========
    
    def _prepare_portal_layout_values(self):
        """Preparar valores seguros para el layout del portal."""
        values = {
            'website': False,
            'preview_object': False,
            'editable': False,
            'translatable': False,
        }
        
        return values

    # ========== REDIRECCIONES AUTOMÁTICAS (PRIORIDAD ALTA) ==========

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True, priority=5)
    def portal_my_home(self, **kw):
        """
        Intercepta /my y redirige a /mi-portal para distribuidores B2B.
        Para usuarios normales, usa el comportamiento estándar.
        
        PRIORIDAD 5: Se ejecuta ANTES que las rutas estándar (priority=10 por defecto)
        """
        partner = request.env.user.partner_id
        
        if partner.is_distributor:
            _logger.info(f"Distribuidor {partner.name} redirigido de /my a /mi-portal")
            return request.redirect('/mi-portal')
        
        # Para usuarios normales, comportamiento estándar
        return super().portal_my_home(**kw)

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], 
                type='http', auth='user', website=True, priority=5)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """
        Intercepta /my/orders y redirige a /mis-pedidos para distribuidores.
        """
        partner = request.env.user.partner_id
        
        if partner.is_distributor:
            # Construir URL con parámetros
            redirect_url = f'/mis-pedidos/page/{page}' if page > 1 else '/mis-pedidos'
            
            # Añadir parámetros de query string si existen
            params = []
            if date_begin:
                params.append(f'date_begin={date_begin}')
            if date_end:
                params.append(f'date_end={date_end}')
            if sortby:
                params.append(f'sortby={sortby}')
            
            if params:
                redirect_url += '?' + '&'.join(params)
            
            return request.redirect(redirect_url)
        
        # Para usuarios normales, comportamiento estándar
        return super().portal_my_orders(page=page, date_begin=date_begin, 
                                       date_end=date_end, sortby=sortby, **kw)

    @http.route(['/my/orders/<int:order_id>'], type='http', auth='public', 
                website=True, priority=5)
    def portal_order_page(self, order_id, report_type=None, access_token=None, 
                         message=False, download=False, **kw):
        """
        Intercepta /my/orders/<id> para:
        - Permitir descargas PDF (report_type='pdf') con o sin token
        - Redirigir a /mis-pedidos/<id> para distribuidores (navegación normal)
        """
        # Si es una descarga de PDF, manejar directamente
        if report_type in ('html', 'pdf', 'text'):
            _logger.debug(f"Descarga de pedido {order_id} en formato {report_type}")
            
            try:
                # Intentar obtener el pedido con acceso público si hay token
                if access_token:
                    order_sudo = request.env['sale.order'].sudo().search([
                        ('id', '=', order_id),
                        ('access_token', '=', access_token)
                    ], limit=1)
                else:
                    # Sin token, verificar que el usuario tenga acceso
                    order_sudo = request.env['sale.order'].sudo().browse(order_id)
                    
                    # Verificar que el usuario autenticado sea el propietario
                    if not request.env.user._is_public():
                        partner = request.env.user.partner_id
                        if order_sudo.partner_id.commercial_partner_id != partner.commercial_partner_id:
                            _logger.warning(f"Usuario {request.env.user.login} intentó acceder a pedido {order_id} sin permiso")
                            return request.redirect('/mis-pedidos')
                    else:
                        # Usuario público sin token
                        _logger.warning(f"Intento de acceso público a pedido {order_id} sin token")
                        return request.redirect('/web/login')
                
                if not order_sudo.exists():
                    _logger.error(f"Pedido {order_id} no encontrado")
                    return request.redirect('/mis-pedidos')
                
                # Generar PDF
                if report_type == 'pdf':
                    pdf_content, content_type = request.env.ref('sale.action_report_saleorder').sudo()._render_qweb_pdf([order_id])
                    
                    pdfhttpheaders = [
                        ('Content-Type', 'application/pdf'),
                        ('Content-Length', len(pdf_content)),
                        ('Content-Disposition', f'attachment; filename="{order_sudo.name}.pdf"')
                    ]
                    
                    return request.make_response(pdf_content, headers=pdfhttpheaders)
                
                # Para HTML o text, usar método estándar
                return super().portal_order_page(
                    order_id=order_id,
                    report_type=report_type,
                    access_token=access_token,
                    message=message,
                    download=download,
                    **kw
                )
                
            except Exception as e:
                _logger.error(f"Error en descarga de pedido {order_id}: {str(e)}", exc_info=True)
                return request.redirect('/mis-pedidos')
        
        # Si es acceso público con token, usar ruta estándar
        if access_token:
            try:
                return super().portal_order_page(
                    order_id=order_id,
                    access_token=access_token,
                    message=message,
                    **kw
                )
            except Exception as e:
                _logger.error(f"Error con access_token: {str(e)}")
                return request.redirect('/mis-pedidos')
        
        # Para distribuidores autenticados, redirigir a ruta en español
        if request.env.user and not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.is_distributor:
                return request.redirect(f'/mis-pedidos/{order_id}')
        
        # Para usuarios normales, comportamiento estándar
        return super().portal_order_page(order_id=order_id, **kw)

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], 
                type='http', auth='user', website=True, priority=5)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """
        Intercepta /my/invoices y redirige a /mis-facturas para distribuidores.
        """
        partner = request.env.user.partner_id
        
        if partner.is_distributor:
            redirect_url = f'/mis-facturas/page/{page}' if page > 1 else '/mis-facturas'
            
            params = []
            if date_begin:
                params.append(f'date_begin={date_begin}')
            if date_end:
                params.append(f'date_end={date_end}')
            if sortby:
                params.append(f'sortby={sortby}')
            
            if params:
                redirect_url += '?' + '&'.join(params)
            
            return request.redirect(redirect_url)
        
        return super().portal_my_invoices(page=page, date_begin=date_begin, 
                                         date_end=date_end, sortby=sortby, **kw)

    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth='public', 
                website=True, priority=5)
    def portal_my_invoice_detail(self, invoice_id, report_type=None, access_token=None,
                                message=False, download=False, **kw):
        """
        Intercepta /my/invoices/<id> para:
        - BLOQUEAR descargas PDF para distribuidores (se envían por correo desde backend)
        - Permitir descargas solo con access_token (usuarios externos/correos)
        - Redirigir a /mis-facturas para distribuidores
        """
        # Verificar si es distribuidor autenticado
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.is_distributor:
                # DISTRIBUIDORES: NO pueden descargar, solo ver
                if report_type in ('html', 'pdf', 'text'):
                    _logger.warning(
                        f"Distribuidor {partner.name} intentó descargar factura {invoice_id}. "
                        f"Descarga bloqueada - las facturas se envían por correo."
                    )
                    return request.redirect(f'/mis-facturas/{invoice_id}?error=download_blocked')
                
                # Redirigir a vista de detalle en español
                return request.redirect(f'/mis-facturas/{invoice_id}')
        
        # Para usuarios NO distribuidores o con access_token, permitir descarga
        if report_type in ('html', 'pdf', 'text'):
            _logger.debug(f"Descarga de factura {invoice_id} en formato {report_type}")
            
            try:
                # Intentar obtener la factura
                if access_token:
                    invoice_sudo = request.env['account.move'].sudo().search([
                        ('id', '=', invoice_id),
                        ('access_token', '=', access_token)
                    ], limit=1)
                else:
                    # Sin token, verificar que el usuario tenga acceso
                    invoice_sudo = request.env['account.move'].sudo().browse(invoice_id)
                    
                    # Verificar que el usuario autenticado sea el propietario
                    if not request.env.user._is_public():
                        partner = request.env.user.partner_id
                        if invoice_sudo.partner_id.commercial_partner_id != partner.commercial_partner_id:
                            _logger.warning(f"Usuario {request.env.user.login} intentó acceder a factura {invoice_id} sin permiso")
                            return request.redirect('/mis-facturas')
                    else:
                        # Usuario público sin token
                        _logger.warning(f"Intento de acceso público a factura {invoice_id} sin token")
                        return request.redirect('/web/login')
                
                if not invoice_sudo.exists():
                    _logger.error(f"Factura {invoice_id} no encontrada")
                    return request.redirect('/mis-facturas')
                
                # Asegurar que la factura tenga token (generar si no existe)
                if not invoice_sudo.access_token:
                    invoice_sudo.access_token = invoice_sudo._generate_access_token()
                    _logger.info(f"Token generado para factura {invoice_sudo.name}")
                
                # Generar PDF
                if report_type == 'pdf':
                    pdf_content, content_type = request.env.ref('account.account_invoices').sudo()._render_qweb_pdf([invoice_id])
                    
                    pdfhttpheaders = [
                        ('Content-Type', 'application/pdf'),
                        ('Content-Length', len(pdf_content)),
                        ('Content-Disposition', f'attachment; filename="{invoice_sudo.name}.pdf"')
                    ]
                    
                    return request.make_response(pdf_content, headers=pdfhttpheaders)
                
                # Para HTML o text, usar método estándar
                return super().portal_my_invoice_detail(
                    invoice_id=invoice_id,
                    report_type=report_type,
                    access_token=access_token,
                    message=message,
                    download=download,
                    **kw
                )
                
            except Exception as e:
                _logger.error(f"Error en descarga de factura {invoice_id}: {str(e)}", exc_info=True)
                return request.redirect('/mis-facturas')
        
        # Si hay token pero no es descarga, usar ruta estándar
        if access_token:
            try:
                return super().portal_my_invoice_detail(
                    invoice_id=invoice_id,
                    access_token=access_token,
                    message=message,
                    **kw
                )
            except Exception as e:
                _logger.error(f"Error con access_token en factura: {str(e)}")
                return request.redirect('/mis-facturas')
        
        # Para distribuidores autenticados sin descarga, redirigir a ruta en español
        if request.env.user and not request.env.user._is_public():
            partner = request.env.user.partner_id
            if partner.is_distributor:
                return request.redirect(f'/mis-facturas/{invoice_id}')
        
        # Para usuarios normales, comportamiento estándar
        return super().portal_my_invoice_detail(invoice_id=invoice_id, **kw)

    # ========== PREPARACIÓN DE VALORES ==========

    def _prepare_home_portal_values(self, counters):
        """Añade contadores B2B al portal home."""
        values = super()._prepare_home_portal_values(counters)

        partner = request.env.user.partner_id

        # SIEMPRE definir estas variables para evitar errores en templates
        values.update({
            'is_distributor': False,
            'credit_limit': 0.0,
            'available_credit': 0.0,
            'total_invoiced_year': 0.0,
            'has_delivery_module': False,
            'recent_orders': [],
        })

        # Solo actualizar si es distribuidor
        if partner.is_distributor:
            if 'order_count' in counters:
                values['order_count'] = request.env['sale.order'].search_count(
                    self._get_orders_domain()
                )

            if 'invoice_count' in counters:
                values['invoice_count'] = request.env['account.move'].search_count(
                    self._get_invoices_domain()
                )

            values.update({
                'is_distributor': True,
                'credit_limit': float(partner.credit_limit or 0.0),
                'available_credit': float(partner.available_credit or 0.0),
                'total_invoiced_year': float(partner.total_invoiced_year or 0.0),
            })
            
            # Obtener últimos 5 pedidos
            recent_orders = request.env['sale.order'].search([
                ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
                ('state', '!=', 'cancel'),
            ], order='date_order desc', limit=5)
            values['recent_orders'] = recent_orders

        # Verificar si módulo de direcciones está instalado
        try:
            request.env['delivery.address']
            values['has_delivery_module'] = True
        except Exception:
            values['has_delivery_module'] = False

        return values

    def _get_orders_domain(self):
        """
        Domain para pedidos del distribuidor actual.

        Mejoras:
        - Busca por partner comercial Y todos sus hijos
        - Incluye pedidos donde el partner_id sea cualquier contacto relacionado
        """
        partner = request.env.user.partner_id
        commercial_partner = partner.commercial_partner_id

        # Obtener todos los partners relacionados (padre comercial + hijos)
        related_partners = request.env['res.partner'].search([
            '|',
            ('id', '=', commercial_partner.id),
            ('commercial_partner_id', '=', commercial_partner.id)
        ])

        _logger.debug(f"Portal orders filter - User: {request.env.user.name}, "
                     f"Partner: {partner.name}, Commercial: {commercial_partner.name}, "
                     f"Related partners: {len(related_partners)}")

        return [
            ('partner_id', 'in', related_partners.ids),
            ('state', '!=', 'cancel'),
        ]

    def _get_invoices_domain(self, invoice_type=None):
        """
        Domain para facturas del distribuidor actual.

        Mejoras:
        - Busca por partner comercial Y todos sus hijos
        - Incluye facturas donde el partner_id sea cualquier contacto relacionado
        """
        partner = request.env.user.partner_id
        commercial_partner = partner.commercial_partner_id

        # Obtener todos los partners relacionados
        related_partners = request.env['res.partner'].search([
            '|',
            ('id', '=', commercial_partner.id),
            ('commercial_partner_id', '=', commercial_partner.id)
        ])

        domain = [
            ('move_type', '=', invoice_type or 'out_invoice'),
            ('partner_id', 'in', related_partners.ids),
        ]

        _logger.debug(f"Portal invoices filter - Related partners: {len(related_partners)}")

        return domain

    # ========== RUTAS EN ESPAÑOL ==========

    @http.route(['/mi-portal'], type='http', auth='user', website=True)
    def mi_portal_home(self, **kw):
        """Dashboard principal del portal B2B."""
        values = self._prepare_portal_layout_values()
        
        # Añadir contadores y datos del portal
        counters = self._prepare_home_portal_values(['order_count', 'invoice_count'])
        values.update(counters)
        
        return request.render('portal_b2b_base.portal_b2b_dashboard_home', values)

    @http.route(['/mis-pedidos', '/mis-pedidos/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_mis_pedidos(self, page=1, date_begin=None, date_end=None, 
                          sortby=None, search=None, search_in='name', **kw):
        """Lista paginada de pedidos del distribuidor."""
        partner = request.env.user.partner_id

        if not partner.is_distributor: 
            return request.redirect('/mi-portal')

        SaleOrder = request.env['sale.order']

        searchbar_sortings = {
            'date': {'label': 'Fecha Pedido', 'order': 'date_order desc'},
            'name': {'label': 'Referencia', 'order': 'name desc'},
            'state': {'label': 'Estado', 'order': 'state'},
            'amount': {'label': 'Total', 'order': 'amount_total desc'},
        }

        searchbar_inputs = {
            'name': {'input': 'name', 'label': 'Buscar en Referencia'},
            'client_order_ref': {'input': 'client_order_ref', 'label': 'Buscar en Su Referencia'},
            'all': {'input': 'all', 'label': 'Buscar en Todo'},
        }

        searchbar_filters = {
            'all': {'label': 'Todos', 'domain': []},
            'draft': {'label': 'Presupuestos', 'domain': [('state', 'in', ['draft', 'sent'])]},
            'confirmed': {'label': 'Confirmados', 'domain': [('state', 'in', ['sale', 'done'])]},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if not search_in:
            search_in = 'name'

        domain = self._get_orders_domain()

        if date_begin and date_end:
            domain += [('date_order', '>=', date_begin), ('date_order', '<=', date_end)]

        if search and search_in:
            if search_in == 'all':
                domain += ['|', '|', 
                          ('name', 'ilike', search),
                          ('client_order_ref', 'ilike', search),
                          ('partner_id.name', 'ilike', search)]
            elif search_in == 'client_order_ref':
                domain += [('client_order_ref', 'ilike', search)]
            else:
                domain += [(searchbar_inputs[search_in]['input'], 'ilike', search)]

        order_count = SaleOrder.search_count(domain)

        pager = portal_pager(
            url='/mis-pedidos',
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 
                     'search_in': search_in, 'search': search},
            total=order_count,
            page=page,
            step=20,
        )

        orders = SaleOrder.search(domain, order=order, limit=20, offset=pager['offset'])
        
        # ASEGURAR VALORES POR DEFECTO PARA TODOS LOS CAMPOS
        for order_item in orders:
            try:
                # Asegurar que los campos tengan valores válidos
                if not hasattr(order_item, 'order_status') or not order_item.order_status:
                    order_item.order_status = 'new'
                if not hasattr(order_item, 'picking_status') or not order_item.picking_status:
                    order_item.picking_status = 'not_created'
                if not hasattr(order_item, 'distributor_document_count'):
                    order_item.distributor_document_count = 0
                if not hasattr(order_item, 'has_new_distributor_documents'):
                    order_item.has_new_distributor_documents = False
                    
                # Trigger computed fields de forma segura
                try:
                    _ = order_item.order_status
                    _ = order_item.picking_status
                    _ = order_item.distributor_document_count
                    _ = order_item.has_new_distributor_documents
                except Exception as compute_error:
                    _logger.warning(f"Error calculando campos computed para pedido {order_item.id}: {str(compute_error)}")
                    
            except Exception as e:
                _logger.warning(f"Error procesando pedido {order_item.id}: {str(e)}")
                # Asignar valores por defecto si hay error
                order_item.order_status = 'new'
                order_item.picking_status = 'not_created'
        
        # Calcular total general
        all_orders = SaleOrder.search(domain)
        grand_total = sum(float(o.amount_total) for o in all_orders)

        values = {
            'orders': orders,
            'order_count': order_count,
            'grand_total': grand_total,
            'page_name': 'mis_pedidos',
            'pager': pager,
            'default_url': '/mis-pedidos',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
            'date_begin': date_begin,
            'date_end': date_end,
        }

        return request.render('portal_b2b_base.portal_mis_pedidos', values)

    @http.route(['/mis-pedidos/<int:order_id>'], type='http', auth='user', website=True)
    def portal_pedido_detalle(self, order_id, access_token=None, **kw):
        """Detalle de un pedido específico."""
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/mis-pedidos')

        partner = request.env.user.partner_id
        if order_sudo.partner_id.commercial_partner_id != partner.commercial_partner_id:
            _logger.warning(
                f"Intento de acceso no autorizado al pedido {order_id} "
                f"por usuario {request.env.user.login}"
            )
            return request.redirect('/mis-pedidos')

        productos_sin_stock = order_sudo.obtener_productos_sin_stock()

        values = {
            'order': order_sudo,
            'page_name': 'pedido_detalle',
            'productos_sin_stock': productos_sin_stock,
            'can_cancel': order_sudo.can_be_cancelled,
        }

        return request.render('portal_b2b_base.portal_pedido_detalle', values)

    @http.route(['/mis-pedidos/<int:order_id>/cancelar'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_pedido_cancelar(self, order_id, **kw):
        """Cancela un pedido desde el portal."""
        try:
            order_sudo = self._document_check_access('sale.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/mis-pedidos')

        partner = request.env.user.partner_id
        if order_sudo.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return request.redirect('/mis-pedidos')

        try:
            order_sudo.action_cancel_from_portal()
            return request.redirect(f'/mis-pedidos/{order_id}?message=cancelled')
        except Exception as e:
            _logger.error(f"Error al cancelar pedido {order_id}: {str(e)}")
            return request.redirect(f'/mis-pedidos/{order_id}?error=cancel_failed')

    @http.route(['/mis-pedidos/<int:order_id>/repetir'], 
                type='http', auth='user', website=True)
    def portal_pedido_repetir(self, order_id, **kw):
        """Duplica un pedido existente como borrador."""
        try:
            order_sudo = self._document_check_access('sale.order', order_id)
        except (AccessError, MissingError):
            return request.redirect('/mis-pedidos')

        partner = request.env.user.partner_id
        if order_sudo.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return request.redirect('/mis-pedidos')

        try:
            new_order_id = order_sudo.action_duplicate_order()
            return request.redirect(f'/mis-pedidos/{new_order_id}?message=duplicated')
        except Exception as e:
            _logger.error(f"Error al duplicar pedido {order_id}: {str(e)}")
            return request.redirect(f'/mis-pedidos/{order_id}?error=duplicate_failed')

    @http.route(['/crear-pedido'], type='http', auth='user', website=True)
    def portal_crear_pedido(self, redirect=None, **kw):
        """Formulario para crear un nuevo pedido."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect('/mi-portal')

        pricelist = partner.obtener_tarifa_aplicable()
        
        delivery_addresses = []
        default_address = None
        has_delivery_module = False
        
        try:
            DeliveryAddress = request.env['delivery.address']
            delivery_addresses = DeliveryAddress.search([
                ('partner_id', '=', partner.id),
                ('active', '=', True)
            ], order='is_default desc, name asc')
            
            default_address = delivery_addresses.filtered(lambda a: a.is_default)[:1]
            has_delivery_module = True
            
        except Exception as e:
            _logger.debug(f"Módulo delivery_addresses no disponible: {str(e)}")

        distributor_labels = []
        try:
            DistributorLabel = request.env['distributor.label']
            distributor_labels = DistributorLabel.search([
                ('partner_id', '=', partner.id),
                ('active', '=', True)
            ], order='name asc')
        except Exception as e:
            _logger.debug(f"Módulo distributor_label no disponible: {str(e)}")

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'crear_pedido',
            'partner': partner,
            'pricelist': pricelist,
            'credit_limit': float(partner.credit_limit or 0.0),
            'available_credit': float(partner.available_credit or 0.0),
            'currency_id': partner.currency_id,
            'delivery_addresses': delivery_addresses,
            'default_address': default_address,
            'has_delivery_module': has_delivery_module,
            'distributor_labels': distributor_labels,
            'redirect_url': redirect or '/mis-pedidos',
        })

        return request.render('portal_b2b_base.portal_crear_pedido', values)

    @http.route(['/crear-pedido/submit'], type='json', auth='user', 
                methods=['POST'], csrf=True)
    def portal_crear_pedido_submit(self, **kw):
        """Procesa la creación de un nuevo pedido vía AJAX."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {'error': _('Usuario no autorizado')}

        try:
            lines_data = kw.get('lines', [])
            notes = kw.get('notes', '')
            delivery_address_id = kw.get('delivery_address_id')
            distributor_label_id = kw.get('distributor_label_id')
            customer_delivery_ref = kw.get('customer_delivery_reference')
            delivery_schedule = kw.get('delivery_schedule', '')
            client_order_ref = kw.get('client_order_ref', '')

            # Validar que hay líneas
            if not lines_data:
                return {'error': _('Debe agregar al menos un producto')}

            # Validar que las líneas tienen datos válidos
            valid_lines = []
            for line_data in lines_data:
                try:
                    product_id = line_data.get('product_id')
                    qty = float(line_data.get('qty', 0))
                    
                    if product_id and qty > 0: 
                        valid_lines.append({
                            'product_id': int(product_id),
                            'qty': qty
                        })
                except (ValueError, TypeError) as e:
                    _logger.warning(f"Error procesando línea: {str(e)}")
                    continue
            
            if not valid_lines:
                return {'error': _('Debe agregar al menos un producto con cantidad válida')}

            # Preparar valores del pedido
            order_vals = {
                'partner_id': partner.id,
                'pricelist_id': partner.obtener_tarifa_aplicable().id,
                'delivery_schedule': delivery_schedule,
                'client_order_ref': client_order_ref,
            }
            
            # Gestión de dirección de entrega
            delivery_option = kw.get('delivery_option', 'default')
            delivery_address_id = None

            if delivery_option == 'saved':
                # Usar dirección guardada
                delivery_address_id = kw.get('delivery_address_id')
                if delivery_address_id:
                    try:
                        delivery_address = request.env['delivery.address'].browse(int(delivery_address_id))
                        if delivery_address.exists() and delivery_address.partner_id == partner:
                            order_vals['delivery_address_id'] = delivery_address.id
                    except Exception as e:
                        _logger.warning(f"Error al asignar dirección guardada: {str(e)}")

            elif delivery_option == 'new':
                # Crear nueva dirección
                try:
                    new_address_vals = {
                        'partner_id': partner.id,
                        'name': kw.get('new_address_name', ''),
                        'street': kw.get('new_address_street', ''),
                        'street2': kw.get('new_address_street2', ''),
                        'zip': kw.get('new_address_zip', ''),
                        'city': kw.get('new_address_city', ''),
                        'contact_name': kw.get('new_address_contact_name', ''),
                        'contact_phone': kw.get('new_address_contact_phone', ''),
                        'delivery_notes': kw.get('new_address_notes', ''),
                        'require_appointment': kw.get('new_address_appointment') == 'on',
                        'tail_lift_required': kw.get('new_address_tail_lift') == 'on',
                        'active': True,
                    }
                    
                    # Validar campos obligatorios
                    if not all([new_address_vals['name'], new_address_vals['street'], 
                               new_address_vals['zip'], new_address_vals['city']]):
                        return {'error': _('Complete todos los campos obligatorios de la dirección')}
                    
                    # Crear dirección
                    new_address = request.env['delivery.address'].sudo().create(new_address_vals)
                    order_vals['delivery_address_id'] = new_address.id
                    
                    # Si el usuario NO marcó "guardar para futuros pedidos", marcarla como no predeterminada
                    if not kw.get('save_address_for_future'):
                        new_address.write({'is_default': False})
                    
                    _logger.info(f"Nueva dirección '{new_address.name}' creada para {partner.name}")
                    
                except Exception as e:
                    _logger.error(f"Error creando nueva dirección: {str(e)}")
                    return {'error': _('Error al crear la dirección de entrega')}

            # Etiqueta distribuidor (opcional)
            if distributor_label_id:
                try:
                    order_vals['distributor_label_id'] = int(distributor_label_id)
                    order_vals['customer_delivery_reference'] = customer_delivery_ref or ''
                except Exception as e:
                    _logger.warning(f"Error al asignar etiqueta: {str(e)}")

            # Crear pedido
            order = request.env['sale.order'].sudo().create(order_vals)
            
            # Forzar sincronización si hay dirección de entrega
            if order.delivery_address_id:
                order._sync_shipping_address_from_delivery_address()

            # Formatear notas con HTML para backend (negrita y rojo)
            formatted_notes = []

            # Añadir notas del pedido si existen
            if notes:
                formatted_notes.append(
                    f'<p><strong style="color: red;">📝 NOTAS DEL PEDIDO:</strong></p>'
                    f'<p style="color: red;"><strong>{notes}</strong></p>'
                )

            # Añadir horario/restricciones si existe
            if delivery_schedule:
                formatted_notes.append(
                    f'<p><strong style="color: red;">📅 HORARIO/RESTRICCIONES DE ENTREGA:</strong></p>'
                    f'<p style="color: red;"><strong>{delivery_schedule}</strong></p>'
                )

            # Combinar todas las notas formateadas
            if formatted_notes:
                order.note = '<br/>'.join(formatted_notes)

            # Crear líneas de pedido
            for line_data in valid_lines:
                try:
                    product = request.env['product.product'].sudo().browse(line_data['product_id'])

                    if not product.exists():
                        _logger.warning(f"Producto {line_data['product_id']} no encontrado")
                        continue

                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id,
                        'product_id': line_data['product_id'],
                        'product_uom_qty': line_data['qty'],
                    })
                except Exception as e:
                    _logger.error(f"Error creando línea de pedido: {str(e)}")
                    continue

            # NOTA: Los documentos se gestionan en la fase post-creación
            # en la ruta /mis-pedidos/{id}/documentos

            # Validar crédito (con manejo de errores)
            try:
                order.validar_credito_antes_confirmar()
            except ValidationError as ve:
                order.sudo().unlink()
                return {'error': _('Error de validación: %s') % str(ve)}
            except Exception as e:
                _logger.warning(f"Error en validación de crédito: {str(e)}")

            _logger.info(
                f"Pedido {order.name} creado desde portal por {request.env.user.login}"
            )

            return {
                'success': True,
                'order_id': order.id,
                'order_name': order.name,
                'redirect_url': f'/mis-pedidos/{order.id}',
            }

        except ValidationError as ve:
            _logger.error(f"Error de validación al crear pedido: {str(ve)}")
            return {'error': _('Error de validación: %s') % str(ve)}
        except Exception as e:
            _logger.error(f"Error al crear pedido desde portal: {str(e)}", exc_info=True)
            return {'error': _('Error al crear el pedido. Por favor, inténtelo de nuevo.')}

    @http.route(['/mis-pedidos/exportar'], type='http', auth='user', website=True)
    def portal_exportar_pedidos(self, date_begin=None, date_end=None, **kw):
        """
        Exporta pedidos a Excel con información completa para el distribuidor.
        
        Parámetros:
            date_begin: Fecha inicio (YYYY-MM-DD)
            date_end: Fecha fin (YYYY-MM-DD)
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect('/mi-portal')

        try:
            import io
            import xlsxwriter
            from collections import defaultdict
            
            # Crear archivo Excel en memoria
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Pedidos')
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#0066CC',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            money_format = workbook.add_format({'num_format': '#,##0.00 €'})
            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Estados en español
            state_translations = {
                'draft': 'Presupuesto',
                'sent': 'Presupuesto Enviado',
                'sale': 'Pedido de Venta',
                'done': 'Bloqueado',
                'cancel': 'Cancelado'
            }
            
            order_status_translations = {
                'new': 'Nuevo',
                'warehouse': 'Almacén',
                'manufacturing': 'Fabricación',
                'prepared': 'Preparado',
                'shipped': 'Salida'
            }
            
            picking_status_translations = {
                'not_created': 'No Creado',
                'waiting': 'Esperando',
                'partially_available': 'Parcialmente Disponible',
                'assigned': 'Reservado',
                'done': 'Realizado',
                'cancelled': 'Cancelado'
            }
            
            # Cabeceras ampliadas
            headers = [
                'Nº Pedido',
                'Su Referencia',
                'Fecha Pedido',
                'Estado',
                'Estado Pedido',
                'Estado Albarán',
                'Subtotal',
                'Impuestos',
                'Total',
                'Dirección Entrega',
                'Cliente Final',
                'Ref. Cliente Final',
                'Nº Líneas',
                'Documentos',
                'Notas'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Obtener pedidos con información completa
            domain = self._get_orders_domain()
            
            if date_begin and date_end:
                domain += [('date_order', '>=', date_begin), ('date_order', '<=', date_end)]
            
            orders = request.env['sale.order'].search(domain, order='date_order desc')
            
            # Escribir datos
            row = 1
            for order in orders:
                # Información básica
                worksheet.write(row, 0, order.name)
                worksheet.write(row, 1, order.client_order_ref or '')
                worksheet.write(row, 2, order.date_order, date_format)
                
                # Estados en español
                worksheet.write(row, 3, state_translations.get(order.state, order.state))
                worksheet.write(row, 4, order_status_translations.get(order.order_status, order.order_status or ''))
                worksheet.write(row, 5, picking_status_translations.get(order.picking_status, order.picking_status or ''))
                
                # Importes
                worksheet.write(row, 6, float(order.amount_untaxed), money_format)
                worksheet.write(row, 7, float(order.amount_tax), money_format)
                worksheet.write(row, 8, float(order.amount_total), money_format)
                
                # Dirección de entrega
                delivery_address = ''
                if hasattr(order, 'delivery_address_id') and order.delivery_address_id:
                    delivery_address = order.delivery_address_id.name
                elif order.partner_shipping_id and order.partner_shipping_id != order.partner_id:
                    delivery_address = order.partner_shipping_id.name
                worksheet.write(row, 9, delivery_address)
                
                # Cliente final
                final_customer = ''
                final_customer_ref = ''
                if hasattr(order, 'distributor_label_id') and order.distributor_label_id:
                    final_customer = order.distributor_label_id.customer_name
                    final_customer_ref = order.distributor_label_id.customer_reference or ''
                elif hasattr(order, 'distributor_customer_name') and order.distributor_customer_name:
                    final_customer = order.distributor_customer_name
                    final_customer_ref = order.distributor_customer_reference or ''
                
                worksheet.write(row, 10, final_customer)
                worksheet.write(row, 11, final_customer_ref)
                
                # Número de líneas
                worksheet.write(row, 12, len(order.order_line), center_format)
                
                # Documentos
                doc_count = 0
                if hasattr(order, 'distributor_document_count'):
                    doc_count = order.distributor_document_count
                worksheet.write(row, 13, doc_count, center_format)
                
                # Notas (combinadas)
                notas = []
                if order.note:
                    notas.append(order.note)
                if hasattr(order, 'delivery_schedule') and order.delivery_schedule:
                    notas.append(f"Horario: {order.delivery_schedule}")
                if hasattr(order, 'distributor_notes') and order.distributor_notes:
                    notas.append(f"Notas distribuidor: {order.distributor_notes}")
                
                worksheet.write(row, 14, ' | '.join(notas))
                
                row += 1
            
            # Ajustar anchos de columna
            column_widths = [15, 20, 12, 18, 15, 20, 12, 12, 12, 25, 25, 15, 8, 8, 40]
            for col, width in enumerate(column_widths):
                worksheet.set_column(col, col, width)
            
            # Añadir hoja de resumen
            summary_sheet = workbook.add_worksheet('Resumen')
            
            # Cabecera resumen
            summary_sheet.write(0, 0, 'RESUMEN DE PEDIDOS', header_format)
            summary_sheet.write(1, 0, f'Distribuidor: {partner.name}')
            summary_sheet.write(2, 0, f'Período: {date_begin or "Desde inicio"} - {date_end or "Hasta hoy"}')
            summary_sheet.write(3, 0, f'Total pedidos: {len(orders)}')
            
            # Estadísticas por estado
            summary_sheet.write(5, 0, 'ESTADÍSTICAS POR ESTADO', header_format)
            summary_sheet.write(6, 0, 'Estado', header_format)
            summary_sheet.write(6, 1, 'Cantidad', header_format)
            summary_sheet.write(6, 2, 'Total €', header_format)
            
            # Agrupar por estado
            stats_by_state = defaultdict(lambda: {'count': 0, 'total': 0.0})
            
            for order in orders:
                state_name = state_translations.get(order.state, order.state)
                stats_by_state[state_name]['count'] += 1
                stats_by_state[state_name]['total'] += float(order.amount_total)
            
            summary_row = 7
            for state_name, stats in stats_by_state.items():
                summary_sheet.write(summary_row, 0, state_name)
                summary_sheet.write(summary_row, 1, stats['count'], center_format)
                summary_sheet.write(summary_row, 2, stats['total'], money_format)
                summary_row += 1
            
            # Total general
            total_amount = sum(float(order.amount_total) for order in orders)
            summary_sheet.write(summary_row + 1, 0, 'TOTAL GENERAL', header_format)
            summary_sheet.write(summary_row + 1, 1, len(orders), center_format)
            summary_sheet.write(summary_row + 1, 2, total_amount, money_format)
            
            # Ajustar anchos resumen
            summary_sheet.set_column(0, 0, 25)
            summary_sheet.set_column(1, 1, 12)
            summary_sheet.set_column(2, 2, 15)
            
            workbook.close()
            output.seek(0)
            
            # Generar nombre de archivo con fecha
            fecha_str = fields.Date.today().strftime('%Y%m%d')
            periodo_str = ''
            if date_begin and date_end:
                periodo_str = f'_{date_begin}_{date_end}'
            
            filename = f'pedidos_{partner.name.replace(" ", "_")}_{fecha_str}{periodo_str}.xlsx'
            
            return request.make_response(
                output.read(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )
            
        except ImportError:
            _logger.error("xlsxwriter no está instalado")
            return request.redirect('/mis-pedidos?error=export_failed')
        except Exception as e:
            _logger.error(f"Error al exportar pedidos: {str(e)}")
            return request.redirect('/mis-pedidos?error=export_failed')

    @http.route(['/mis-facturas/<int:invoice_id>'], type='http', auth='user', website=True)
    def portal_factura_detalle(self, invoice_id, report_type=None, access_token=None, **kw):
        """Detalle de una factura específica (SIN descarga para distribuidores)."""
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/mis-facturas')

        partner = request.env.user.partner_id
        if invoice_sudo.partner_id.commercial_partner_id != partner.commercial_partner_id:
            _logger.warning(
                f"Intento de acceso no autorizado a factura {invoice_id} "
                f"por usuario {request.env.user.login}"
            )
            return request.redirect('/mis-facturas')

        # BLOQUEAR descarga de PDF para distribuidores
        if report_type == 'pdf':
            if partner.is_distributor:
                _logger.warning(
                    f"Distribuidor {partner.name} intentó descargar factura {invoice_sudo.name}. "
                    f"Descarga bloqueada - las facturas se envían por correo desde el backend."
                )
                return request.redirect(f'/mis-facturas/{invoice_id}?error=download_blocked')
            
            # Para usuarios NO distribuidores, permitir descarga
            try:
                # Asegurar que la factura tenga token
                if not invoice_sudo.access_token:
                    invoice_sudo.sudo().access_token = invoice_sudo._generate_access_token()
                    _logger.info(f"Token generado para factura {invoice_sudo.name}")
                
                # Generar PDF usando el reporte estándar de Odoo
                pdf_content, content_type = request.env.ref('account.account_invoices').sudo()._render_qweb_pdf([invoice_id])
                
                # Headers para forzar descarga
                pdfhttpheaders = [
                    ('Content-Type', 'application/pdf'),
                    ('Content-Length', len(pdf_content)),
                    ('Content-Disposition', f'attachment; filename="{invoice_sudo.name}.pdf"')
                ]
                
                _logger.info(f"PDF generado correctamente para factura {invoice_sudo.name}")
                
                return request.make_response(pdf_content, headers=pdfhttpheaders)
            except Exception as e:
                _logger.error(f"Error generando PDF de factura {invoice_id}: {str(e)}", exc_info=True)
                return request.redirect(f'/mis-facturas/{invoice_id}?error=pdf_failed')

        # Vista de detalle de la factura en el navegador
        values = self._prepare_portal_layout_values()
        values.update({
            'invoice': invoice_sudo,
            'page_name': 'factura_detalle',
            'report_type': report_type,
            'is_distributor': partner.is_distributor,  # Para ocultar botón en template
        })

        return request.render('portal_b2b_base.portal_factura_detalle', values)

    @http.route(['/mis-facturas', '/mis-facturas/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_mis_facturas(self, page=1, date_begin=None, date_end=None, 
                           sortby=None, search=None, **kw):
        """Lista paginada de facturas del distribuidor."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect('/mi-portal')

        AccountMove = request.env['account.move']

        searchbar_sortings = {
            'date': {'label': 'Fecha Factura', 'order': 'invoice_date desc'},
            'name': {'label': 'Número', 'order': 'name desc'},
            'amount': {'label': 'Total', 'order': 'amount_total desc'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        domain = self._get_invoices_domain()

        if date_begin and date_end:
            domain += [('invoice_date', '>=', date_begin), ('invoice_date', '<=', date_end)]

        if search:
            domain += [('name', 'ilike', search)]

        invoice_count = AccountMove.search_count(domain)

        pager = portal_pager(
            url='/mis-facturas',
            url_args={'date_begin': date_begin, 'date_end': date_end, 
                     'sortby': sortby, 'search': search},
            total=invoice_count,
            page=page,
            step=20,
        )

        invoices = AccountMove.search(domain, order=order, limit=20, offset=pager['offset'])

        current_year = fields.Date.today().year
        year_domain = domain + [
            ('invoice_date', '>=', f'{current_year}-01-01'),
            ('invoice_date', '<=', f'{current_year}-12-31'),
            ('state', '=', 'posted'),
        ]
        year_invoices = AccountMove.search(year_domain)
        total_year = sum(year_invoices.mapped('amount_total'))

        values = self._prepare_portal_layout_values()
        values.update({
            'invoices': invoices,
            'page_name': 'mis_facturas',
            'pager': pager,
            'default_url': '/mis-facturas',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'search': search,
            'date_begin': date_begin,
            'date_end': date_end,
            'total_year': float(total_year or 0.0),
        })

        return request.render('portal_b2b_base.portal_mis_facturas', values)

    @http.route(['/mi-cuenta'], type='http', auth='user', website=True)
    def portal_mi_cuenta(self, **kw):
        """Página de gestión de cuenta del distribuidor."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect('/mi-portal')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'mi_cuenta',
            'partner': partner,
            'user': request.env.user,
        })

        return request.render('portal_b2b_base.portal_mi_cuenta', values)

    @http.route(['/mi-cuenta/actualizar'], type='json', auth='user', 
                methods=['POST'], csrf=True)
    def portal_mi_cuenta_actualizar(self, **kw):
        """Actualiza datos de contacto del distribuidor vía AJAX."""
        partner = request.env.user.partner_id

        try:
            update_vals = {}

            if 'phone' in kw:
                update_vals['phone'] = kw['phone']

            if 'mobile' in kw:
                update_vals['mobile'] = kw['mobile']

            if 'email' in kw:
                update_vals['email'] = kw['email']

            if update_vals:
                partner.sudo().write(update_vals)
                _logger.info(f"Datos actualizados para partner {partner.name}")

            return {'success': True, 'message': _('Datos actualizados correctamente')}

        except Exception as e:
            _logger.error(f"Error al actualizar datos de partner: {str(e)}")
            return {'error': _('Error al actualizar los datos')}

    # ========== NOTIFICACIONES ==========

    @http.route(['/mis-notificaciones'], type='http', auth='user', website=True)
    def portal_notifications(self, **kw):
        """Lista de notificaciones."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            notifications = request.env['portal.notification'].get_recent_notifications(
                partner.id, limit=50
            )
        except Exception as e:
            _logger.warning(f"Error obteniendo notificaciones: {str(e)}")
            notifications = []
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'notifications',
            'notifications': notifications,
        })
        
        return request.render('portal_b2b_base.portal_notifications', values)

    # ========== MENSAJES ==========

    @http.route(['/mis-mensajes'], type='http', auth='user', website=True)
    def portal_messages(self, **kw):
        """Lista de mensajes."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            messages = request.env['portal.message'].get_recent_messages(
                partner.id, limit=50
            )
        except Exception as e:
            _logger.warning(f"Error obteniendo mensajes: {str(e)}")
            messages = []
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'messages',
            'messages': messages,
        })
        
        return request.render('portal_b2b_base.portal_messages', values)

    @http.route(['/api/mensajes/enviar'], type='json', auth='user', methods=['POST'])
    def api_send_message(self, subject, message, parent_id=None, **kw):
        """Envía un mensaje."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            message_data = {
                'partner_id': partner.id,
                'subject': subject,
                'message': message,
                'sender_type': 'distributor',
            }
            
            if parent_id:
                message_data['parent_id'] = parent_id
            
            new_message = request.env['portal.message'].create(message_data)
            
            return {
                'success': True,
                'message_id': new_message.id
            }
        except Exception as e:
            _logger.error(f"Error enviando mensaje: {str(e)}")
            return {'error': str(e)}

    # ========== DEVOLUCIONES ==========

    @http.route(['/mis-devoluciones'], type='http', auth='user', website=True)
    def portal_returns(self, **kw):
        """Lista de devoluciones."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            returns = request.env['sale.return'].search([
                ('partner_id', '=', partner.id)
            ], order='create_date desc')
        except Exception as e:
            _logger.warning(f"Error obteniendo devoluciones: {str(e)}")
            returns = []
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'returns',
            'returns': returns,
        })
        
        return request.render('portal_b2b_base.portal_returns', values)

    @http.route(['/crear-devolucion'], type='http', auth='user', website=True)
    def portal_create_return(self, order_id=None, **kw):
        """Formulario para crear una devolución."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        # Obtener pedidos confirmados/entregados del distribuidor
        orders = request.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done'])
        ], order='date_order desc')
        
        # Si viene order_id, obtener productos del pedido
        selected_order = None
        order_products = []
        
        if order_id:
            try:
                selected_order = request.env['sale.order'].browse(int(order_id))
                if selected_order.exists() and selected_order.partner_id == partner:
                    # Obtener productos únicos del pedido
                    for line in selected_order.order_line:
                        if line.product_id:
                            order_products.append({
                                'id': line.product_id.id,
                                'name': line.product_id.name,
                                'default_code': line.product_id.default_code or '',
                                'quantity_ordered': line.product_uom_qty,
                                'price_unit': line.price_unit,
                            })
            except Exception as e:
                _logger.warning(f"Error obteniendo pedido {order_id}: {str(e)}")
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'create_return',
            'orders': orders,
            'selected_order': selected_order,
            'order_products': order_products,
        })
        
        return request.render('portal_b2b_base.portal_create_return', values)

    @http.route(['/crear-devolucion/submit'], type='http', auth='user', 
                website=True, methods=['POST'], csrf=True)
    def portal_create_return_submit(self, **kw):
        """Procesa la creación de una nueva devolución."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            # Obtener datos del formulario
            order_id = kw.get('order_id')
            reason = kw.get('reason')
            reason_description = kw.get('reason_description', '')
            customer_notes = kw.get('customer_notes', '')
            
            # Validaciones básicas
            if not order_id or not reason:
                return request.redirect('/crear-devolucion?error=missing_data')
            
            # Verificar que el pedido pertenece al distribuidor
            order = request.env['sale.order'].browse(int(order_id))
            if not order.exists() or order.partner_id != partner:
                return request.redirect('/crear-devolucion?error=invalid_order')
            
            # Crear devolución
            return_vals = {
                'partner_id': partner.id,
                'order_id': order.id,
                'reason': reason,
                'reason_description': reason_description,
                'customer_notes': customer_notes,
                'state': 'draft',
            }
            
            return_obj = request.env['sale.return'].create(return_vals)
            
            # Procesar líneas de productos
            product_ids = kw.getlist('product_id[]')
            quantities = kw.getlist('quantity[]')
            notes_list = kw.getlist('notes[]')
            
            if not product_ids or not quantities:
                return_obj.unlink()
                return request.redirect('/crear-devolucion?error=no_products')
            
            for i, product_id in enumerate(product_ids):
                if product_id and quantities[i]:
                    try:
                        qty = float(quantities[i])
                        if qty <= 0:
                            continue
                        
                        product = request.env['product.product'].browse(int(product_id))
                        if not product.exists():
                            continue
                        
                        # Obtener precio del pedido original
                        order_line = order.order_line.filtered(
                            lambda l: l.product_id.id == product.id
                        )
                        unit_price = order_line[0].price_unit if order_line else product.list_price
                        
                        request.env['sale.return.line'].create({
                            'return_id': return_obj.id,
                            'product_id': int(product_id),
                            'quantity': qty,
                            'unit_price': unit_price,
                            'notes': notes_list[i] if i < len(notes_list) else '',
                        })
                    except (ValueError, IndexError) as e:
                        _logger.warning(f"Error procesando línea {i}: {str(e)}")
                        continue
            
            # Verificar que se crearon líneas
            if not return_obj.line_ids:
                return_obj.unlink()
                return request.redirect('/crear-devolucion?error=no_valid_products')
            
            # Enviar para aprobación automáticamente
            return_obj.action_submit()
            
            _logger.info(f"Devolución creada y enviada por {partner.name} para pedido {order.name}")
            
            return request.redirect(f'/mis-devoluciones?created=success')
            
        except Exception as e:
            _logger.error(f"Error creando devolución: {str(e)}", exc_info=True)
            return request.redirect('/crear-devolucion?error=create_failed')

    # ========== PLANTILLAS ==========

    @http.route(['/mis-plantillas'], type='http', auth='user', website=True)
    def portal_templates(self, **kw):
        """Lista de plantillas de pedidos."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            templates = request.env['sale.order.template'].search([
                ('partner_id', '=', partner.id)
            ], order='name asc')
        except Exception as e:
            _logger.warning(f"Error obteniendo plantillas: {str(e)}")
            templates = []
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'templates',
            'templates': templates,
        })
        
        return request.render('portal_b2b_base.portal_my_templates', values)

    @http.route(['/mis-plantillas/crear'], type='http', auth='user', website=True)
    def portal_create_template(self, **kw):
        """Formulario para crear una nueva plantilla."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'create_template',
        })
        
        return request.render('portal_b2b_base.portal_create_template', values)

    @http.route(['/mis-plantillas/crear/submit'], type='json', auth='user', 
                methods=['POST'], csrf=True)
    def portal_create_template_submit(self, **kw):
        """Procesa la creación de una nueva plantilla."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            name = kw.get('name')
            notes = kw.get('notes', '')
            lines_data = kw.get('lines', [])
            
            if not name:
                return {'error': _('El nombre es obligatorio')}
            
            if not lines_data:
                return {'error': _('Debe agregar al menos un producto')}
            
            # Crear plantilla
            template = request.env['sale.order.template'].create({
                'name': name,
                'partner_id': partner.id,
                'notes': notes,
            })
            
            # Crear líneas
            for line_data in lines_data:
                request.env['sale.order.template.line'].create({
                    'template_id': template.id,
                    'product_id': line_data['product_id'],
                    'quantity': line_data['quantity'],
                    'notes': line_data.get('notes', ''),
                })
            
            return {
                'success': True,
                'template_id': template.id,
                'redirect_url': f'/mis-plantillas/{template.id}',
            }
            
        except Exception as e:
            _logger.error(f"Error creando plantilla: {str(e)}")
            return {'error': _('Error al crear la plantilla')}

    @http.route(['/mis-plantillas/<int:template_id>'], type='http', auth='user', website=True)
    def portal_template_detail(self, template_id, **kw):
        """Detalle de una plantilla."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            template = request.env['sale.order.template'].browse(template_id)
            if not template.exists() or template.partner_id != partner:
                return request.redirect('/mis-plantillas')
        except Exception:
            return request.redirect('/mis-plantillas')
        
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'template_detail',
            'template': template,
        })
        
        return request.render('portal_b2b_base.portal_template_detail', values)

    @http.route(['/mis-plantillas/<int:template_id>/usar'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_use_template(self, template_id, **kw):
        """Usa una plantilla para crear un nuevo pedido."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            template = request.env['sale.order.template'].browse(template_id)
            if not template.exists() or template.partner_id != partner:
                return request.redirect('/mis-plantillas')
            
            # Crear pedido desde plantilla
            order = template.action_create_order_from_template()
            
            return request.redirect(f'/mis-pedidos/{order.id}')
        except Exception as e:
            _logger.error(f"Error usando plantilla: {str(e)}")
            return request.redirect('/mis-plantillas?error=use_failed')

    @http.route(['/mis-plantillas/<int:template_id>/eliminar'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_delete_template(self, template_id, **kw):
        """Elimina una plantilla."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        try:
            template = request.env['sale.order.template'].browse(template_id)
            if not template.exists() or template.partner_id != partner:
                return request.redirect('/mis-plantillas')
            
            template.unlink()
            
            return request.redirect('/mis-plantillas?deleted=success')
        except Exception as e:
            _logger.error(f"Error eliminando plantilla: {str(e)}")
            return request.redirect('/mis-plantillas?error=delete_failed')

    # ========== ESTADÍSTICAS ==========

    @http.route(['/mi-portal/estadisticas'], type='http', auth='user', website=True)
    def portal_statistics_dashboard(self, period='month', **kwargs):
        """Dashboard de estadísticas del distribuidor."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        from datetime import datetime, timedelta
        today = datetime.today().date()
        
        # Calcular fechas según período
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
        
        try:
            # Dominio base para pedidos del distribuidor
            order_domain = [
                ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
                ('date_order', '>=', start_date),
                ('date_order', '<=', today),
            ]
            
            # Obtener pedidos
            orders = request.env['sale.order'].search(order_domain)
            
            # Calcular estadísticas de pedidos
            total_orders = len(orders)
            confirmed_orders = orders.filtered(lambda o: o.state in ['sale', 'done'])
            total_amount = sum(float(o.amount_total) for o in orders)
            average_value = total_amount / total_orders if total_orders > 0 else 0
            
            # Obtener productos más pedidos
            order_lines = orders.mapped('order_line')
            product_stats = {}
            
            for line in order_lines:
                product_id = line.product_id.id
                if product_id not in product_stats:
                    product_stats[product_id] = {
                        'product': line.product_id,
                        'quantity': 0,
                        'amount': 0,
                    }
                product_stats[product_id]['quantity'] += line.product_uom_qty
                product_stats[product_id]['amount'] += line.price_subtotal
            
            # Ordenar por cantidad y tomar top 10
            top_products = sorted(
                product_stats.values(),
                key=lambda x: x['quantity'],
                reverse=True
            )[:10]
            
            top_products_data = []
            for item in top_products:
                top_products_data.append({
                    'name': item['product'].name,
                    'default_code': item['product'].default_code or '',
                    'quantity': item['quantity'],
                    'amount': item['amount'],
                })
            
            # Estadísticas de facturación
            invoice_domain = [
                ('move_type', '=', 'out_invoice'),
                ('partner_id', 'child_of', partner.commercial_partner_id.id),
                ('invoice_date', '>=', start_date),
                ('invoice_date', '<=', today),
                ('state', '=', 'posted'),
            ]
            
            invoices = request.env['account.move'].search(invoice_domain)
            
            total_invoiced = sum(float(inv.amount_total) for inv in invoices)
            paid_invoices = invoices.filtered(lambda i: i.payment_state == 'paid')
            total_paid = sum(float(inv.amount_total) for inv in paid_invoices)
            pending_payment = total_invoiced - total_paid
            
            # Construir datos del dashboard
            dashboard_data = {
                'orders': {
                    'total': total_orders,
                    'confirmed': len(confirmed_orders),
                    'total_amount': total_amount,
                    'average_value': average_value,
                },
                'products': {
                    'total_ordered': len(product_stats),
                    'top_products': top_products_data,
                },
                'invoicing': {
                    'total_invoiced': total_invoiced,
                    'total_paid': total_paid,
                    'pending_payment': pending_payment,
                },
            }
            
        except Exception as e:
            _logger.error(f"Error calculando estadísticas: {str(e)}", exc_info=True)
            dashboard_data = {
                'orders': {'total': 0, 'confirmed': 0, 'total_amount': 0, 'average_value': 0},
                'products': {'total_ordered': 0, 'top_products': []},
                'invoicing': {'total_invoiced': 0, 'total_paid': 0, 'pending_payment': 0},
            }
        
        values = self._prepare_portal_layout_values()
        values.update({
            'dashboard_data': dashboard_data,
            'period': period,
            'page_name': 'statistics',
        })
        
        return request.render('portal_b2b_base.portal_statistics_dashboard', values)

    # ========== HISTORIAL ==========

    @http.route(['/mi-historial'], type='http', auth='user', website=True)
    def portal_activity_history(self, page=1, action_filter=None, **kw):
        """Historial de actividad del distribuidor."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return request.redirect('/mi-portal')
        
        from odoo.addons.portal.controllers.portal import pager as portal_pager
        
        domain = [('partner_id', '=', partner.id)]
        
        if action_filter:
            domain.append(('action', '=', action_filter))
        
        try:
            log_count = request.env['portal.audit.log'].search_count(domain)
            
            pager = portal_pager(
                url='/mi-historial',
                url_args={'action_filter': action_filter},
                total=log_count,
                page=page,
                step=50,
            )
            
            logs = request.env['portal.audit.log'].search(
                domain,
                limit=50,
                offset=pager['offset'],
                order='create_date desc'
            )
        except Exception as e:
            _logger.warning(f"Error obteniendo historial: {str(e)}")
            logs = []
            log_count = 0
            pager = {}
        
        values = self._prepare_portal_layout_values()
        values.update({
            'logs': logs,
            'log_count': log_count,
            'page_name': 'historial',
            'pager': pager,
            'action_filter': action_filter,
        })
        
        return request.render('portal_b2b_base.portal_activity_history', values)

    # ========== API ENDPOINTS ADICIONALES ==========

    @http.route(['/api/notificaciones/marcar-leida'], type='json', auth='user', methods=['POST'])
    def api_mark_notification_read(self, notification_id, **kw):
        """Marca una notificación como leída."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            notification = request.env['portal.notification'].browse(notification_id)
            
            if not notification.exists() or notification.partner_id != partner:
                return {'error': _('Notificación no encontrada')}
            
            notification.action_mark_read()
            
            return {'success': True}
            
        except Exception as e:
            _logger.error(f"Error marcando notificación: {str(e)}")
            return {'error': str(e)}

    # ========== GESTIÓN DOCUMENTOS DISTRIBUIDOR ==========

    @http.route(['/mis-pedidos/<int:order_id>/documentos'], 
                type='http', auth='user', website=True)
    def portal_order_documents(self, order_id, **kw):
        """Página de gestión de documentos del pedido."""
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return request.redirect('/mis-pedidos')
        except Exception:
            return request.redirect('/mis-pedidos')

        partner = request.env.user.partner_id
        if order.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return request.redirect('/mis-pedidos')

        values = self._prepare_portal_layout_values()
        values.update({
            'order': order,
            'page_name': 'order_documents',
        })

        return request.render('portal_b2b_base.portal_order_documents', values)

    @http.route(['/mis-pedidos/<int:order_id>/subir-documento'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_upload_document(self, order_id, document_type, **post):
        """Sube un documento al pedido."""
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return request.redirect('/mis-pedidos')
        except Exception:
            return request.redirect('/mis-pedidos')

        partner = request.env.user.partner_id
        if order.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return request.redirect('/mis-pedidos')

        try:
            uploaded_file = request.httprequest.files.get('file')
            
            if not uploaded_file:
                return request.redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=no_file'
                )

            uploaded_file.seek(0, 2)
            file_size = uploaded_file.tell()
            uploaded_file.seek(0)
            
            if file_size > 10 * 1024 * 1024:
                return request.redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=file_too_large'
                )

            filename = uploaded_file.filename
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            if not any(filename.lower().endswith(ext)for ext in allowed_extensions):
                return request.redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=invalid_format'
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
                field_name: [(4, attachment.id)]
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

            return request.redirect(
                f'/mis-pedidos/{order_id}/documentos?uploaded=success'
            )

        except Exception as e:
            _logger.error(f"Error al subir documento: {str(e)}", exc_info=True)
            return request.redirect(
                f'/mis-pedidos/{order_id}/documentos?error=upload_failed'
            )


    @http.route(['/mis-pedidos/<int:order_id>/eliminar-documento/<int:attachment_id>'], 
                type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_delete_document(self, order_id, attachment_id, **kw):
        """Elimina un documento del pedido."""
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return request.redirect('/mis-pedidos')
        except Exception:
            return request.redirect('/mis-pedidos')

        partner = request.env.user.partner_id
        if order.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return request.redirect('/mis-pedidos')

        try:
            attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
            
            if not attachment.exists():
                return request.redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=not_found'
                )

            if attachment.res_model != 'sale.order' or attachment.res_id != order_id:
                return request.redirect(
                    f'/mis-pedidos/{order_id}/documentos?error=unauthorized'
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

            return request.redirect(
                f'/mis-pedidos/{order_id}/documentos?deleted=success'
            )

        except Exception as e:
            _logger.error(f"Error al eliminar documento: {str(e)}", exc_info=True)
            return request.redirect(
                f'/mis-pedidos/{order_id}/documentos?error=delete_failed'
            )

    # ========== API PREFERENCIAS ==========

    @http.route(['/api/preferencias/actualizar'], type='json', auth='user', methods=['POST'])
    def api_update_preferences(self, **preferences):
        """Actualiza preferencias del usuario."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            # Guardar preferencias en el partner o en un modelo específico
            # Por ahora solo confirmamos que se recibieron
            _logger.info(f"Preferencias actualizadas para {partner.name}: {preferences}")
            
            return {'success': True}
            
        except Exception as e:
            _logger.error(f"Error actualizando preferencias: {str(e)}")
            return {'error': str(e)}

    @http.route(['/api/preferencias/obtener'], type='json', auth='user', methods=['POST'])
    def api_get_preferences(self, **kw):
        """Obtiene preferencias del usuario."""
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            # Por ahora devolver preferencias por defecto
            # En el futuro se pueden guardar en base de datos
            preferences = {
                'theme_mode': 'light',
                'high_contrast': False,
                'large_text': False,
                'reduce_motion': False,
                'screen_reader_mode': False,
                'dashboard_layout': 'cards',
                'orders_per_page': 20,
            }
            
            return {'success': True, 'preferences': preferences}
            
        except Exception as e:
            _logger.error(f"Error obteniendo preferencias: {str(e)}")
            return {'error': str(e)}

    # ========== API JSON ==========

    @http.route(['/api/productos/buscar'], type='json', auth='user', methods=['POST'])
    def api_productos_buscar(self, query='', limit=10, **kw):
        """API para búsqueda de productos (autocompletado)."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {'error': _('Usuario no autorizado')}

        try:
            if not query or not query.strip():
                return {'products': []}

            query = query.strip()
            limit = int(limit) if limit else 10

            # Obtener dominio base con restricciones de categoría
            base_domain = partner.get_allowed_product_domain()

            # Añadir filtro de búsqueda
            search_domain = [
                '|',
                ('name', 'ilike', query),
                ('default_code', 'ilike', query),
            ]

            domain = base_domain + search_domain

            products = request.env['product.product'].sudo().search(domain, limit=limit)
            
            pricelist = None
            if hasattr(partner, 'obtener_tarifa_aplicable'):
                try:
                    pricelist = partner.obtener_tarifa_aplicable()
                except Exception as e:
                    _logger.debug(f"Error obteniendo tarifa: {str(e)}")

            result = []
            for product in products:
                price = float(product.list_price or 0.0)
                
                if pricelist:
                    try:
                        price_compute = pricelist._get_product_price(
                            product,
                            1.0,
                            partner=partner,
                            date=fields.Date.today(),
                        )
                        if price_compute:
                            price = float(price_compute)
                    except Exception as e:
                        _logger.debug(
                            f"No se pudo obtener precio de tarifa para {product.name}: {str(e)}"
                        )

                result.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code or '',
                    'list_price': price,
                    'uom_name': product.uom_id.name,
                })

            return {'products': result}

        except Exception as e:
            _logger.error(f"Error en búsqueda de productos: {str(e)}", exc_info=True)
            return {'error': _('Error en la búsqueda')}

    @http.route(['/api/productos/<int:product_id>/stock'], 
                type='json', auth='user', methods=['POST'])
    def api_producto_stock(self, product_id, **kw):
        """Obtiene información de stock de un producto."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {'error': _('Usuario no autorizado')}

        try:
            product = request.env['product.product'].sudo().browse(product_id)

            if not product.exists():
                return {'error': _('Producto no encontrado')}

            return {
                'message': 'Información de stock no disponible para distribuidores'
            }

        except Exception as e:
            _logger.error(f"Error al obtener stock del producto {product_id}: {str(e)}")
            return {'error': _('Error al obtener información de stock')}

    @http.route(['/api/productos/<int:product_id>/historial-precios'], 
                type='json', auth='user', methods=['POST'])
    def api_producto_historial_precios(self, product_id, **kw):
        """
        Obtiene historial de precios de un producto en pedidos anteriores.
        
        Returns:
            Lista de precios históricos con fechas
        """
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {'error': _('Usuario no autorizado')}

        try:
            # Buscar líneas de pedido anteriores con este producto
            order_lines = request.env['sale.order.line'].search([
                ('order_id.partner_id', '=', partner.id),
                ('product_id', '=', product_id),
                ('order_id.state', 'in', ['sale', 'done'])
            ], order='order_id.date_order desc', limit=10)
            
            historial = []
            for line in order_lines:
                historial.append({
                    'fecha': line.order_id.date_order.strftime('%d/%m/%Y'),
                    'pedido': line.order_id.name,
                    'cantidad': float(line.product_uom_qty),
                    'precio_unitario': float(line.price_unit),
                    'subtotal': float(line.price_subtotal),
                })
            
            return {'historial': historial}

        except Exception as e:
            _logger.error(f"Error al obtener historial de precios: {str(e)}")
            return {'error': _('Error al obtener historial')}

    @http.route(['/api/productos/catalogo'], type='json', auth='user', methods=['POST'])
    def api_productos_catalogo(self, page=1, limit=20, search='', category_id=None, sort='name', **kw):
        """API para obtener catálogo de productos con imágenes."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {'error': _('Usuario no autorizado')}

        try:
            page = int(page)
            limit = int(limit)
            offset = (page - 1) * limit

            # Construir dominio con restricciones de categoría
            domain = partner.get_allowed_product_domain()

            if search:
                domain += [
                    '|', '|',
                    ('name', 'ilike', search),
                    ('default_code', 'ilike', search),
                    ('description_sale', 'ilike', search),
                ]

            if category_id:
                domain.append(('categ_id', '=', int(category_id)))

            # Ordenamiento
            order_map = {
                'name': 'name asc',
                'price': 'list_price asc',
                'code': 'default_code asc',
            }
            order = order_map.get(sort, 'name asc')

            # Contar total
            total_count = request.env['product.product'].sudo().search_count(domain)

            # Obtener productos
            products = request.env['product.product'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order=order
            )

            # Obtener tarifa del distribuidor
            pricelist = None
            if hasattr(partner, 'obtener_tarifa_aplicable'):
                try:
                    pricelist = partner.obtener_tarifa_aplicable()
                except Exception as e:
                    _logger.debug(f"Error obteniendo tarifa: {str(e)}")

            # Preparar datos
            result = []
            for product in products:
                # Calcular precio
                price = float(product.list_price or 0.0)
                if pricelist:
                    try:
                        price_compute = pricelist._get_product_price(
                            product,
                            1.0,
                            partner=partner,
                            date=fields.Date.today(),
                        )
                        if price_compute:
                            price = float(price_compute)
                    except Exception:
                        pass

                # Obtener imagen (base64)
                image_url = f'/web/image/product.product/{product.id}/image_128'

                result.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code or '',
                    'description_sale': product.description_sale or '',
                    'list_price': price,
                    'uom_name': product.uom_id.name,
                    'image_url': image_url,
                    'categ_id': product.categ_id.id if product.categ_id else None,
                    'categ_name': product.categ_id.name if product.categ_id else '',
                })

            # Calcular páginas
            total_pages = (total_count + limit - 1) // limit

            return {
                'products': result,
                'total_count': total_count,
                'page': page,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }

        except Exception as e:
            _logger.error(f"Error en catálogo de productos: {str(e)}", exc_info=True)
            return {'error': _('Error al cargar el catálogo')}

    @http.route(['/api/productos/categorias'], type='json', auth='user', methods=['POST'])
    def api_productos_categorias(self, **kw):
        """API para obtener categorías de productos."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return {'error': _('Usuario no autorizado')}

        try:
            # Obtener categorías permitidas para el distribuidor
            if partner.allow_all_categories or not partner.allowed_product_categories:
                # Todas las categorías con productos
                categories = request.env['product.category'].sudo().search([
                    ('product_count', '>', 0)
                ], order='name asc')
            else:
                # Solo categorías permitidas (incluyendo hijas)
                allowed_category_ids = partner._get_child_categories(
                    partner.allowed_product_categories.ids
                )
                categories = request.env['product.category'].sudo().browse(allowed_category_ids)

            result = []
            for category in categories:
                # Contar productos vendibles en esta categoría
                product_count = request.env['product.product'].sudo().search_count([
                    ('categ_id', '=', category.id),
                    ('sale_ok', '=', True),
                    ('active', '=', True),
                ])

                if product_count > 0:
                    result.append({
                        'id': category.id,
                        'name': category.name,
                        'product_count': product_count,
                    })

            return {'categories': result}

        except Exception as e:
            _logger.error(f"Error obteniendo categorías: {str(e)}")
            return {'error': _('Error al cargar categorías')}

    @http.route(['/api/notificaciones/recientes'], type='json', auth='user', methods=['POST'])
    def get_recent_notifications(self, limit=10, **kw):
        """
        API para obtener notificaciones recientes.
        
        Args:
            limit: Número máximo de notificaciones
            
        Returns:
            dict: Lista de notificaciones
        """
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            notifications = request.env['portal.notification'].sudo().get_recent_notifications(
                partner.id,
                limit=limit
            )
            
            unread_count = request.env['portal.notification'].sudo().get_unread_count(
                partner.id
            )
            
            return {
                'success': True,
                'notifications': notifications,
                'unread_count': unread_count,
            }
            
        except Exception as e:
            _logger.error(f"Error obteniendo notificaciones: {str(e)}")
            return {'error': str(e)}

    @http.route(['/api/notificaciones/<int:notification_id>/marcar-leida'], 
                type='json', auth='user', methods=['POST'])
    def mark_notification_read(self, notification_id, **kw):
        """
        Marca una notificación como leída.
        
        Args:
            notification_id: ID de la notificación
            
        Returns:
            dict: Resultado de la operación
        """
        partner = request.env.user.partner_id
        
        if not partner.is_distributor:
            return {'error': _('No autorizado')}
        
        try:
            notification = request.env['portal.notification'].sudo().browse(notification_id)
            
            if not notification.exists() or notification.partner_id != partner:
                return {'error': _('Notificación no encontrada')}
            
            notification.action_mark_read()
            
            return {'success': True}
            
        except Exception as e:
            _logger.error(f"Error marcando notificación como leída: {str(e)}")
            return {'error': str(e)}

