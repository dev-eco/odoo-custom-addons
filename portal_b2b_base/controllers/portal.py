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
        - Permitir descargas PDF (report_type='pdf')
        - Redirigir a /mis-pedidos/<id> para distribuidores (navegación normal)
        """
        # Si es una descarga de PDF, usar la funcionalidad estándar
        if report_type in ('html', 'pdf', 'text'):
            _logger.debug(f"Descarga de pedido {order_id} en formato {report_type}")
            return super().portal_order_page(
                order_id=order_id,
                report_type=report_type,
                access_token=access_token,
                message=message,
                download=download,
                **kw
            )
        
        # Si es acceso público con token, usar ruta estándar
        if access_token:
            return super().portal_order_page(
                order_id=order_id,
                access_token=access_token,
                message=message,
                **kw
            )
        
        # Para distribuidores autenticados, redirigir a ruta en español
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
        - Permitir descargas PDF
        - Redirigir a /mis-facturas para distribuidores
        """
        if report_type in ('html', 'pdf', 'text'):
            _logger.debug(f"Descarga de factura {invoice_id} en formato {report_type}")
            return super().portal_my_invoice_detail(
                invoice_id=invoice_id,
                report_type=report_type,
                access_token=access_token,
                message=message,
                download=download,
                **kw
            )
        
        if access_token:
            return super().portal_my_invoice_detail(
                invoice_id=invoice_id,
                access_token=access_token,
                message=message,
                **kw
            )
        
        partner = request.env.user.partner_id
        if partner.is_distributor:
            return request.redirect('/mis-facturas')
        
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
                ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
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
        """Domain para pedidos del distribuidor actual."""
        partner = request.env.user.partner_id
        return [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', '!=', 'cancel'),
        ]

    def _get_invoices_domain(self, invoice_type=None):
        """Domain para facturas del distribuidor actual."""
        partner = request.env.user.partner_id
        domain = [
            ('move_type', '=', invoice_type or 'out_invoice'),
            ('partner_id', 'child_of', partner.commercial_partner_id.id),
        ]
        return domain

    # ========== RUTAS EN ESPAÑOL ==========

    @http.route(['/mi-portal'], type='http', auth='user', website=True)
    def mi_portal_home(self, **kw):
        """Dashboard principal del portal B2B."""
        values = self._prepare_home_portal_values(['order_count', 'invoice_count'])
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

        values = {
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
        }

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
                'note': notes,
                'delivery_schedule': delivery_schedule,
                'client_order_ref': client_order_ref,
            }
            
            # Dirección de entrega (opcional)
            if delivery_address_id:
                try:
                    delivery_address = request.env['delivery.address'].browse(
                        int(delivery_address_id)
                    )
                    if delivery_address.exists() and delivery_address.partner_id == partner:
                        order_vals['delivery_address_id'] = delivery_address.id
                except Exception as e:
                    _logger.warning(f"Error al asignar dirección de entrega: {str(e)}")

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

            # Añadir horario/restricciones a las notas si existe
            if delivery_schedule:
                current_note = order.note or ''
                order.note = f"{current_note}\n\n📅 HORARIO/RESTRICCIONES:\n{delivery_schedule}".strip()

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

        values = {
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
        }

        return request.render('portal_b2b_base.portal_mis_facturas', values)

    @http.route(['/mi-cuenta'], type='http', auth='user', website=True)
    def portal_mi_cuenta(self, **kw):
        """Página de gestión de cuenta del distribuidor."""
        partner = request.env.user.partner_id

        if not partner.is_distributor:
            return request.redirect('/mi-portal')

        values = {
            'page_name': 'mi_cuenta',
            'partner': partner,
            'user': request.env.user,
        }

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

        values = {
            'order': order,
            'page_name': 'order_documents',
        }

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
                f"Documento '{doc_name}' subido al pedido {order_sudo.name} "
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
                    f'/mis-pe didos/{order_id}/documentos?error=unauthorized'
                )

            doc_name = attachment.name
            attachment.unlink()

            order.message_post(
                body=f"🗑️ Documento eliminado desde portal: {doc_name}",
                subject="Documento Eliminado",
                message_type='notification',
            )

            _logger.info(
                f"Documento '{doc_name}' eliminado del pedido {order_sudo.name} "
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

            domain = [
                ('sale_ok', '=', True),
                ('active', '=', True),
                '|',
                ('name', 'ilike', query),
                ('default_code', 'ilike', query),
            ]

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
                    'qty_available': float(product.qty_available) if product.type == 'product' else 999,
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
                'qty_available': float(product.qty_available),
                'incoming_qty': float(product.incoming_qty),
                'outgoing_qty': float(product.outgoing_qty),
                'virtual_available': float(product.virtual_available),
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
