# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campo para activar direcciones alternativas (distribuidores)
    use_alternative_delivery = fields.Boolean(
        string='Usar Dirección de Entrega Alternativa',
        default=False,
        help='Activar para seleccionar entre direcciones de entrega alternativas para distribuidores',
        compute='_compute_use_alternative_delivery',
        store=True
    )
    
    # Dirección de entrega seleccionada
    selected_delivery_partner_id = fields.Many2one(
        'res.partner',
        string='Dirección de Entrega Seleccionada',
        domain="[('parent_id', '=', partner_id), ('type', '=', 'delivery')]",
        help='Dirección de entrega seleccionada para este pedido'
    )
    
    # Campos inline para edición de dirección (adaptados a España)
    delivery_name = fields.Char(
        string='Nombre de Contacto de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_name',
        help='Nombre de la persona de contacto para la entrega'
    )
    
    delivery_street = fields.Char(
        string='Dirección de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street',
        help='Calle, avenida, plaza donde realizar la entrega'
    )
    
    delivery_street2 = fields.Char(
        string='Información Adicional de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_street2',
        help='Piso, puerta, polígono industrial, etc.'
    )
    
    delivery_city = fields.Char(
        string='Ciudad de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_city',
        help='Ciudad o localidad donde realizar la entrega'
    )
    
    delivery_state_id = fields.Many2one(
        'res.country.state',
        string='Provincia de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_state_id',
        help='Provincia donde realizar la entrega'
    )
    
    delivery_zip = fields.Char(
        string='Código Postal de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_zip',
        help='Código postal de la dirección de entrega'
    )
    
    delivery_country_id = fields.Many2one(
        'res.country',
        string='País de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_country_id',
        help='País donde realizar la entrega'
    )
    
    delivery_phone = fields.Char(
        string='Teléfono de Contacto de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_phone',
        help='Teléfono de contacto para coordinar la entrega'
    )
    
    delivery_email = fields.Char(
        string='Email de Contacto de Entrega',
        compute='_compute_delivery_fields',
        inverse='_inverse_delivery_email',
        help='Email de contacto para coordinar la entrega'
    )

    @api.depends('partner_id', 'partner_id.is_distributor')
    def _compute_use_alternative_delivery(self):
        """Auto-activar entrega alternativa para distribuidores"""
        for order in self:
            if order.partner_id:
                order.use_alternative_delivery = order.partner_id.is_distributor
            else:
                order.use_alternative_delivery = False

    @api.depends('partner_shipping_id', 'selected_delivery_partner_id', 'use_alternative_delivery')
    def _compute_delivery_fields(self):
        """Calcular campos de entrega desde el partner apropiado"""
        for order in self:
            # Determinar qué partner usar para la dirección
            if order.use_alternative_delivery and order.selected_delivery_partner_id:
                delivery_partner = order.selected_delivery_partner_id
            else:
                delivery_partner = order.partner_shipping_id
            
            if delivery_partner:
                order.delivery_name = delivery_partner.name or ''
                order.delivery_street = delivery_partner.street or ''
                order.delivery_street2 = delivery_partner.street2 or ''
                order.delivery_city = delivery_partner.city or ''
                order.delivery_state_id = delivery_partner.state_id.id if delivery_partner.state_id else False
                order.delivery_zip = delivery_partner.zip or ''
                order.delivery_country_id = delivery_partner.country_id.id if delivery_partner.country_id else False
                order.delivery_phone = delivery_partner.phone or ''
                order.delivery_email = delivery_partner.email or ''
            else:
                # Limpiar campos si no hay partner de entrega
                order._clear_delivery_fields()

    def _clear_delivery_fields(self):
        """Limpiar todos los campos de entrega"""
        self.delivery_name = ''
        self.delivery_street = ''
        self.delivery_street2 = ''
        self.delivery_city = ''
        self.delivery_state_id = False
        self.delivery_zip = ''
        self.delivery_country_id = False
        self.delivery_phone = ''
        self.delivery_email = ''

    # Métodos inverse para actualizar direcciones
    def _inverse_delivery_name(self):
        for order in self:
            if order.delivery_name:
                order._update_delivery_field('name', order.delivery_name)

    def _inverse_delivery_street(self):
        for order in self:
            order._update_delivery_field('street', order.delivery_street)

    def _inverse_delivery_street2(self):
        for order in self:
            order._update_delivery_field('street2', order.delivery_street2)

    def _inverse_delivery_city(self):
        for order in self:
            order._update_delivery_field('city', order.delivery_city)

    def _inverse_delivery_state_id(self):
        for order in self:
            state_id = order.delivery_state_id.id if order.delivery_state_id else False
            order._update_delivery_field('state_id', state_id)

    def _inverse_delivery_zip(self):
        for order in self:
            order._update_delivery_field('zip', order.delivery_zip)

    def _inverse_delivery_country_id(self):
        for order in self:
            country_id = order.delivery_country_id.id if order.delivery_country_id else False
            order._update_delivery_field('country_id', country_id)

    def _inverse_delivery_phone(self):
        for order in self:
            order._update_delivery_field('phone', order.delivery_phone)

    def _inverse_delivery_email(self):
        for order in self:
            order._update_delivery_field('email', order.delivery_email)

    def _update_delivery_field(self, field_name, value):
        """Actualizar un campo específico en el partner de entrega"""
        self.ensure_one()
        
        # Determinar qué partner actualizar
        if self.use_alternative_delivery and self.selected_delivery_partner_id:
            delivery_partner = self.selected_delivery_partner_id
        else:
            delivery_partner = self.partner_shipping_id
        
        if delivery_partner:
            old_value = getattr(delivery_partner, field_name, '')
            delivery_partner.write({field_name: value})
            
            # Log del cambio en chatter con más detalle
            field_labels = {
                'name': 'Nombre de contacto',
                'street': 'Dirección',
                'street2': 'Información adicional',
                'city': 'Ciudad',
                'state_id': 'Provincia',
                'zip': 'Código postal',
                'country_id': 'País',
                'phone': 'Teléfono',
                'email': 'Email',
            }
            
            field_label = field_labels.get(field_name, field_name)
            
            # Formatear valores para Many2one
            if field_name in ['state_id', 'country_id'] and value:
                model_name = 'res.country.state' if field_name == 'state_id' else 'res.country'
                record = self.env[model_name].browse(value)
                value_display = record.name if record.exists() else str(value)
            else:
                value_display = value or '(vacío)'
            
            self.message_post(
                body=_('📍 Dirección de entrega actualizada:<br/><strong>%s:</strong> %s') % (field_label, value_display),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )

    @api.onchange('selected_delivery_partner_id')
    def _onchange_selected_delivery_partner(self):
        """Actualizar partner_shipping_id cuando se selecciona dirección alternativa"""
        if self.use_alternative_delivery and self.selected_delivery_partner_id:
            self.partner_shipping_id = self.selected_delivery_partner_id

    @api.onchange('partner_id')
    def _onchange_partner_id_delivery(self):
        """Resetear selecciones de entrega cuando cambia el partner principal"""
        if self.partner_id:
            self.selected_delivery_partner_id = False
            self.use_alternative_delivery = self.partner_id.is_distribuidor if hasattr(self.partner_id, 'is_distributor') else False
            # Establecer país por defecto España
            if not self.delivery_country_id:
                spain = self.env.ref('base.es', raise_if_not_found=False)
                if spain:
                    self.delivery_country_id = spain
        else:
            self.use_alternative_delivery = False
            self.selected_delivery_partner_id = False

    def action_create_delivery_address_es(self):
        """Acción para crear nueva dirección de entrega desde campos inline"""
        self.ensure_one()
        
        if not self.partner_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Debe seleccionar un cliente primero'),
                    'type': 'warning',
                }
            }
        
        # Recopilar datos de los campos inline
        address_data = {
            'name': self.delivery_name or f"{self.partner_id.name} - Nueva Dirección",
            'parent_id': self.partner_id.id,
            'type': 'delivery',
            'street': self.delivery_street,
            'street2': self.delivery_street2,
            'city': self.delivery_city,
            'state_id': self.delivery_state_id.id if self.delivery_state_id else False,
            'zip': self.delivery_zip,
            'country_id': self.delivery_country_id.id if self.delivery_country_id else self.env.ref('base.es').id,
            'phone': self.delivery_phone,
            'email': self.delivery_email,
            'company_id': self.company_id.id,
            'is_company': False,
        }
        
        # Crear la nueva dirección
        new_address = self.env['res.partner'].create(address_data)
        
        # Asignar al pedido
        if self.use_alternative_delivery:
            self.selected_delivery_partner_id = new_address
        else:
            self.partner_shipping_id = new_address
        
        # Log en chatter
        self.message_post(
            body=_('🏭 Nueva dirección de entrega creada: <strong>%s</strong><br/>📍 %s') % (
                new_address.name, 
                new_address.contact_address
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Éxito!'),
                'message': _('Dirección de entrega creada correctamente: %s') % new_address.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def get_delivery_summary(self):
        """Obtener resumen de la dirección de entrega para reportes"""
        self.ensure_one()
        if self.use_alternative_delivery and self.selected_delivery_partner_id:
            partner = self.selected_delivery_partner_id
        else:
            partner = self.partner_shipping_id
        
        if not partner:
            return "Dirección de entrega no especificada"
        
        address_parts = [
            partner.name,
            partner.street,
            partner.street2,
            f"{partner.zip} {partner.city}" if partner.zip and partner.city else partner.city,
            partner.state_id.name if partner.state_id else None,
            partner.country_id.name if partner.country_id else None,
        ]
        
        return ", ".join(filter(None, address_parts))
