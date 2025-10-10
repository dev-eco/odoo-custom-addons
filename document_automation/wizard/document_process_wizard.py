# wizard/document_process_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json

class DocumentValidateWizard(models.TransientModel):
    _name = 'document.validate.wizard'
    _description = 'Validador de Documentos'
    
    document_id = fields.Many2one(
        'document.automation', 
        string='Documento', 
        required=True
    )
    document_type_id = fields.Many2one(
        'document.type',
        string='Tipo de documento',
        related='document_id.document_type_id',
        readonly=True
    )
    extracted_data = fields.Text(
        string='Datos extraídos',
        related='document_id.extracted_data',
        readonly=True
    )
    
    # Campos dinámicos según tipo de documento
    document_data = fields.Text(
        string='Datos a utilizar',
        help="Datos JSON para crear el documento"
    )
    
    # Datos específicos de factura
    partner_id = fields.Many2one('res.partner', string='Proveedor')
    invoice_date = fields.Date(string='Fecha de factura')
    invoice_number = fields.Char(string='Número de factura')
    amount_total = fields.Float(string='Importe total')
    
    # Datos específicos de pedido
    order_date = fields.Date(string='Fecha de pedido')
    order_number = fields.Char(string='Número de pedido')
    
    # Datos específicos de albarán
    delivery_date = fields.Date(string='Fecha de entrega')
    delivery_number = fields.Char(string='Número de albarán')
    order_reference = fields.Char(string='Referencia de pedido')
    
    @api.model
    def default_get(self, fields_list):
        """Prepopular campos según datos extraídos"""
        res = super(DocumentValidateWizard, self).default_get(fields_list)
        
        document_id = self.env.context.get('default_document_id')
        if not document_id:
            return res
            
        document = self.env['document.automation'].browse(document_id)
        if not document.extracted_data:
            return res
            
        try:
            # Cargar datos extraídos
            data = json.loads(document.extracted_data)
            
            # Prepopular campos comunes
            if data.get('partner_id'):
                res['partner_id'] = data.get('partner_id')
            elif data.get('vat'):
                partner = self.env['res.partner'].search([
                    '|', ('vat', '=ilike', data.get('vat')), 
                    ('vat', '=ilike', 'ES' + data.get('vat'))
                ], limit=1)
                if partner:
                    res['partner_id'] = partner.id
                    
            # Tipo específico: Factura
            if document.document_type_id.code == 'invoice':
                res['invoice_date'] = data.get('invoice_date')
                res['invoice_number'] = data.get('invoice_number')
                res['amount_total'] = data.get('amount_total')
                
            # Tipo específico: Pedido
            elif document.document_type_id.code == 'purchase_order':
                res['order_date'] = data.get('date_order')
                res['order_number'] = data.get('order_number')
                
            # Tipo específico: Albarán
            elif document.document_type_id.code == 'delivery':
                res['delivery_date'] = data.get('date')
                res['delivery_number'] = data.get('delivery_number')
                res['order_reference'] = data.get('order_reference')
                
        except Exception as e:
            self.env['document.automation.log'].create({
                'document_id': document_id,
                'action': 'validate',
                'level': 'error',
                'message': _("Error al cargar datos: %s") % str(e),
                'user_id': self.env.user.id,
            })
        
        return res
    
    def action_validate(self):
        """Validar y crear documento"""
        self.ensure_one()
        
        document = self.document_id
        doc_type = document.document_type_id
        
        if not doc_type:
            raise UserError(_("El documento debe tener un tipo asignado para poder validarlo."))
            
        # Preparar datos según tipo
        if doc_type.code == 'invoice':
            if not self.partner_id:
                raise UserError(_("Debe seleccionar un proveedor para la factura."))
                
            # Crear factura
            invoice_vals = {
                'move_type': 'in_invoice',
                'partner_id': self.partner_id.id,
                'ref': self.invoice_number,
            }
            
            if self.invoice_date:
                invoice_vals['invoice_date'] = self.invoice_date
                
            try:
                invoice = self.env['account.move'].create(invoice_vals)
                
                # Añadir línea si tenemos importe
                if self.amount_total:
                    line_vals = {
                        'name': _('Importe validado manualmente'),
                        'quantity': 1,
                        'price_unit': self.amount_total,
                    }
                    invoice.write({
                        'invoice_line_ids': [(0, 0, line_vals)]
                    })
                    
                # Vincular con documento
                document.write({
                    'result_model': 'account.move',
                    'result_id': invoice.id,
                    'state': 'validated',
                    'validated_date': fields.Datetime.now(),
                    'status_message': _("Documento validado, factura creada")
                })
                
                # Adjuntar documento a factura
                attachment_vals = {
                    'name': document.filename or document.name,
                    'datas': document.document_file,
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'description': _("Documento validado manualmente")
                }
                self.env['ir.attachment'].create(attachment_vals)
                
                document.log_action('validate', _('Factura creada manualmente: %s') % invoice.name)
                
                # Mostrar factura creada
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
                
            except Exception as e:
                raise UserError(_("Error al crear factura: %s") % str(e))
                
        elif doc_type.code == 'purchase_order':
            if not self.partner_id:
                raise UserError(_("Debe seleccionar un proveedor para el pedido."))
                
            # Crear pedido
            order_vals = {
                'partner_id': self.partner_id.id,
                'name': self.order_number or '/',
            }
            
            if self.order_date:
                order_vals['date_order'] = self.order_date
                
            try:
                order = self.env['purchase.order'].create(order_vals)
                
                # Vincular con documento
                document.write({
                    'result_model': 'purchase.order',
                    'result_id': order.id,
                    'state': 'validated',
                    'validated_date': fields.Datetime.now(),
                    'status_message': _("Documento validado, pedido creado")
                })
                
                # Adjuntar documento a pedido
                attachment_vals = {
                    'name': document.filename or document.name,
                    'datas': document.document_file,
                    'res_model': 'purchase.order',
                    'res_id': order.id,
                    'description': _("Documento validado manualmente")
                }
                self.env['ir.attachment'].create(attachment_vals)
                
                document.log_action('validate', _('Pedido creado manualmente: %s') % order.name)
                
                # Mostrar pedido creado
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'res_id': order.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
                
            except Exception as e:
                raise UserError(_("Error al crear pedido: %s") % str(e))
                
        elif doc_type.code == 'delivery':
            if not self.partner_id:
                raise UserError(_("Debe seleccionar un proveedor para el albarán."))
                
            if self.order_reference:
                # Buscar pedido relacionado
                order = self.env['purchase.order'].search([
                    ('name', '=ilike', self.order_reference),
                    ('partner_id', '=', self.partner_id.id)
                ], limit=1)
                
                if order:
                    # Crear actividad en el pedido
                    activity_vals = {
                        'summary': _('Revisar albarán recibido'),
                        'note': _("""
                            Se ha validado manualmente un albarán con referencia: {delivery_number}
                            Fecha: {delivery_date}
                            
                            Este albarán requiere revisión manual para validar los productos recibidos.
                        """).format(
                            delivery_number=self.delivery_number or _('Sin referencia'),
                            delivery_date=self.delivery_date or _('No especificada')
                        ),
                        'res_id': order.id,
                        'res_model_id': self.env['ir.model'].search([('model', '=', 'purchase.order')], limit=1).id,
                        'user_id': order.user_id.id or self.env.user.id,
                        'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    }
                    
                    activity = self.env['mail.activity'].create(activity_vals)
                    
                    # Vincular documento con el pedido y registrar actividad creada
                    document.write({
                        'result_model': 'purchase.order',
                        'result_id': order.id,
                        'state': 'validated',
                        'validated_date': fields.Datetime.now(),
                        'status_message': _("Documento validado. Creada tarea de revisión manual en pedido relacionado.")
                    })
                    
                    # Adjuntar documento al pedido
                    attachment_vals = {
                        'name': document.filename or document.name,
                        'datas': document.document_file,
                        'res_model': 'purchase.order',
                        'res_id': order.id,
                        'description': _("Albarán validado manualmente")
                    }
                    self.env['ir.attachment'].create(attachment_vals)
                    
                    document.log_action('validate', _('Actividad creada en pedido: %s') % order.name)
                    
                    # Mostrar pedido relacionado
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'purchase.order',
                        'res_id': order.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                    
                else:
                    # No se encontró pedido, crear solo documento validado
                    document.write({
                        'state': 'validated',
                        'validated_date': fields.Datetime.now(),
                        'status_message': _("Documento validado. No se encontró pedido relacionado.")
                    })
                    document.log_action('validate', _('Albarán validado manualmente sin pedido relacionado'))
            else:
                # No hay referencia de pedido
                document.write({
                    'state': 'validated',
                    'validated_date': fields.Datetime.now(),
                    'status_message': _("Documento validado. No se especificó pedido relacionado.")
                })
                document.log_action('validate', _('Albarán validado manualmente sin referencia de pedido'))
                
            # Regresar al documento
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'document.automation',
                'res_id': document.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        else:
            # Tipo de documento no implementado específicamente
            document.write({
                'state': 'validated',
                'validated_date': fields.Datetime.now(),
                'status_message': _("Documento validado manualmente.")
            })
            document.log_action('validate', _('Documento validado manualmente'))
            
            # Regresar al documento
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'document.automation',
                'res_id': document.id,
                'view_mode': 'form',
                'target': 'current',
            }
