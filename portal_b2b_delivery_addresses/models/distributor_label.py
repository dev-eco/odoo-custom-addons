# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DistributorLabel(models.Model):
    """Etiquetas personalizadas de distribuidores para sus clientes finales."""
    
    _name = 'distributor.label'
    _description = 'Etiqueta Personalizada Distribuidor'
    _order = 'name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Distribuidor',
        required=True,
        ondelete='cascade',
        index=True,
        help='Distribuidor propietario de esta etiqueta'
    )
    
    name = fields.Char(
        string='Nombre Etiqueta',
        required=True,
        help='Nombre identificativo (ej: "Cliente Final ABC")'
    )
    
    customer_name = fields.Char(
        string='Nombre Cliente Final',
        required=True,
        help='Nombre del cliente final del distribuidor'
    )
    
    customer_reference = fields.Char(
        string='Referencia Cliente',
        help='Referencia interna del distribuidor para este cliente'
    )
    
    tax_id = fields.Char(
        string='NIF/CIF Cliente Final',
        help='Número de identificación fiscal del cliente final'
    )
    
    customer_address = fields.Text(
        string='Dirección Cliente Final',
        help='Dirección completa del cliente final'
    )
    
    customer_phone = fields.Char(
        string='Teléfono Cliente Final'
    )
    
    customer_email = fields.Char(
        string='Email Cliente Final'
    )
    
    notes = fields.Text(
        string='Notas',
        help='Información adicional sobre este cliente'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    # Configuración de impresión
    print_on_delivery_note = fields.Boolean(
        string='Imprimir en Albarán',
        default=True,
        help='Incluir esta información en el albarán de entrega'
    )
    
    hide_company_info = fields.Boolean(
        string='Ocultar Info Empresa',
        default=False,
        help='No mostrar información de nuestra empresa en documentos'
    )
    
    # Campos adicionales para información del cliente
    contact_person = fields.Char(
        string='Persona de Contacto',
        help='Nombre de la persona de contacto en el cliente final'
    )
    
    payment_terms = fields.Char(
        string='Condiciones de Pago',
        help='Condiciones de pago acordadas con el cliente final'
    )
    
    delivery_instructions = fields.Text(
        string='Instrucciones de Entrega',
        help='Instrucciones especiales para entregas a este cliente'
    )
    
    # Archivos adjuntos
    transport_label = fields.Binary(
        string='Etiqueta de Transporte',
        attachment=True,
        help='Etiqueta personalizada para el transporte'
    )
    
    transport_label_filename = fields.Char(
        string='Nombre Archivo Etiqueta'
    )
    
    delivery_note = fields.Binary(
        string='Albarán Personalizado',
        attachment=True,
        help='Plantilla de albarán personalizada'
    )
    
    delivery_note_filename = fields.Char(
        string='Nombre Archivo Albarán'
    )
    
    # Campos computados para estadísticas
    order_count = fields.Integer(
        string='Número de Pedidos',
        compute='_compute_order_stats',
        store=False,
        help='Cantidad de pedidos con esta etiqueta'
    )
    
    last_order_date = fields.Date(
        string='Último Pedido',
        compute='_compute_order_stats',
        store=False,
        help='Fecha del último pedido con esta etiqueta'
    )

    @api.depends('name')
    def _compute_order_stats(self) -> None:
        """Calcula estadísticas de pedidos con esta etiqueta."""
        for label in self:
            orders = self.env['sale.order'].search([
                ('distributor_label_id', '=', label.id)
            ])
            
            label.order_count = len(orders)
            
            if orders:
                latest_order = orders.sorted('date_order', reverse=True)[0]
                label.last_order_date = latest_order.date_order.date() if latest_order.date_order else False
            else:
                label.last_order_date = False

    @api.constrains('customer_email')
    def _check_email(self):
        """Valida formato de email si se proporciona."""
        for label in self:
            if label.customer_email:
                if '@' not in label.customer_email or '.' not in label.customer_email:
                    raise ValidationError(_('El formato del email no es válido.'))

    def obtener_info_completa(self) -> dict:
        """
        Obtiene toda la información de la etiqueta en formato diccionario.
        
        Returns:
            dict: Información completa de la etiqueta
        """
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'customer_name': self.customer_name,
            'customer_reference': self.customer_reference or '',
            'tax_id': self.tax_id or '',
            'customer_address': self.customer_address or '',
            'customer_phone': self.customer_phone or '',
            'customer_email': self.customer_email or '',
            'contact_person': self.contact_person or '',
            'payment_terms': self.payment_terms or '',
            'delivery_instructions': self.delivery_instructions or '',
            'notes': self.notes or '',
            'print_on_delivery_note': self.print_on_delivery_note,
            'hide_company_info': self.hide_company_info,
            'order_count': self.order_count,
            'last_order_date': self.last_order_date,
        }
