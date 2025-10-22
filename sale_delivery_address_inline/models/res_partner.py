# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campo principal para identificar distribuidores
    is_distributor = fields.Boolean(
        string='Es Distribuidor',
        default=False,
        help='Marque esta casilla si este cliente es un distribuidor con múltiples direcciones de entrega'
    )
    
    # Campos específicos para distribuidores en España
    distributor_type = fields.Selection([
        ('regional', 'Distribuidor Regional'),
        ('local', 'Distribuidor Local'),
        ('nacional', 'Distribuidor Nacional'),
        ('internacional', 'Distribuidor Internacional'),
    ], string='Tipo de Distribuidor', help='Tipo de distribuidor según su alcance geográfico')
    
    # Contador de direcciones de entrega
    delivery_address_count = fields.Integer(
        string='Número de Direcciones de Entrega',
        compute='_compute_delivery_address_count',
        help='Número total de direcciones de entrega asociadas'
    )
    
    # Direcciones de entrega relacionadas
    delivery_address_ids = fields.One2many(
        'res.partner',
        'parent_id',
        domain=[('type', '=', 'delivery')],
        string='Direcciones de Entrega',
        help='Direcciones de entrega asociadas a este distribuidor'
    )
    
    # Campos adicionales para gestión de losas
    losa_preferences = fields.Text(
        string='Preferencias de Productos de Losa',
        help='Preferencias específicas del cliente sobre tipos de losas, colores, tamaños, etc.'
    )
    
    delivery_schedule_notes = fields.Text(
        string='Notas de Horarios de Entrega',
        help='Información sobre horarios preferidos, restricciones de acceso, etc.'
    )
    
    installation_capability = fields.Boolean(
        string='Capacidad de Instalación Propia',
        help='Indica si el cliente/distribuidor tiene capacidad de instalación propia'
    )
    
    # Información logística específica para España
    truck_access = fields.Selection([
        ('camion_grande', 'Acceso para Camión Grande (+12m)'),
        ('camion_mediano', 'Acceso para Camión Mediano (7-12m)'),
        ('furgoneta', 'Solo Furgoneta/Camión Pequeño (<7m)'),
        ('manual', 'Solo Descarga Manual'),
    ], string='Tipo de Acceso para Vehículos', help='Tipo de vehículo que puede acceder para descarga')
    
    loading_equipment = fields.Selection([
        ('grua', 'Grúa Disponible'),
        ('carretilla', 'Carretilla Elevadora'),
        ('transpaleta', 'Transpaleta'),
        ('manual', 'Solo Descarga Manual'),
    ], string='Equipo de Descarga Disponible', help='Equipamiento disponible en destino para descarga')

    @api.depends('child_ids')
    def _compute_delivery_address_count(self):
        """Calcular el número de direcciones de entrega para cada partner"""
        for partner in self:
            delivery_addresses = partner.child_ids.filtered(lambda c: c.type == 'delivery')
            partner.delivery_address_count = len(delivery_addresses)

    @api.constrains('is_distributor', 'parent_id')
    def _check_distributor_consistency(self):
        """Asegurar que los distribuidores no sean contactos hijo"""
        for partner in self:
            if partner.is_distributor and partner.parent_id:
                raise ValidationError(
                    _('Un contacto no puede marcarse como distribuidor si tiene una empresa padre')
                )

    def get_delivery_addresses_for_selection(self):
        """Obtener direcciones de entrega formateadas para widget de selección"""
        self.ensure_one()
        addresses = []
        
        if self.is_distributor:
            # Incluir la dirección principal si tiene dirección completa
            if self.street:
                addresses.append((self.id, f"[Principal] {self.contact_address}"))
            
            # Incluir todas las direcciones de entrega
            for delivery in self.delivery_address_ids:
                province = f" ({delivery.state_id.name})" if delivery.state_id else ""
                addresses.append((delivery.id, f"[Entrega] {delivery.name} - {delivery.city}{province}"))
        else:
            # Para clientes normales, solo la dirección principal
            if self.street:
                addresses.append((self.id, self.contact_address))
        
        return addresses

    def action_view_delivery_addresses(self):
        """Acción para ver todas las direcciones de entrega de este partner"""
        self.ensure_one()
        action = self.env.ref('contacts.action_contacts').read()[0]
        action['domain'] = [('parent_id', '=', self.id), ('type', '=', 'delivery')]
        action['context'] = {
            'default_parent_id': self.id,
            'default_type': 'delivery',
            'default_is_company': False,
            'default_country_id': self.env.ref('base.es').id,  # España por defecto
        }
        action['name'] = _('Direcciones de Entrega para %s') % self.display_name
        return action

    @api.model
    def create_delivery_address_es(self, partner_id, address_data):
        """
        Crear una nueva dirección de entrega para un partner (versión española)
        
        Args:
            partner_id (int): ID del partner padre
            address_data (dict): Diccionario con información de la dirección
            
        Returns:
            res.partner: Dirección de entrega creada
        """
        parent_partner = self.browse(partner_id)
        
        if not parent_partner.exists():
            raise ValidationError(_('Partner padre no encontrado'))
        
        # Preparar datos para la nueva dirección con valores por defecto españoles
        delivery_data = {
            'name': address_data.get('name', f"{parent_partner.name} - Entrega"),
            'parent_id': partner_id,
            'type': 'delivery',
            'street': address_data.get('street', ''),
            'street2': address_data.get('street2', ''),
            'city': address_data.get('city', ''),
            'state_id': address_data.get('state_id', False),
            'zip': address_data.get('zip', ''),
            'country_id': address_data.get('country_id', self.env.ref('base.es').id),  # España por defecto
            'phone': address_data.get('phone', ''),
            'email': address_data.get('email', ''),
            'company_id': parent_partner.company_id.id,
            'is_company': False,
            'truck_access': address_data.get('truck_access', 'camion_mediano'),
            'loading_equipment': address_data.get('loading_equipment', 'manual'),
        }
        
        # Crear la nueva dirección
        new_address = self.create(delivery_data)
        
        return new_address

    def get_installation_info(self):
        """Obtener información de instalación y logística"""
        self.ensure_one()
        
        info = {
            'can_install': self.installation_capability,
            'truck_access': dict(self._fields['truck_access'].selection).get(self.truck_access, 'No especificado'),
            'loading_equipment': dict(self._fields['loading_equipment'].selection).get(self.loading_equipment, 'No especificado'),
            'schedule_notes': self.delivery_schedule_notes or 'Sin notas específicas',
        }
        
        return info

    def action_create_project_delivery(self):
        """Crear dirección de entrega específica para un proyecto"""
        self.ensure_one()
        
        return {
            'name': _('Nueva Dirección de Proyecto'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'view_id': self.env.ref('sale_delivery_address_inline.view_delivery_address_form_es').id,
            'target': 'new',
            'context': {
                'default_parent_id': self.id,
                'default_type': 'delivery',
                'default_country_id': self.env.ref('base.es').id,
                'default_is_company': False,
                'default_name': f"{self.name} - Proyecto Nuevo",
            }
        }

    @api.model
    def get_spanish_provinces_stats(self):
        """Obtener estadísticas de direcciones por provincia española"""
        query = """
            SELECT 
                rcs.name as provincia,
                COUNT(rp.id) as total_direcciones,
                COUNT(CASE WHEN rp.type = 'delivery' THEN 1 END) as direcciones_entrega
            FROM res_partner rp
            LEFT JOIN res_country_state rcs ON rp.state_id = rcs.id
            LEFT JOIN res_country rc ON rp.country_id = rc.id
            WHERE rc.code = 'ES' OR rc.id IS NULL
            GROUP BY rcs.name, rcs.id
            ORDER BY total_direcciones DESC
        """
        
        self.env.cr.execute(query)
        return self.env.cr.dictfetchall()

    def check_delivery_compatibility(self, product_weight=0, product_volume=0):
        """
        Verificar compatibilidad de entrega según peso y volumen del producto
        
        Args:
            product_weight (float): Peso en kg
            product_volume (float): Volumen en m³
            
        Returns:
            dict: Información de compatibilidad
        """
        self.ensure_one()
        
        compatibility = {
            'can_deliver': True,
            'warnings': [],
            'recommendations': [],
        }
        
        # Verificar acceso según peso (losas de caucho son pesadas)
        if product_weight > 1000:  # Más de 1 tonelada
            if self.truck_access in ['furgoneta', 'manual']:
                compatibility['warnings'].append(
                    'Peso elevado para vehículo pequeño. Considerar fraccionamiento de entrega.'
                )
        
        # Verificar equipo de descarga
        if product_weight > 500 and self.loading_equipment == 'manual':
            compatibility['warnings'].append(
                'Descarga manual no recomendada para este peso. Valorar equipo mecánico.'
            )
        
        if product_weight > 100 and not self.loading_equipment:
            compatibility['recommendations'].append(
                'Especificar equipo de descarga disponible para optimizar entrega.'
            )
        
        return compatibility

    def _get_contact_address_formatted(self):
        """Obtener dirección formateada para España"""
        self.ensure_one()
        
        address_parts = []
        
        if self.street:
            address_parts.append(self.street)
        
        if self.street2:
            address_parts.append(self.street2)
        
        # Formato español: CP Ciudad, Provincia
        city_line = []
        if self.zip:
            city_line.append(self.zip)
        if self.city:
            city_line.append(self.city)
        
        if city_line:
            address_parts.append(" ".join(city_line))
        
        if self.state_id:
            address_parts.append(self.state_id.name)
        
        if self.country_id and self.country_id.code != 'ES':
            address_parts.append(self.country_id.name)
        
        return "\n".join(address_parts)
