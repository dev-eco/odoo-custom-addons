# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DeliveryAddressWizard(models.TransientModel):
    _name = 'delivery.address.wizard'
    _description = 'Wizard de Creación de Direcciones de Entrega'

    # ==========================================
    # CAMPOS BÁSICOS
    # ==========================================
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        domain=[('is_company', '=', True)]
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Pedido de Venta'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company
    )
    
    # ==========================================
    # TIPO DE DIRECCIÓN
    # ==========================================
    
    is_temporary = fields.Boolean(
        string='Dirección Temporal',
        default=False,
        help="Marca si es dirección temporal para un proyecto específico"
    )
    
    address_type = fields.Selection([
        ('permanent', 'Dirección Permanente'),
        ('temporary', 'Dirección Temporal (Proyecto)')
    ], string='Tipo de Dirección', default='permanent', required=True)
    
    # ==========================================
    # DATOS DE PROYECTO (para temporales)
    # ==========================================
    
    project_reference = fields.Char(
        string='Referencia Proyecto',
        help="Código o nombre del proyecto"
    )
    
    project_description = fields.Text(
        string='Descripción Proyecto'
    )
    
    project_start_date = fields.Date(
        string='Fecha Inicio'
    )
    
    project_end_date = fields.Date(
        string='Fecha Fin Estimada'
    )
    
    project_status = fields.Selection([
        ('planned', 'Planificado'),
        ('active', 'En Curso'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string='Estado Proyecto', default='planned')
    
    # ==========================================
    # DATOS DE DIRECCIÓN
    # ==========================================
    
    name = fields.Char(
        string='Nombre Dirección',
        required=True,
        help="Nombre descriptivo de la dirección"
    )
    
    street = fields.Char(
        string='Dirección',
        required=True
    )
    
    street2 = fields.Char(
        string='Información Adicional'
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
        string='Provincia'
    )
    
    country_id = fields.Many2one(
        'res.country',
        string='País',
        default=lambda self: self.env.ref('base.es')
    )
    
    phone = fields.Char(
        string='Teléfono'
    )
    
    mobile = fields.Char(
        string='Móvil'
    )
    
    email = fields.Char(
        string='Email'
    )
    
    # ==========================================
    # DATOS LOGÍSTICOS
    # ==========================================
    
    site_contact_name = fields.Char(
        string='Contacto en Obra'
    )
    
    site_contact_phone = fields.Char(
        string='Teléfono Contacto'
    )
    
    truck_access = fields.Selection([
        ('large', 'Camión Grande (+12m)'),
        ('medium', 'Camión Mediano (7-12m)'),
        ('small', 'Furgoneta/Pequeño (<7m)'),
        ('manual', 'Solo Descarga Manual')
    ], string='Acceso Vehículos')
    
    loading_equipment = fields.Selection([
        ('crane', 'Grúa Disponible'),
        ('forklift', 'Carretilla Elevadora'),
        ('pallet', 'Transpaleta'),
        ('manual', 'Solo Descarga Manual')
    ], string='Equipo Descarga')
    
    delivery_schedule_notes = fields.Text(
        string='Notas de Horario'
    )
    
    # ==========================================
    # ONCHANGES
    # ==========================================
    
    @api.onchange('address_type')
    def _onchange_address_type(self):
        """Sincroniza is_temporary con address_type"""
        self.is_temporary = (self.address_type == 'temporary')
    
    @api.onchange('is_temporary')
    def _onchange_is_temporary(self):
        """Sincroniza address_type con is_temporary"""
        if self.is_temporary:
            self.address_type = 'temporary'
        else:
            self.address_type = 'permanent'
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    @api.constrains('project_start_date', 'project_end_date')
    def _check_project_dates(self):
        """Valida fechas de proyecto"""
        for wizard in self:
            if wizard.project_start_date and wizard.project_end_date:
                if wizard.project_end_date < wizard.project_start_date:
                    raise ValidationError(_(
                        "La fecha fin no puede ser anterior a la fecha inicio"
                    ))
    
    # ==========================================
    # ACTIONS
    # ==========================================
    
    def action_create_address(self):
        """Crea la dirección de entrega"""
        self.ensure_one()
        
        # Validar que para temporales haya referencia de proyecto
        if self.is_temporary and not self.project_reference:
            raise UserError(_(
                "Para direcciones temporales debe indicar "
                "una referencia de proyecto"
            ))
        
        # Preparar valores
        vals = {
            'name': self.name,
            'parent_id': self.partner_id.id,
            'type': 'delivery',
            'company_id': self.company_id.id,
            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'zip': self.zip,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': self.email,
            'is_temporary_address': self.is_temporary,
            'site_contact_name': self.site_contact_name,
            'site_contact_phone': self.site_contact_phone,
            'truck_access': self.truck_access,
            'loading_equipment': self.loading_equipment,
            'delivery_schedule_notes': self.delivery_schedule_notes,
        }
        
        # Añadir datos de proyecto si es temporal
        if self.is_temporary:
            vals.update({
                'project_reference': self.project_reference,
                'project_description': self.project_description,
                'project_start_date': self.project_start_date,
                'project_end_date': self.project_end_date,
                'project_status': self.project_status,
            })
        
        # Crear dirección
        new_address = self.env['res.partner'].create(vals)
        
        # Si viene de un pedido, actualizar
        if self.sale_order_id:
            self.sale_order_id.write({
                'partner_shipping_id': new_address.id,
                'selected_delivery_partner_id': new_address.id,
                'use_alternative_delivery': True,
            })
            
            # Mensaje en pedido
            msg = _("🏭 Nueva dirección creada: <strong>%s</strong>") % new_address.name
            if self.is_temporary:
                msg += _("<br/>📦 Proyecto: %s") % self.project_reference
            self.sale_order_id.message_post(body=msg)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Éxito!'),
                'message': _('Dirección creada: %s') % new_address.name,
                'type': 'success',
                'sticky': False,
            }
        }
