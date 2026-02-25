# -*- coding: utf-8 -*-

import logging
import secrets
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """Extensión de factura para funcionalidades B2B."""

    _inherit = 'account.move'

    # Token de acceso para descargas seguras desde portal
    access_token = fields.Char(
        string='Token de Acceso Portal',
        copy=False,
        readonly=True,
        help='Token para acceso seguro desde el portal'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override para generar access_token automáticamente."""
        for vals in vals_list:
            if 'access_token' not in vals or not vals.get('access_token'):
                vals['access_token'] = self._generate_access_token()
        return super().create(vals_list)

    @staticmethod
    def _generate_access_token():
        """Genera un token de acceso único y seguro."""
        return secrets.token_urlsafe(32)

    @api.model
    def _ensure_access_tokens(self):
        """
        Asegura que todas las facturas tengan access_token.
        Llamado desde post_init_hook.
        """
        invoices_without_token = self.search([
            ('access_token', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ])
        if invoices_without_token:
            _logger.info(f"Generando access_token para {len(invoices_without_token)} facturas...")
            for invoice in invoices_without_token:
                invoice.access_token = self._generate_access_token()
            _logger.info(f"✓ Tokens generados para {len(invoices_without_token)} facturas")


class SaleOrder(models.Model):
    """Extensión de pedido de venta para funcionalidades B2B."""

    _inherit = 'sale.order'

    # Campos B2B
    customer_delivery_note = fields.Binary(
        string='Albarán Cliente',
        attachment=True,
        help='Albarán de entrega firmado por el cliente'
    )

    customer_delivery_note_filename = fields.Char(
        string='Nombre Archivo Albarán'
    )

    is_recurring = fields.Boolean(
        string='Pedido Recurrente',
        default=False,
        help='Marca si este pedido se genera automáticamente de forma recurrente'
    )

    notify_on_stock = fields.Boolean(
        string='Notificar Disponibilidad Stock',
        default=False,
        help='Enviar notificación cuando productos sin stock estén disponibles'
    )

    portal_visible = fields.Boolean(
        string='Visible en Portal',
        compute='_compute_portal_visible',
        store=True,
        help='Determina si el pedido es visible en el portal del cliente'
    )

    can_be_cancelled = fields.Boolean(
        string='Puede Cancelarse',
        compute='_compute_can_be_cancelled',
        help='Indica si el pedido puede ser cancelado desde el portal'
    )

    # Token de acceso para descargas seguras desde portal
    access_token = fields.Char(
        string='Token de Acceso Portal',
        copy=False,
        readonly=True,
        help='Token para acceso seguro desde el portal'
    )

    # Relación con plantillas
    template_id = fields.Many2one(
        'sale.order.template',
        string='Plantilla Origen',
        readonly=True,
        help='Plantilla desde la que se creó este pedido'
    )

    # Campos de estado para distribuidores
    order_status = fields.Selection([
        ('new', 'Nuevo'),
        ('warehouse', 'Almacén'),
        ('manufacturing', 'Fabricación'),
        ('prepared', 'Preparado'),
        ('shipped', 'Salida')
    ], string='Estado de Pedido', default='new', tracking=True, store=True,
       help='Estado actual del pedido: nuevo, en almacén, en fabricación, preparado o ya salido')

    picking_status = fields.Selection([
        ('not_created', 'No Creado'),
        ('waiting', 'Esperando'),
        ('partially_available', 'Parcialmente Disponible'),
        ('assigned', 'Reservado'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado')
    ], string='Estado Albarán', compute='_compute_picking_status', store=True,
       help='Estado del albarán/picking asociado al pedido')

    # Campos para adjuntos del distribuidor
    delivery_schedule = fields.Text(
        string='Horario/Restricciones de Entrega',
        help='Horarios específicos o restricciones de entrega'
    )

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Documentos Adjuntos',
        domain=[('res_model', '=', 'sale.order')],
        help='Etiquetas de transporte, albaranes y otros documentos'
    )

    # Documentos del distribuidor sobre sus clientes finales
    distributor_delivery_note_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_distributor_delivery_note_rel',
        'order_id',
        'attachment_id',
        string='Albaranes Cliente Final',
        help='Albaranes que el distribuidor genera para su cliente final'
    )
    
    distributor_invoice_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_distributor_invoice_rel',
        'order_id',
        'attachment_id',
        string='Facturas Cliente Final',
        help='Facturas que el distribuidor emite a su cliente final'
    )
    
    distributor_label_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_distributor_label_rel',
        'order_id',
        'attachment_id',
        string='Etiquetas Envío Cliente Final',
        help='Etiquetas de envío del distribuidor a su cliente final'
    )
    
    distributor_transport_invoice_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_distributor_transport_rel',
        'order_id',
        'attachment_id',
        string='Facturas Transporte',
        help='Facturas de transporte del distribuidor'
    )
    
    distributor_other_docs_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_distributor_other_rel',
        'order_id',
        'attachment_id',
        string='Otros Documentos',
        help='Otros documentos del distribuidor'
    )
    
    # Contador total de documentos
    distributor_document_count = fields.Integer(
        string='Total Documentos Distribuidor',
        compute='_compute_distributor_document_count',
        store=False,
        help='Número total de documentos subidos por el distribuidor'
    )

    # Campos para información del cliente final del distribuidor
    distributor_customer_name = fields.Char(
        string='Cliente Final del Distribuidor',
        help='Nombre del cliente final al que el distribuidor vende',
        copy=False
    )

    distributor_customer_reference = fields.Char(
        string='Referencia Cliente Final',
        help='Referencia del cliente final del distribuidor',
        copy=False
    )

    # Campos para notificación de documentos nuevos
    has_new_distributor_documents = fields.Boolean(
        string='Documentos Nuevos Distribuidor',
        compute='_compute_has_new_documents',
        store=False,
        help='Indica si hay documentos del distribuidor sin revisar'
    )

    distributor_documents_reviewed = fields.Boolean(
        string='Documentos Revisados',
        default=False,
        help='Marca si los documentos del distribuidor han sido revisados'
    )

    @api.depends('state')
    def _compute_picking_status(self) -> None:
        """Calcula el estado del albarán basado en el estado del pedido."""
        for order in self:
            if order.state == 'draft':
                order.picking_status = 'not_created'
            elif order.state == 'sent':
                order.picking_status = 'waiting'
            elif order.state == 'sale':
                order.picking_status = 'assigned'
            elif order.state == 'done':
                order.picking_status = 'done'
            elif order.state == 'cancel':
                order.picking_status = 'cancelled'
            else:
                order.picking_status = 'not_created'

    @api.depends('partner_id', 'partner_id.user_ids', 'state')
    def _compute_portal_visible(self) -> None:
        """
        Determina si el pedido debe ser visible en el portal.

        Visible si:
        - El cliente tiene usuario de portal
        - El pedido no está en estado 'cancel'
        """
        for order in self:
            order.portal_visible = (
                bool(order.partner_id.user_ids) and
                order.state != 'cancel'
            )

    @api.depends('state')
    def _compute_can_be_cancelled(self) -> None:
        """
        Determina si el pedido puede cancelarse desde el portal.

        Solo pedidos en estado 'draft' o 'sent' pueden cancelarse.
        """
        for order in self:
            order.can_be_cancelled = order.state in ('draft', 'sent')

    @api.depends('distributor_delivery_note_ids', 'distributor_invoice_ids', 
                 'distributor_label_ids', 'distributor_transport_invoice_ids',
                 'distributor_other_docs_ids')
    def _compute_distributor_document_count(self) -> None:
        """Cuenta total de documentos subidos por el distribuidor"""
        for order in self:
            order.distributor_document_count = (
                len(order.distributor_delivery_note_ids) +
                len(order.distributor_invoice_ids) +
                len(order.distributor_label_ids) +
                len(order.distributor_transport_invoice_ids) +
                len(order.distributor_other_docs_ids)
            )

    @api.depends('state', 'distributor_document_count', 'distributor_documents_reviewed')
    def _compute_has_new_documents(self) -> None:
        """
        Indica si hay documentos nuevos sin revisar.
        
        SOLO alerta si:
        - El pedido está confirmado (state in ['sale', 'done'])
        - Hay documentos subidos
        - No han sido revisados
        """
        for order in self:
            order.has_new_distributor_documents = (
                order.state in ['sale', 'done'] and
                order.distributor_document_count > 0 and
                not order.distributor_documents_reviewed
            )

    @api.model_create_multi
    def create(self, vals_list):
        """Override para generar access_token automáticamente y asegurar order_status."""
        for vals in vals_list:
            if 'access_token' not in vals or not vals.get('access_token'):
                vals['access_token'] = self._generate_access_token()
            # Asegurar que order_status tenga un valor por defecto
            if 'order_status' not in vals or not vals.get('order_status'):
                vals['order_status'] = 'new'
        return super().create(vals_list)

    @staticmethod
    def _generate_access_token():
        """Genera un token de acceso único y seguro."""
        return secrets.token_urlsafe(32)

    @api.model
    def _ensure_access_tokens(self):
        """
        Asegura que todos los pedidos tengan access_token.
        Llamado desde post_init_hook.
        """
        orders_without_token = self.search([
            ('access_token', '=', False),
            ('state', '!=', 'cancel'),
        ])
        if orders_without_token:
            _logger.info(f"Generando access_token para {len(orders_without_token)} pedidos...")
            for order in orders_without_token:
                order.access_token = self._generate_access_token()
            _logger.info(f"✓ Tokens generados para {len(orders_without_token)} pedidos")

    @api.model
    def _ensure_order_status_defaults(self):
        """Asegura que todos los pedidos tengan order_status definido."""
        orders_without_status = self.search([
            ('order_status', '=', False)
        ])
        if orders_without_status:
            orders_without_status.write({'order_status': 'new'})
            _logger.info(f"Actualizados {len(orders_without_status)} pedidos sin order_status")

    def validar_credito_antes_confirmar(self) -> bool:
        """
        Valida el crédito disponible antes de confirmar el pedido.

        Returns:
            True si la validación es exitosa

        Raises:
            ValidationError: Si no hay crédito suficiente
        """
        self.ensure_one()

        partner = self.partner_id.commercial_partner_id

        if not partner.is_distributor:
            # No es distribuidor, no validar crédito
            return True

        if partner.credit_limit <= 0:
            # Sin límite configurado, permitir
            _logger.info(f"Pedido {self.name}: distribuidor sin límite de crédito configurado")
            return True

        monto_pedido = self.amount_total

        if not partner.validar_credito_disponible(monto_pedido):
            raise ValidationError(
                _('Crédito insuficiente.\n\n'
                  'Límite de crédito: %(limit).2f\n'
                  'Crédito disponible: %(available).2f\n'
                  'Monto del pedido: %(amount).2f\n\n'
                  'Por favor, contacte con su gestor comercial.') % {
                    'limit': partner.credit_limit,
                    'available': partner.available_credit,
                    'amount': monto_pedido,
                }
            )

        _logger.info(
            f"Pedido {self.name} validado. "
            f"Crédito disponible: {partner.available_credit}, Monto: {monto_pedido}"
        )
        return True

    def action_confirm(self):
        """
        Override para validar crédito antes de confirmar.
        """
        for order in self:
            order.validar_credito_antes_confirmar()

        return super(SaleOrder, self).action_confirm()
    def action_cancel_from_portal(self) -> dict:
        """
        Cancela el pedido desde el portal.

        Returns:
            dict: Acción de redirección

        Raises:
            UserError: Si el pedido no puede cancelarse
        """
        self.ensure_one()

        if not self.can_be_cancelled:
            raise UserError(
                _('Este pedido no puede cancelarse. Estado actual: %s') %
                dict(self._fields['state'].selection).get(self.state)
            )

        self.action_cancel()

        _logger.info(f"Pedido {self.name} cancelado desde portal por usuario {self.env.user.name}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pedido Cancelado'),
                'message': _('El pedido %s ha sido cancelado correctamente.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_duplicate_order(self) -> int:
        """
        Duplica el pedido como borrador con precios actualizados.

        Returns:
            int: ID del nuevo pedido
        """
        self.ensure_one()

        # Copiar pedido
        new_order = self.copy({
            'state': 'draft',
            'date_order': fields.Datetime.now(),
            'is_recurring': False,
            'customer_delivery_note': False,
            'customer_delivery_note_filename': False,
            'access_token': self._generate_access_token(),
        })

        # Actualizar precios según tarifa actual
        new_order.order_line._compute_price_unit()
        new_order.order_line._compute_tax_id()

        _logger.info(f"Pedido {self.name} duplicado como {new_order.name}")

        return new_order.id

    def obtener_productos_sin_stock(self) -> list:
        """
        Obtiene lista de productos del pedido sin stock disponible.

        Returns:
            list: Lista de diccionarios con info de productos sin stock
        """
        self.ensure_one()

        productos_sin_stock = []

        for line in self.order_line:
            if not line.product_id or line.product_id.type != 'product':
                continue

            stock_disponible = line.product_id.with_context(
                warehouse=self.warehouse_id.id
            ).qty_available

            if stock_disponible < line.product_uom_qty:
                productos_sin_stock.append({
                    'producto': line.product_id.name,
                    'solicitado': line.product_uom_qty,
                    'disponible': stock_disponible,
                    'faltante': line.product_uom_qty - stock_disponible,
                })

        return productos_sin_stock

    def action_view_distributor_documents(self):
        """Acción mejorada para ver todos los documentos del distribuidor"""
        self.ensure_one()
        
        # Recopilar todos los IDs de attachments
        all_attachment_ids = (
            self.distributor_delivery_note_ids.ids +
            self.distributor_invoice_ids.ids +
            self.distributor_label_ids.ids +
            self.distributor_transport_invoice_ids.ids +
            self.distributor_other_docs_ids.ids
        )
        
        if not all_attachment_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sin Documentos'),
                    'message': _('No hay documentos del distribuidor para mostrar.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        return {
            'name': f'Documentos Distribuidor - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', all_attachment_ids)],
            'context': {
                'default_res_model': 'sale.order',
                'default_res_id': self.id,
                'create': False,
            },
            'target': 'new',
        }

    def action_mark_documents_reviewed(self):
        """Marca los documentos del distribuidor como revisados."""
        self.ensure_one()
        self.write({'distributor_documents_reviewed': True})
        
        _logger.info(
            f"Documentos del pedido {self.name} marcados como revisados "
            f"por usuario {self.env.user.login}"
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Documentos Marcados'),
                'message': _('Los documentos han sido marcados como revisados.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _ensure_computed_fields(self):
        """Asegura que todos los pedidos tengan campos computed inicializados."""
        try:
            orders_to_update = self.search([])
            for order in orders_to_update:
                # Forzar cálculo de campos computed
                _ = order.order_status
                _ = order.picking_status
                _ = order.distributor_document_count
                _ = order.has_new_distributor_documents
                
                # Asegurar valores por defecto
                if not order.order_status:
                    order.order_status = 'new'
                if not order.picking_status:
                    order.picking_status = 'not_created'
                    
            _logger.info(f"Campos computed actualizados en {len(orders_to_update)} pedidos")
        except Exception as e:
            _logger.warning(f"Error actualizando campos computed: {str(e)}")

    @api.constrains('customer_delivery_note')
    def _check_delivery_note_size(self) -> None:
        """Valida que el albarán no exceda 10MB."""
        for order in self:
            if order.customer_delivery_note:
                # Base64 aumenta ~33% el tamaño
                size_mb = len(order.customer_delivery_note) * 0.75 / (1024 * 1024)
                if size_mb > 10:
                    raise ValidationError(
                        _('El archivo del albarán no puede exceder 10 MB. Tamaño actual: %.2f MB') % size_mb
                    )

    def write(self, vals):
        """Override para crear notificaciones automáticas."""
        result = super().write(vals)
        
        # Notificar cambio de estado
        if 'state' in vals:
            for order in self:
                if order.partner_id.is_distributor:
                    self._notify_state_change(order, vals['state'])
        
        # Notificar cambio de order_status
        if 'order_status' in vals:
            for order in self:
                if order.partner_id.is_distributor:
                    self._notify_order_status_change(order, vals['order_status'])
        
        return result

    def _notify_state_change(self, order, new_state):
        """Crea notificación de cambio de estado."""
        state_messages = {
            'sale': {
                'title': f'Pedido {order.name} Confirmado',
                'message': f'Su pedido ha sido confirmado y está siendo procesado.',
                'type': 'success',
            },
            'done': {
                'title': f'Pedido {order.name} Completado',
                'message': f'Su pedido ha sido completado exitosamente.',
                'type': 'success',
            },
            'cancel': {
                'title': f'Pedido {order.name} Cancelado',
                'message': f'Su pedido ha sido cancelado.',
                'type': 'warning',
            },
        }
        
        if new_state in state_messages:
            msg = state_messages[new_state]
            self.env['portal.notification'].sudo().create_notification(
                partner_id=order.partner_id.id,
                title=msg['title'],
                message=msg['message'],
                notification_type=msg['type'],
                action_url=f'/mis-pedidos/{order.id}',
                related_model='sale.order',
                related_id=order.id,
            )

    def _notify_order_status_change(self, order, new_status):
        """Crea notificación de cambio de estado de pedido."""
        status_messages = {
            'warehouse': {
                'title': f'Pedido {order.name} en Almacén',
                'message': f'Su pedido está siendo preparado en el almacén.',
                'type': 'info',
            },
            'manufacturing': {
                'title': f'Pedido {order.name} en Fabricación',
                'message': f'Algunos productos de su pedido están en fabricación.',
                'type': 'info',
            },
            'prepared': {
                'title': f'Pedido {order.name} Preparado',
                'message': f'Su pedido está preparado y listo para envío.',
                'type': 'success',
            },
            'shipped': {
                'title': f'Pedido {order.name} Enviado',
                'message': f'Su pedido ha sido enviado y está en camino.',
                'type': 'success',
            },
        }
        
        if new_status in status_messages:
            msg = status_messages[new_status]
            self.env['portal.notification'].sudo().create_notification(
                partner_id=order.partner_id.id,
                title=msg['title'],
                message=msg['message'],
                notification_type=msg['type'],
                action_url=f'/mis-pedidos/{order.id}',
                related_model='sale.order',
                related_id=order.id,
            )
