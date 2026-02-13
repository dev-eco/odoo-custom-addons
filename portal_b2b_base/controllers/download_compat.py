# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class DownloadCompatibility(CustomerPortal):
    """Rutas de compatibilidad para descargas de documentos."""
    
    @http.route(['/my/orders/<int:order_id>'], type='http', auth='public', website=True, 
                priority=50)
    def portal_order_page(self, order_id, report_type=None, access_token=None, 
                         message=False, download=False, **kw):
        """Compatibilidad con descarga de pedidos."""
        try:
            # Si es una descarga de PDF, usar la funcionalidad estándar
            if report_type in ('html', 'pdf', 'text'):
                _logger.info(f"Descargando pedido {order_id} en formato {report_type}")
                return super().portal_order_page(
                    order_id=order_id,
                    report_type=report_type,
                    access_token=access_token,
                    message=message,
                    download=download,
                    **kw
                )
            else:
                # Si no es descarga, redirigir a la ruta en español
                _logger.debug(f"Redirigiendo pedido {order_id} a ruta en español")
                return request.redirect(f'/mis-pedidos/{order_id}')
                
        except Exception as e:
            _logger.error(f"Error en descarga de pedido {order_id}: {str(e)}", exc_info=True)
            return request.redirect('/mis-pedidos')
    
    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth='public', website=True,
                priority=50)
    def portal_my_invoice_detail(self, invoice_id, report_type=None, access_token=None,
                                 message=False, download=False, **kw):
        """Compatibilidad con descarga de facturas."""
        try:
            # Si es una descarga de PDF, usar la funcionalidad estándar
            if report_type in ('html', 'pdf', 'text'):
                _logger.info(f"Descargando factura {invoice_id} en formato {report_type}")
                return super().portal_my_invoice_detail(
                    invoice_id=invoice_id,
                    report_type=report_type,
                    access_token=access_token,
                    message=message,
                    download=download,
                    **kw
                )
            else:
                # Si no es descarga, redirigir a la ruta en español
                _logger.debug(f"Redirigiendo factura {invoice_id} a ruta en español")
                return request.redirect(f'/mis-facturas')
                
        except Exception as e:
            _logger.error(f"Error en descarga de factura {invoice_id}: {str(e)}", exc_info=True)
            return request.redirect('/mis-facturas')
