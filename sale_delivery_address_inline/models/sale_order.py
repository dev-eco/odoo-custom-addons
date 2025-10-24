# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Flag para indicar si el cliente es distribuidor (computed)
    is_distributor_customer = fields.Boolean(
        string='Cliente Distribuidor',
        compute='_compute_is_distributor_customer',
        store=True,
        help="Indica si el cliente es un distribuidor con múltiples direcciones de entrega"
    )

    # Flag para usar dirección alternativa de entrega
    use_alternative_delivery = fields.Boolean(
        string='Usar Dirección Alternativa',
        default=False,
        tracking=True,
        help="Activa esta opción para usar una dirección de entrega distinta a la predeterminada"
    )

    # Selector de dirección de entrega para distribuidores
    selected_delivery_partner_id = fields.Many2one(
        'res.partner',
        string='Dirección de Entrega Seleccionada',
        domain="[('parent_id', '=', partner_id), ('type', '=', 'delivery')]",
        tracking=True
    )

    # Campos de dirección inline con mejor diseño

    delivery_street = fields.Char(
        string='Dirección de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street',
        tracking=True
    )

    delivery_street2 = fields.Char(
        string='Información Adicional',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street2',
        tracking=True
    )

    delivery_city = fields.Char(
        string='Ciudad de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_city',
        tracking=True
    )

    delivery_zip = fields.Char(
        string='Código Postal',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_zip',
        tracking=True
    )

    delivery_state_id = fields.Many2one(
        'res.country.state',
        string='Provincia/Estado',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_state',
        tracking=True
    )

    delivery_country_id = fields.Many2one(
        'res.country',
        string='País',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_country',
        tracking=True
    )

    delivery_phone = fields.Char(
        string='Teléfono de Contacto',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_phone',
        tracking=True
    )

    delivery_email = fields.Char(
        string='Email de Contacto',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_email',
        tracking=True
    )

    # Flag para indicar si se modificó la dirección (para mostrar advertencias)
    delivery_address_modified = fields.Boolean(
        string='Dirección Modificada',
        default=False,
        copy=False,
        help="Indica si la dirección de entrega ha sido modificada después de confirmar el pedido"
    )

    @api.depends('partner_id', 'partner_id.is_distributor')
    def _compute_is_distributor_customer(self):
        """Determina si el cliente es distribuidor"""
        for order in self:
            order.is_distributor_customer = order.partner_id.is_distributor if order.partner_id else False

    @api.onchange('partner_id')
    def _onchange_partner_id_delivery(self):
        """Al cambiar el cliente, resetea los campos de entrega y distribuidor"""
        if self.partner_id:
            self.use_alternative_delivery = False
            self.selected_delivery_partner_id = False
            # Si es distribuidor, establece la dirección de entrega como la primera disponible
            if self.is_distributor_customer and self.partner_id.child_ids.filtered(lambda r: r.type == 'delivery'):
                self.partner_shipping_id = self.partner_id.child_ids.filtered(lambda r: r.type == 'delivery')[0]
            else:
                self.partner_shipping_id = self.partner_id

    @api.onchange('use_alternative_delivery')
    def _onchange_use_alternative_delivery(self):
        """Gestiona el cambio de opción de usar dirección alternativa"""
        if not self.use_alternative_delivery:
            # Si se desactiva, volvemos a la dirección principal
            self.selected_delivery_partner_id = False
            self.partner_shipping_id = self.partner_id
        else:
            # Si se activa y hay direcciones disponibles, selecciona la primera
            delivery_addresses = self.partner_id.child_ids.filtered(lambda r: r.type == 'delivery')
            if delivery_addresses:
                self.selected_delivery_partner_id = delivery_addresses[0]
                self.partner_shipping_id = delivery_addresses[0]
            else:
                # Si no hay direcciones, crea una nueva plantilla vacía
                self.partner_shipping_id = self.partner_id

    @api.onchange('selected_delivery_partner_id')
    def _onchange_selected_delivery_partner_id(self):
        """Al seleccionar una dirección de la lista, actualiza partner_shipping_id"""
        if self.selected_delivery_partner_id:
            self.partner_shipping_id = self.selected_delivery_partner_id
        elif self.use_alternative_delivery and not self.selected_delivery_partner_id:
            # Si está marcado usar alternativa pero no hay selección, volver al partner principal
            self.partner_shipping_id = self.partner_id

    @api.depends('partner_shipping_id', 'selected_delivery_partner_id')
    def _compute_delivery_fields(self):
        """Calcula los campos de dirección de entrega desde la dirección seleccionada"""
        for order in self:
            if order.partner_shipping_id:
                order.delivery_street = order.partner_shipping_id.street or ''
                order.delivery_street2 = order.partner_shipping_id.street2 or ''
                order.delivery_city = order.partner_shipping_id.city or ''
                order.delivery_zip = order.partner_shipping_id.zip or ''
                order.delivery_state_id = order.partner_shipping_id.state_id.id if order.partner_shipping_id.state_id else False
                order.delivery_country_id = order.partner_shipping_id.country_id.id if order.partner_shipping_id.country_id else False
                order.delivery_phone = order.partner_shipping_id.phone or ''
                order.delivery_email = order.partner_shipping_id.email or ''
            else:
                # Valores por defecto si no hay dirección
                order.delivery_street = ''
                order.delivery_street2 = ''
                order.delivery_city = ''
                order.delivery_zip = ''
                order.delivery_state_id = False
                order.delivery_country_id = False
                order.delivery_phone = ''
                order.delivery_email = ''

    # Métodos inversos mejorados con registro de cambios y validación
    def _inverse_delivery_name(self):
        for order in self:
            if order.partner_shipping_id and order.delivery_name:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.name
                new_value = order.delivery_name
                if old_value != new_value:
                    order.partner_shipping_id.name = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Nombre de contacto', old_value, new_value)

    def _inverse_delivery_street(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.street
                new_value = order.delivery_street
                if old_value != new_value:
                    order.partner_shipping_id.street = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Dirección', old_value, new_value)

    def _inverse_delivery_street2(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.street2
                new_value = order.delivery_street2
                if old_value != new_value:
                    order.partner_shipping_id.street2 = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Información adicional', old_value, new_value)

    def _inverse_delivery_city(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.city
                new_value = order.delivery_city
                if old_value != new_value:
                    order.partner_shipping_id.city = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Ciudad', old_value, new_value)

    def _inverse_delivery_zip(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.zip
                new_value = order.delivery_zip
                if old_value != new_value:
                    order.partner_shipping_id.zip = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Código postal', old_value, new_value)

    def _inverse_delivery_state(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.state_id.id
                new_value = order.delivery_state_id.id if order.delivery_state_id else False
                if old_value != new_value:
                    order.partner_shipping_id.state_id = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        old_name = order.partner_shipping_id.state_id.name if order.partner_shipping_id.state_id else ''
                        new_name = order.delivery_state_id.name if order.delivery_state_id else ''
                        self._log_delivery_field_change('Provincia/Estado', old_name, new_name)

    def _inverse_delivery_country(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.country_id.id
                new_value = order.delivery_country_id.id if order.delivery_country_id else False
                if old_value != new_value:
                    order.partner_shipping_id.country_id = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        old_name = order.partner_shipping_id.country_id.name if order.partner_shipping_id.country_id else ''
                        new_name = order.delivery_country_id.name if order.delivery_country_id else ''
                        self._log_delivery_field_change('País', old_name, new_name)

    def _inverse_delivery_phone(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.phone
                new_value = order.delivery_phone
                if old_value != new_value:
                    order.partner_shipping_id.phone = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Teléfono', old_value, new_value)

    def _inverse_delivery_email(self):
        for order in self:
            if order.partner_shipping_id:
                # Verificar permisos para pedidos confirmados
                if order.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
                    raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

                old_value = order.partner_shipping_id.email
                new_value = order.delivery_email
                if old_value != new_value:
                    order.partner_shipping_id.email = new_value
                    if order.state != 'draft':
                        order.delivery_address_modified = True
                        self._log_delivery_field_change('Email', old_value, new_value)

    def _log_delivery_field_change(self, field_name, old_value, new_value):
        """Registra los cambios de campos de dirección en el chatter"""
        for order in self:
            if old_value != new_value:
                message = _(
                    "📍 Dirección de entrega actualizada:<br/>"
                    "<strong>%s:</strong> %s → %s"
                ) % (field_name, old_value or _("Sin valor"), new_value or _("Sin valor"))
                order.message_post(body=message)

    def _create_new_delivery_address(self, address_data):
        """Crea una nueva dirección de entrega y la vincula al pedido"""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Debe seleccionar un cliente primero"))

        # Validar datos mínimos
        if not address_data.get('name') or not address_data.get('street'):
            raise UserError(_("El nombre y la dirección son obligatorios"))

        # Crear dirección de entrega
        vals = {
            'name': address_data.get('name'),
            'type': 'delivery',
            'parent_id': self.partner_id.id,
            'street': address_data.get('street'),
            'street2': address_data.get('street2', ''),
            'city': address_data.get('city', ''),
            'zip': address_data.get('zip', ''),
            'state_id': address_data.get('state_id', False),
            'country_id': address_data.get('country_id', self.partner_id.country_id.id or False),
            'phone': address_data.get('phone', ''),
            'email': address_data.get('email', ''),
            'comment': _("Creada desde pedido %s", self.name),
            'company_id': self.company_id.id,
        }

        new_address = self.env['res.partner'].with_context(tracking_disable=True).create(vals)

        # Actualizar el pedido
        self.partner_shipping_id = new_address.id
        self.selected_delivery_partner_id = new_address.id

        # Registrar en el historial
        address_summary = "%s, %s, %s" % (
            new_address.street or '',
            new_address.city or '',
            new_address.country_id.name if new_address.country_id else ''
        )

        self.message_post(
            body=_("🏭 Nueva dirección de entrega creada: <strong>%s</strong><br/>📍 %s") % (
                new_address.name, address_summary
            ),
            subtype_xmlid="mail.mt_note"
        )

        return new_address

    def action_create_delivery_address(self):
        """Acción para crear una nueva dirección de entrega desde el formulario"""
        self.ensure_one()

        # Verificar permisos para pedidos confirmados
        if self.state in ['sale', 'done'] and not self.env.user.has_group('sales_team.group_sale_manager'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Acceso Denegado'),
                    'message': _('Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados'),
                    'type': 'danger',
                }
            }

        if not self.partner_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Debe seleccionar un cliente primero'),
                    'type': 'danger',
                }
            }

        # Preparar datos de la dirección
        address_data = {
            'name': self.delivery_name or _('Dirección de entrega para %s', self.name),
            'street': self.delivery_street or '',
            'street2': self.delivery_street2 or '',
            'city': self.delivery_city or '',
            'zip': self.delivery_zip or '',
            'state_id': self.delivery_state_id.id if self.delivery_state_id else False,
            'country_id': self.delivery_country_id.id if self.delivery_country_id else False,
            'phone': self.delivery_phone or '',
            'email': self.delivery_email or '',
        }

        try:
            new_address = self._create_new_delivery_address(address_data)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('¡Éxito!'),
                    'message': _('Dirección de entrega creada correctamente: %s', new_address.name),
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def write(self, vals):
        """Sobreescribir write para gestionar cambios en direcciones después de confirmación"""
        # Verificar permisos para modificar direcciones en pedidos confirmados
        if any(order.state in ['sale', 'done'] for order in self) and not self.env.user.has_group('sales_team.group_sale_manager'):
            delivery_fields = [
                'delivery_name', 'delivery_street', 'delivery_street2', 'delivery_city',
                'delivery_zip', 'delivery_state_id', 'delivery_country_id', 'delivery_phone',
                'delivery_email', 'selected_delivery_partner_id', 'partner_shipping_id'
            ]
            if any(field in vals for field in delivery_fields):
                raise AccessError(_("Solo los gerentes de ventas pueden modificar direcciones en pedidos confirmados"))

        res = super(SaleOrder, self).write(vals)

        # Si el pedido está confirmado y se modifica la dirección, notificar
        for order in self:
            if order.state in ['sale', 'done'] and order.delivery_address_modified:
                # Notificar al equipo de ventas
                user_ids = order.team_id.member_ids.ids if order.team_id else []
                if order.user_id and order.user_id.id not in user_ids:
                    user_ids.append(order.user_id.id)

                if user_ids:
                    order.activity_schedule(
                        'mail.mail_activity_data_warning',
                        summary=_("Dirección de entrega modificada"),
                        note=_(
                            "La dirección de entrega de este pedido ha sido modificada "
                            "después de su confirmación. Por favor, verifica si esto "
                            "afecta a la logística o al envío."
                        ),
                        user_id=user_ids[0]
                    )

        return res
