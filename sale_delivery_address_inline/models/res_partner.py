# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ==========================================
    # CAMPOS PRINCIPALES
    # ==========================================
    
    is_distributor = fields.Boolean(
        string='Es Distribuidor',
        default=False,
        tracking=True,
        help="Marca si este cliente es un distribuidor con múltiples direcciones de entrega permanentes"
    )
    
    # NUEVO - Direcciones temporales para proyectos
    is_temporary_address = fields.Boolean(
        string='Dirección Temporal',
        default=False,
        tracking=True,
        help="Marca si esta dirección es temporal (para un proyecto específico)"
    )
    
    project_reference = fields.Char(
        string='Referencia de Proyecto',
        tracking=True,
        help="Código o nombre del proyecto asociado a esta dirección temporal"
    )
    
    project_description = fields.Text(
        string='Descripción del Proyecto',
        help="Detalles adicionales sobre el proyecto"
    )
    
    project_start_date = fields.Date(
        string='Fecha Inicio Proyecto',
        tracking=True
    )
    
    project_end_date = fields.Date(
        string='Fecha Fin Proyecto',
        tracking=True,
        help="Fecha estimada de finalización del proyecto"
    )
    
    project_status = fields.Selection([
        ('planned', 'Planificado'),
        ('active', 'En Curso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string='Estado del Proyecto', default='planned', tracking=True)
    
    # Contador de direcciones de entrega
    delivery_address_count = fields.Integer(
        string='Nº Direcciones de Entrega',
        compute='_compute_delivery_address_count',
        store=True
    )
    
    # Relación inversa
    delivery_address_ids = fields.One2many(
        'res.partner',
        compute='_compute_delivery_address_ids',
        string='Direcciones de Entrega'
    )
    
    # ==========================================
    # CAMPOS LOGÍSTICOS
    # ==========================================
    
    distributor_type = fields.Selection([
        ('local', 'Distribuidor Local'),
        ('regional', 'Distribuidor Regional'),
        ('national', 'Distribuidor Nacional'),
        ('international', 'Distribuidor Internacional')
    ], string='Tipo de Distribuidor', tracking=True)
    
    delivery_schedule_notes = fields.Text(
        string='Notas de Horarios de Entrega',
        help="Restricciones de horario, días permitidos, etc."
    )
    
    truck_access = fields.Selection([
        ('large', 'Camión Grande (+12m)'),
        ('medium', 'Camión Mediano (7-12m)'),
        ('small', 'Furgoneta/Pequeño (<7m)'),
        ('manual', 'Solo Descarga Manual')
    ], string='Acceso para Vehículos', tracking=True)
    
    loading_equipment = fields.Selection([
        ('crane', 'Grúa Disponible'),
        ('forklift', 'Carretilla Elevadora'),
        ('pallet', 'Transpaleta'),
        ('manual', 'Solo Descarga Manual')
    ], string='Equipo de Descarga', tracking=True)
    
    site_contact_name = fields.Char(
        string='Contacto en Obra',
        help="Nombre del responsable en la ubicación de entrega"
    )
    
    site_contact_phone = fields.Char(
        string='Teléfono Contacto Obra',
        help="Teléfono del responsable en obra"
    )
    
    # ==========================================
    # CAMPOS COMPUTADOS
    # ==========================================
    
    @api.depends('child_ids', 'child_ids.type')
    def _compute_delivery_address_count(self):
        """Calcula el número de direcciones de entrega"""
        for partner in self:
            partner.delivery_address_count = len(
                partner.child_ids.filtered(lambda r: r.type == 'delivery')
            )
    
    @api.depends('child_ids', 'child_ids.type')
    def _compute_delivery_address_ids(self):
        """Devuelve las direcciones de entrega asociadas"""
        for partner in self:
            partner.delivery_address_ids = partner.child_ids.filtered(
                lambda r: r.type == 'delivery'
            )
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    @api.constrains('is_distributor', 'parent_id')
    def _check_distributor_constraints(self):
        """Valida reglas para distribuidores"""
        for partner in self:
            if partner.is_distributor and partner.parent_id:
                raise ValidationError(_(
                    "Un contacto no puede marcarse como distribuidor "
                    "si tiene una empresa padre"
                ))
    
    @api.constrains('is_temporary_address', 'type')
    def _check_temporary_address_constraints(self):
        """Valida que las direcciones temporales sean de tipo delivery"""
        for partner in self:
            if partner.is_temporary_address and partner.type != 'delivery':
                raise ValidationError(_(
                    "Las direcciones temporales deben ser de tipo 'Dirección de Entrega'"
                ))
    
    @api.constrains('project_start_date', 'project_end_date')
    def _check_project_dates(self):
        """Valida que la fecha de fin sea posterior a la de inicio"""
        for partner in self:
            if partner.project_start_date and partner.project_end_date:
                if partner.project_end_date < partner.project_start_date:
                    raise ValidationError(_(
                        "La fecha de fin del proyecto no puede ser anterior "
                        "a la fecha de inicio"
                    ))
    
    # ==========================================
    # ONCHANGES
    # ==========================================
    
    @api.onchange('is_temporary_address')
    def _onchange_is_temporary_address(self):
        """Al marcar como temporal, sugiere tipo delivery"""
        if self.is_temporary_address and not self.type:
            self.type = 'delivery'
    
    # ==========================================
    # ACTIONS
    # ==========================================
    
    def action_view_delivery_addresses(self):
        """Abre vista de direcciones de entrega del distribuidor"""
        self.ensure_one()
        
        if not self.parent_id:
            parent_id = self.id
        else:
            parent_id = self.parent_id.id
        
        return {
            'name': _('Direcciones de Entrega para %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [
                ('parent_id', '=', parent_id),
                ('type', '=', 'delivery')
            ],
            'context': {
                'default_parent_id': parent_id,
                'default_type': 'delivery',
                'default_company_id': self.company_id.id,
            }
        }
    
    def action_create_project_address(self):
        """Abre wizard para crear dirección de proyecto"""
        self.ensure_one()
        
        return {
            'name': _('Nueva Dirección de Proyecto'),
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.address.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_is_temporary': True,
            }
        }
    
    # ==========================================
    # MÉTODOS AUXILIARES
    # ==========================================
    
    def name_get(self):
        """Override para mostrar referencia de proyecto en nombre"""
        result = []
        for partner in self:
            name = super(ResPartner, partner).name_get()[0][1]
            
            if partner.is_temporary_address and partner.project_reference:
                name = f"[{partner.project_reference}] {name}"
            
            result.append((partner.id, name))
        
        return result
