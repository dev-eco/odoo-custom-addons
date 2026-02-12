# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DeliveryAddress(models.Model):
    """Direcciones de entrega para distribuidores B2B."""
    
    _name = 'delivery.address'
    _description = 'Dirección de Entrega B2B'
    _order = 'is_default desc, name'
    _rec_name = 'name'

    # Campos básicos
    partner_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        required=True,
        ondelete='cascade',
        index=True,
        help='Distribuidor propietario de esta dirección'
    )
    
    name = fields.Char(
        string='Alias',
        required=True,
        help='Nombre identificativo de la dirección (ej: "Obra Madrid", "Almacén Norte")'
    )
    
    # Dirección
    street = fields.Char(
        string='Calle',
        required=True
    )
    
    street2 = fields.Char(
        string='Calle 2'
    )
    
    city = fields.Char(
        string='Ciudad',
        required=True
    )
    
    zip = fields.Char(
        string='Código Postal',
        required=True
    )
    
    state_id = fields.Many2one(
        'res.country.state',
        string='Provincia',
        domain="[('country_id', '=', country_id)]"
    )
    
    country_id = fields.Many2one(
        'res.country',
        string='País',
        required=True,
        default=lambda self: self.env.ref('base.es', raise_if_not_found=False)
    )
    
    # Contacto en destino
    contact_name = fields.Char(
        string='Nombre Contacto',
        help='Persona responsable de recibir la entrega'
    )
    
    contact_phone = fields.Char(
        string='Teléfono Contacto',
        help='Teléfono del responsable de recepción'
    )
    
    # Requisitos de entrega
    require_appointment = fields.Boolean(
        string='Requiere Cita Previa',
        default=False,
        help='Marcar si es necesario concertar cita para la entrega'
    )
    
    tail_lift_required = fields.Boolean(
        string='Requiere Camión con Pluma',
        default=False,
        help='Marcar si se necesita camión con pluma/elevador'
    )
    
    delivery_notes = fields.Text(
        string='Instrucciones de Entrega',
        help='Notas especiales para el transportista (horarios, accesos, etc.)'
    )
    
    # Control
    is_default = fields.Boolean(
        string='Dirección Predeterminada',
        default=False,
        help='Dirección que se selecciona por defecto en nuevos pedidos'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Desmarcar para desactivar la dirección sin eliminarla'
    )
    
    # Campos computados
    full_address = fields.Char(
        string='Dirección Completa',
        compute='_compute_full_address',
        store=False
    )

    @api.depends('street', 'street2', 'city', 'zip', 'state_id', 'country_id')
    def _compute_full_address(self) -> None:
        """Genera la dirección completa formateada."""
        for address in self:
            parts = []
            
            if address.street:
                parts.append(address.street)
            if address.street2:
                parts.append(address.street2)
            
            city_parts = []
            if address.zip:
                city_parts.append(address.zip)
            if address.city:
                city_parts.append(address.city)
            if city_parts:
                parts.append(' '.join(city_parts))
            
            if address.state_id:
                parts.append(address.state_id.name)
            if address.country_id:
                parts.append(address.country_id.name)
            
            address.full_address = ', '.join(parts) if parts else ''

    def name_get(self):
        """
        Override para controlar cómo se muestra el nombre en selects y vistas.
        Retorna solo el alias sin el nombre del partner.
        """
        result = []
        for address in self:
            name = address.name or _('Nueva Dirección')
            result.append((address.id, name))
        return result

    @api.constrains('is_default', 'partner_id')
    def _check_unique_default(self) -> None:
        """Asegura que solo haya una dirección predeterminada por distribuidor."""
        for address in self:
            if address.is_default:
                other_defaults = self.search([
                    ('partner_id', '=', address.partner_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', address.id),
                    ('active', '=', True)
                ])
                
                if other_defaults:
                    raise ValidationError(
                        _('Ya existe una dirección predeterminada para este distribuidor. '
                          'Desmarque la otra dirección primero.')
                    )

    @api.model
    def create(self, vals):
        """Override para manejar dirección predeterminada automáticamente."""
        # Si es la primera dirección del distribuidor, marcarla como predeterminada
        if 'partner_id' in vals and not vals.get('is_default'):
            existing_addresses = self.search([
                ('partner_id', '=', vals['partner_id']),
                ('active', '=', True)
            ], limit=1)
            
            if not existing_addresses:
                vals['is_default'] = True
                _logger.info(f"Primera dirección para partner {vals['partner_id']}, marcada como predeterminada")
        
        return super(DeliveryAddress, self).create(vals)

    def write(self, vals):
        """Override para manejar cambios en dirección predeterminada."""
        # Si se marca como predeterminada, desmarcar las demás
        if vals.get('is_default'):
            for address in self:
                other_defaults = self.search([
                    ('partner_id', '=', address.partner_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', address.id),
                    ('active', '=', True)
                ])
                
                if other_defaults:
                    other_defaults.write({'is_default': False})
                    _logger.info(f"Desmarcadas {len(other_defaults)} direcciones predeterminadas para partner {address.partner_id.name}")
        
        return super(DeliveryAddress, self).write(vals)

    def action_set_default(self) -> dict:
        """Marca esta dirección como predeterminada."""
        self.ensure_one()
        
        if self.is_default:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Ya es Predeterminada'),
                    'message': _('Esta dirección ya está marcada como predeterminada.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        self.write({'is_default': True})
        
        _logger.info(f"Dirección {self.name} marcada como predeterminada para {self.partner_id.name}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dirección Predeterminada'),
                'message': _('La dirección "%s" se ha marcado como predeterminada.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_archive(self) -> dict:
        """Desactiva la dirección (soft delete)."""
        self.ensure_one()
        
        if self.is_default:
            # Buscar otra dirección activa para marcarla como predeterminada
            other_address = self.search([
                ('partner_id', '=', self.partner_id.id),
                ('id', '!=', self.id),
                ('active', '=', True)
            ], limit=1)
            
            if other_address:
                other_address.write({'is_default': True})
                _logger.info(f"Dirección {other_address.name} marcada como predeterminada al archivar {self.name}")
        
        self.write({'active': False})
        
        _logger.info(f"Dirección {self.name} archivada para {self.partner_id.name}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dirección Desactivada'),
                'message': _('La dirección "%s" ha sido desactivada.') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def obtener_info_completa(self) -> dict:
        """
        Obtiene toda la información de la dirección en formato diccionario.
        
        Returns:
            dict: Información completa de la dirección
        """
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.name,
            'full_address': self.full_address,
            'street': self.street,
            'street2': self.street2 or '',
            'city': self.city,
            'zip': self.zip,
            'state': self.state_id.name if self.state_id else '',
            'country': self.country_id.name if self.country_id else '',
            'contact_name': self.contact_name or '',
            'contact_phone': self.contact_phone or '',
            'require_appointment': self.require_appointment,
            'tail_lift_required': self.tail_lift_required,
            'delivery_notes': self.delivery_notes or '',
            'is_default': self.is_default,
        }
