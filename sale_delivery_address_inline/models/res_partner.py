# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo principal para marcar distribuidores
    is_distributor = fields.Boolean(
        string='Es Distribuidor',
        default=False,
        tracking=True,
        help="Marque esta casilla si este cliente es un distribuidor con múltiples direcciones de entrega"
    )
    
    # Contador de direcciones de entrega
    delivery_address_count = fields.Integer(
        string='Número de direcciones de entrega',
        compute='_compute_delivery_address_count',
        store=True
    )
    
    # Relación inversa para fácil acceso
    delivery_address_ids = fields.One2many(
        'res.partner',
        compute='_compute_delivery_address_ids',
        string='Direcciones de Entrega'
    )
    
    # Campos adicionales para distribuidores
    distributor_type = fields.Selection([
        ('local', 'Local Distributor'),
        ('regional', 'Regional Distributor'),
        ('national', 'National Distributor'),
        ('international', 'International Distributor')
    ], string='Tipo de Distribuidor', tracking=True)
    
    delivery_schedule_notes = fields.Text(
        string='Notas de Horarios de Entrega',
        help="Instrucciones o restricciones especiales para entregas (horarios, etc.)"
    )
    
    # Información logística
    truck_access = fields.Selection([
        ('large', 'Large Truck Access (+12m)'),
        ('medium', 'Medium Truck Access (7-12m)'),
        ('small', 'Van/Small Truck Only (<7m)'),
        ('manual', 'Manual Unloading Only')
    ], string='Tipo de Acceso para Vehículos', tracking=True)
    
    loading_equipment = fields.Selection([
        ('crane', 'Crane Available'),
        ('forklift', 'Forklift'),
        ('pallet', 'Pallet Jack'),
        ('manual', 'Manual Unloading Only')
    ], string='Equipo de Descarga Disponible', tracking=True)

    @api.constrains('is_distributor', 'parent_id')
    def _check_distributor_constraints(self):
        """Validar reglas para distribuidores"""
        for partner in self:
            if partner.is_distributor and partner.parent_id:
                raise ValidationError(_("Un contacto no puede marcarse como distribuidor si tiene una empresa padre"))

    @api.depends('child_ids', 'child_ids.type')
    def _compute_delivery_address_count(self):
        """Calcula el número de direcciones de entrega"""
        for partner in self:
            partner.delivery_address_count = len(partner.child_ids.filtered(lambda r: r.type == 'delivery'))

    @api.depends('child_ids', 'child_ids.type')
    def _compute_delivery_address_ids(self):
        """Devuelve las direcciones de entrega asociadas"""
        for partner in self:
            partner.delivery_address_ids = partner.child_ids.filtered(lambda r: r.type == 'delivery')

    def get_delivery_addresses_for_selection(self):
        """Devuelve las direcciones de entrega en formato para selector"""
        self.ensure_one()
        
        # Si es distribuidor, obtener todas las direcciones de entrega
        if self.is_distribuidor:
            delivery_addresses = self.child_ids.filtered(lambda r: r.type == 'delivery')
            
            # Formato para el selector: [(id, nombre_completo)]
            result = [(self.id, _("%s (Dirección Principal)") % self.name)]
            
            for addr in delivery_addresses:
                addr_display = "%s (%s, %s)" % (
                    addr.name,
                    addr.city or _('Sin ciudad'),
                    addr.state_id.name if addr.state_id else (addr.country_id.name if addr.country_id else _('Sin ubicación'))
                )
                result.append((addr.id, addr_display))
                
            return result
        
        # Si no es distribuidor, solo devolver la dirección principal
        return [(self.id, self.name)]

    def action_view_delivery_addresses(self):
        """Acción para ver/gestionar direcciones de entrega"""
        self.ensure_one()
        
        action = {
            'name': _("Direcciones de Entrega para %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'kanban,tree,form',
            'domain': [('parent_id', '=', self.id), ('type', '=', 'delivery')],
            'context': {
                'default_parent_id': self.id,
                'default_type': 'delivery',
                'default_company_id': self.company_id.id,
            }
        }
        
        return action

    def action_create_delivery_address(self):
        """Acción para crear una nueva dirección de entrega rápidamente"""
        self.ensure_one()
        
        # Preparar contexto para la nueva dirección
        ctx = {
            'default_parent_id': self.id,
            'default_type': 'delivery',
            'default_name': _("Nueva Dirección para %s", self.name),
            'default_street': self.street,
            'default_city': self.city,
            'default_zip': self.zip,
            'default_state_id': self.state_id.id,
            'default_country_id': self.country_id.id,
            'default_company_id': self.company_id.id,
        }
        
        # Crear formulario de nueva dirección
        return {
            'name': _('Nueva Dirección de Entrega'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    @api.onchange('is_distributor')
    def _onchange_is_distributor(self):
        """Al marcar como distribuidor, ajustar opciones relacionadas"""
        if self.is_distributor:
            # Si no tiene tipo de distribuidor, establecer uno predeterminado
            if not self.distributor_type:
                self.distributor_type = 'regional'
