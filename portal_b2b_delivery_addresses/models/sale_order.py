# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Extensión de pedido de venta para direcciones de entrega B2B."""
    
    _inherit = 'sale.order'

    delivery_address_id = fields.Many2one(
        'delivery.address',
        string='Dirección de Entrega B2B',
        domain="[('partner_id', '=', partner_id), ('active', '=', True)]",
        help='Dirección de entrega específica del distribuidor'
    )
    
    delivery_address_display = fields.Char(
        string='Dirección de Entrega',
        compute='_compute_delivery_address_display',
        store=False,
        help='Dirección de entrega formateada para visualización'
    )

    distributor_label_id = fields.Many2one(
        'distributor.label',
        string='Etiqueta Cliente Final',
        domain="[('partner_id', '=', partner_id), ('active', '=', True)]",
        help='Etiqueta del cliente final del distribuidor'
    )
    
    customer_delivery_reference = fields.Char(
        string='Referencia Albarán Cliente',
        help='Número de albarán del cliente final del distribuidor'
    )
    
    hide_company_info_on_report = fields.Boolean(
        string='Ocultar Info Empresa en Reporte',
        default=False,
        help='No mostrar información de nuestra empresa en PDF'
    )

    # Archivos adjuntos del distribuidor
    customer_delivery_note_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_customer_delivery_note_rel',
        'order_id',
        'attachment_id',
        string='Albaranes Cliente Final',
        help='Albaranes/documentos del cliente final del distribuidor'
    )
    
    customer_label_ids = fields.Many2many(
        'ir.attachment',
        'sale_order_customer_label_rel',
        'order_id',
        'attachment_id',
        string='Etiquetas Cliente Final',
        help='Etiquetas personalizadas del cliente final'
    )
    
    # Información adicional del distribuidor
    distributor_notes = fields.Text(
        string='Notas del Distribuidor',
        help='Notas internas del distribuidor sobre este pedido'
    )
    
    final_customer_name = fields.Char(
        string='Nombre Cliente Final',
        compute='_compute_final_customer_info',
        store=True,
        default='',
        help='Nombre del cliente final (del distribuidor)'
    )
    
    final_customer_reference = fields.Char(
        string='Referencia Cliente Final',
        compute='_compute_final_customer_info',
        store=True,
        default='',
        help='Referencia del cliente final'
    )

    @api.depends('distributor_label_id', 'distributor_label_id.customer_name', 
                 'distributor_label_id.customer_reference', 'customer_delivery_reference')
    def _compute_final_customer_info(self) -> None:
        """Obtiene información del cliente final desde la etiqueta."""
        for order in self:
            try:
                if order.distributor_label_id and order.distributor_label_id.customer_name:
                    order.final_customer_name = order.distributor_label_id.customer_name or ''
                    order.final_customer_reference = (
                        order.distributor_label_id.customer_reference or 
                        order.customer_delivery_reference or ''
                    )
                else:
                    order.final_customer_name = ''
                    order.final_customer_reference = order.customer_delivery_reference or ''
            except Exception as e:
                _logger.warning(f"Error calculando cliente final para pedido {order.id}: {str(e)}")
                order.final_customer_name = ''
                order.final_customer_reference = ''


    @api.depends('delivery_address_id', 'delivery_address_id.full_address')
    def _compute_delivery_address_display(self) -> None:
        """Genera la visualización de la dirección de entrega."""
        for order in self:
            if order.delivery_address_id:
                order.delivery_address_display = order.delivery_address_id.full_address
            else:
                order.delivery_address_display = ''

    @api.onchange('partner_id')
    def _onchange_partner_id_delivery_address(self) -> None:
        """Al cambiar el cliente, selecciona su dirección predeterminada."""
        if self.partner_id:
            default_address = self.env['delivery.address'].search([
                ('partner_id', '=', self.partner_id.id),
                ('is_default', '=', True),
                ('active', '=', True)
            ], limit=1)
            
            if default_address:
                self.delivery_address_id = default_address
                _logger.debug(f"Dirección predeterminada asignada: {default_address.name}")
            else:
                self.delivery_address_id = False
                self.partner_shipping_id = self.partner_id
                _logger.debug("No se encontró dirección predeterminada")
        else:
            self.delivery_address_id = False
            self.partner_shipping_id = False

    @api.onchange('delivery_address_id')
    def _onchange_delivery_address_id(self) -> None:
        """Al cambiar la dirección de entrega, sincronizar inmediatamente con partner_shipping_id."""
        if self.delivery_address_id:
            _logger.debug(f"Dirección de entrega cambiada a: {self.delivery_address_id.name}")
            
            # Sincronizar INMEDIATAMENTE con partner_shipping_id
            self._sync_shipping_address_from_delivery_address()
            
            # Si la dirección tiene requisitos especiales, añadir notas automáticas
            if self.delivery_address_id.require_appointment or self.delivery_address_id.tail_lift_required:
                notes = []
                if self.delivery_address_id.require_appointment:
                    notes.append("⚠️ REQUIERE CITA PREVIA")
                if self.delivery_address_id.tail_lift_required:
                    notes.append("⚠️ REQUIERE CAMIÓN CON PLUMA")
                
                if self.delivery_address_id.delivery_notes:
                    notes.append(f"Notas: {self.delivery_address_id.delivery_notes}")
                
                # Añadir a las notas del pedido si no están ya
                current_note = self.note or ''
                for note in notes:
                    if note not in current_note:
                        self.note = f"{current_note}\n{note}".strip()
        else:
            # Si no hay dirección B2B, usar el distribuidor
            if self.partner_id:
                self.partner_shipping_id = self.partner_id

    @api.model
    def _ensure_final_customer_fields(self):
        """Asegura que todos los pedidos tengan campos de cliente final inicializados."""
        try:
            orders_without_fields = self.search([
                '|',
                ('final_customer_name', '=', False),
                ('final_customer_reference', '=', False)
            ])
            
            for order in orders_without_fields:
                order._compute_final_customer_info()
            
            if orders_without_fields:
                _logger.info(f"Inicializados campos cliente final en {len(orders_without_fields)} pedidos")
        except Exception as e:
            _logger.warning(f"Error inicializando campos cliente final: {str(e)}")

    def _sync_shipping_address_from_delivery_address(self):
        """
        Sincroniza delivery_address_id con partner_shipping_id.
        
        Crea o actualiza un contacto res.partner de tipo 'delivery' 
        basado en los datos de delivery.address.
        """
        self.ensure_one()
        
        if not self.delivery_address_id:
            return
        
        delivery_addr = self.delivery_address_id
        
        # Buscar si ya existe un contacto con esta dirección exacta
        # Buscar por combinación única: nombre + dirección + ciudad + CP + parent_id
        existing_contact = self.env['res.partner'].search([
            ('name', '=', delivery_addr.name),
            ('street', '=', delivery_addr.street),
            ('city', '=', delivery_addr.city),
            ('zip', '=', delivery_addr.zip),
            ('type', '=', 'delivery'),
            ('parent_id', '=', self.partner_id.id),  # Hijo del distribuidor
        ], limit=1)
        
        # Preparar valores del contacto de entrega
        contact_vals = {
            'parent_id': self.partner_id.id,  # Hijo del distribuidor
            'type': 'delivery',
            'name': delivery_addr.name,  # Alias de la dirección
            'street': delivery_addr.street,
            'street2': delivery_addr.street2 or False,
            'city': delivery_addr.city,
            'zip': delivery_addr.zip,
            'state_id': delivery_addr.state_id.id if delivery_addr.state_id else False,
            'country_id': delivery_addr.country_id.id,
            'phone': delivery_addr.contact_phone or '',
            'email': '',  # Sin email para evitar conflictos
            'active': True,
            'is_company': False,
            'company_type': 'person',
            # Marcar como dirección de entrega B2B
            'comment': f'Dirección de entrega B2B: {delivery_addr.name}',
        }
        
        if existing_contact:
            # Actualizar contacto existente
            existing_contact.sudo().write(contact_vals)
            self.partner_shipping_id = existing_contact
            _logger.info(f"Contacto de entrega actualizado: {existing_contact.name}")
        else:
            # Crear nuevo contacto de entrega
            new_contact = self.env['res.partner'].sudo().create(contact_vals)
            self.partner_shipping_id = new_contact
            _logger.info(f"Nuevo contacto de entrega creado: {new_contact.name}")

    def _get_shipping_address_display(self):
        """
        Obtiene el nombre de visualización de la dirección de envío.
        
        Si hay delivery_address_id, usa solo el alias sin el nombre del distribuidor.
        """
        self.ensure_one()
        
        if self.delivery_address_id:
            # Usar solo el nombre del delivery_address (alias)
            return self.delivery_address_id.name
        elif self.partner_shipping_id:
            # Usar el nombre estándar del partner_shipping_id
            return self.partner_shipping_id.display_name
        else:
            return ''

    def write(self, vals):
        """Override para sincronizar direcciones al actualizar."""
        result = super().write(vals)
        
        # Si se modificó delivery_address_id, sincronizar INMEDIATAMENTE
        if 'delivery_address_id' in vals:
            for order in self:
                if order.delivery_address_id:
                    # Forzar sincronización
                    order._sync_shipping_address_from_delivery_address()
                else:
                    # Si se borra la dirección B2B, volver al distribuidor
                    if order.partner_id:
                        order.partner_shipping_id = order.partner_id
        
        return result

    def _get_shipping_address_display(self):
        """
        Obtiene el nombre de visualización de la dirección de envío.
        
        Si hay delivery_address_id, usa solo el alias sin el nombre del distribuidor.
        """
        self.ensure_one()
        
        if self.delivery_address_id:
            # Usar solo el nombre del delivery_address (alias)
            return self.delivery_address_id.name
        elif self.partner_shipping_id:
            # Usar el nombre estándar del partner_shipping_id
            return self.partner_shipping_id.display_name
        else:
            return ''

    @api.onchange('distributor_label_id')
    def _onchange_distributor_label_id(self) -> None:
        """Al cambiar la etiqueta, actualizar configuración de impresión."""
        if self.distributor_label_id:
            self.hide_company_info_on_report = self.distributor_label_id.hide_company_info
            _logger.debug(
                f"Etiqueta {self.distributor_label_id.name} asignada. "
                f"Ocultar info empresa: {self.hide_company_info_on_report}"
            )

    @api.model
    def _cron_sync_delivery_addresses(self):
        """
        Cron job para sincronizar direcciones de entrega en pedidos existentes.
        
        Ejecutar manualmente si hay pedidos antiguos sin sincronizar:
        self.env['sale.order']._cron_sync_delivery_addresses()
        """
        orders_to_sync = self.search([
            ('delivery_address_id', '!=', False),
            ('partner_shipping_id', '=', False),
        ])
        
        for order in orders_to_sync:
            try:
                order._sync_shipping_address_from_delivery_address()
                _logger.info(f"Sincronizada dirección para pedido {order.name}")
            except Exception as e:
                _logger.error(f"Error sincronizando pedido {order.name}: {str(e)}")
        
        _logger.info(f"Sincronizadas {len(orders_to_sync)} direcciones de entrega")

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
