from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrderMultipleInvoiceWizard(models.TransientModel):
    _name = 'sale.order.multiple.invoice.wizard'
    _description = 'Asistente para crear facturas consolidadas'
    
    sale_order_ids = fields.Many2many(
        'sale.order',
        string='Pedidos de venta',
        required=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
    )
    
    consolidation_mode = fields.Selection([
        ('sum_by_product', 'Sumar cantidades por producto'),
        ('lines_separate', 'Mantener líneas separadas'),
    ], string='Modo de consolidación', 
       required=True, 
       default='sum_by_product',
       help='Define cómo se agruparán las líneas de pedido en la factura')
    
    include_partial = fields.Boolean(
        string='Incluir pedidos parcialmente facturados',
        default=True,
        help='Si está activado, incluirá las cantidades pendientes de facturar en pedidos parcialmente facturados'
    )
    
    group_taxes = fields.Boolean(
        string='Agrupar impuestos',
        default=True,
        help='Agrupar impuestos del mismo tipo en líneas de factura'
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario',
        domain=[('type', '=', 'sale')],
        default=lambda self: self.env['account.journal'].search([('type', '=', 'sale')], limit=1),
        required=True,
    )
    
    date_invoice = fields.Date(
        string='Fecha de factura',
        default=fields.Date.context_today,
        required=True,
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura creada',
        readonly=True,
        copy=False,
    )
    
    use_existing_invoice = fields.Boolean(
        string='Añadir a factura existente',
        default=False
    )
    
    existing_invoice_id = fields.Many2one(
        'account.move',
        string='Factura existente',
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'draft')]",
        help='Seleccione una factura existente para añadir estos pedidos'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Precarga información basada en los pedidos seleccionados"""
        res = super().default_get(fields_list)
        
        sale_order_ids = self.env.context.get('active_ids')
        if not sale_order_ids:
            return res
        
        sale_orders = self.env['sale.order'].browse(sale_order_ids)
        
        # Verificar que todos los pedidos tengan el mismo partner
        partners = sale_orders.mapped('partner_invoice_id')
        if len(partners) != 1:
            raise UserError(_('Solo puede consolidar facturas de un mismo cliente'))
        
        # Verificar que todos los pedidos sean de la misma compañía
        companies = sale_orders.mapped('company_id')
        if len(companies) != 1:
            raise UserError(_('Solo puede consolidar pedidos de la misma compañía'))
        
        # Verificar que todos los pedidos estén confirmados
        invalid_states = sale_orders.filtered(lambda o: o.state not in ['sale', 'done'])
        if invalid_states:
            raise UserError(_('Solo puede facturar pedidos confirmados. '
                             'Los siguientes pedidos no están confirmados: %s') % 
                           ', '.join(invalid_states.mapped('name')))
        
        # Verificar si alguno ya está completamente facturado
        fully_invoiced = sale_orders.filtered(lambda o: o.invoice_status == 'invoiced')
        if fully_invoiced:
            raise UserError(_('Los siguientes pedidos ya están completamente facturados: %s') %
                           ', '.join(fully_invoiced.mapped('name')))
        
        res.update({
            'sale_order_ids': [(6, 0, sale_orders.ids)],
            'partner_id': partners.id,
            'company_id': companies.id,
        })
        
        return res
    
    @api.onchange('sale_order_ids')
    def _onchange_sale_order_ids(self):
        """Actualiza la información cuando cambian los pedidos seleccionados"""
        if not self.sale_order_ids:
            return
        
        partners = self.sale_order_ids.mapped('partner_invoice_id')
        if len(partners) > 1:
            raise UserError(_('Solo puede consolidar facturas de un mismo cliente'))
        
        companies = self.sale_order_ids.mapped('company_id')
        if len(companies) > 1:
            raise UserError(_('Solo puede consolidar pedidos de la misma compañía'))
        
        self.partner_id = partners
        self.company_id = companies
    
    def _check_existing_invoice(self):
        """Comprueba si ya existe una factura consolidada para este conjunto de pedidos"""
        if not self.sale_order_ids:
            return False
            
        # Comprobar si todos estos pedidos ya están asociados a una misma factura
        groups = self.env['sale.order.invoice.group'].search([
            ('sale_order_id', 'in', self.sale_order_ids.ids)
        ])
        
        if not groups:
            return False
            
        invoice_ids = groups.mapped('invoice_id')
        
        # Si todos los pedidos están asociados a una misma factura
        if len(invoice_ids) == 1:
            # Verificar que todos los pedidos estén en la factura
            orders_in_invoice = groups.mapped('sale_order_id')
            if len(orders_in_invoice) == len(self.sale_order_ids):
                return invoice_ids[0]
                
        return False
    
    def _prepare_invoice_vals(self):
        """Prepara los valores para crear la factura"""
        return {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'invoice_date': self.date_invoice,
            'invoice_origin': ', '.join(self.sale_order_ids.mapped('name')),
            'company_id': self.company_id.id,
            'currency_id': self.sale_order_ids[0].currency_id.id,
            'invoice_user_id': self.env.user.id,
            'narration': _('Factura consolidada de pedidos: %s') % 
                         ', '.join(self.sale_order_ids.mapped('name')),
        }
    
    def _get_grouped_lines(self):
        """Obtiene las líneas agrupadas según el modo de consolidación"""
        if self.consolidation_mode == 'lines_separate':
            # Mantener todas las líneas separadas
            result = []
            for order in self.sale_order_ids:
                for line in order.order_line:
                    if line.product_id and line.product_uom_qty > line.qty_invoiced and line.qty_to_invoice > 0:
                        result.append({
                            'product_id': line.product_id.id,
                            'name': '%s - %s: %s' % (line.product_id.name, _('Pedido'), order.name),
                            'quantity': line.qty_to_invoice,
                            'price_unit': line.price_unit,
                            'tax_ids': [(6, 0, line.tax_id.ids)],
                            'discount': line.discount,
                            'sale_order_id': order.id,
                            'sale_order_line_id': line.id,
                            'sale_line_ids': [(4, line.id)],  # Enlace con la línea de venta
                            'account_id': line.product_id.property_account_income_id.id or 
                                        line.product_id.categ_id.property_account_income_categ_id.id,
                        })
            return result
        else:
            # Agrupar por producto
            product_lines = {}
            for order in self.sale_order_ids:
                for line in order.order_line:
                    if not line.product_id or line.qty_to_invoice <= 0:
                        continue
                        
                    product_id = line.product_id.id
                    tax_ids = tuple(line.tax_id.ids)
                    
                    # Clave para agrupar por producto y por impuestos
                    key = (product_id, tax_ids)
                    
                    if key not in product_lines:
                        product_lines[key] = {
                            'product_id': product_id,
                            'name': line.product_id.name,
                            'quantity': 0,
                            'price_unit': line.price_unit,
                            'tax_ids': [(6, 0, line.tax_id.ids)],
                            'discount': line.discount,
                            'sale_order_ids': [],
                            'sale_order_line_ids': [],
                            'sale_line_ids': [],  # Para enlazar con las líneas de venta
                            'account_id': line.product_id.property_account_income_id.id or 
                                        line.product_id.categ_id.property_account_income_categ_id.id,
                        }
                    
                    product_lines[key]['quantity'] += line.qty_to_invoice
                    product_lines[key]['sale_order_ids'].append(order.id)
                    product_lines[key]['sale_order_line_ids'].append(line.id)
                    product_lines[key]['sale_line_ids'].append((4, line.id))  # Enlace con la línea de venta
                    
            # Convertir a lista y ajustar nombres
            result = []
            for key, line in product_lines.items():
                # Obtener pedidos únicos para este producto
                sale_order_ids = list(set(line.pop('sale_order_ids')))
                sale_order_line_ids = list(set(line.pop('sale_order_line_ids')))
                sale_line_ids = line.pop('sale_line_ids')  # No eliminar los enlaces con las líneas de venta
                
                orders = self.env['sale.order'].browse(sale_order_ids)
                order_names = ', '.join(orders.mapped('name'))
                
                line['name'] = '%s - %s: %s' % (line['name'], _('Pedidos'), order_names)
                line['sale_order_id'] = sale_order_ids[0] if sale_order_ids else False
                line['sale_order_line_id'] = sale_order_line_ids[0] if sale_order_line_ids else False
                line['sale_line_ids'] = sale_line_ids  # Mantener los enlaces con las líneas de venta
                
                result.append(line)
                
            return result
    
    def _create_invoice(self):
        """Crea la factura consolidada"""
        # Comprobar si ya existe una factura para este conjunto de pedidos
        existing_invoice = self._check_existing_invoice()
        if existing_invoice:
            return existing_invoice

        # Estas definiciones se han movido al nivel de clase
            
        # Preparar valores de la factura
        invoice_vals = self._prepare_invoice_vals()
        
        # Crear factura
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create(invoice_vals)
        
        # Obtener líneas de factura agrupadas
        invoice_lines = self._get_grouped_lines()
        
        # Crear líneas de factura
        for line in invoice_lines:
            line['move_id'] = invoice.id
            self.env['account.move.line'].create(line)
            
        # Actualizar el estado de facturación de los pedidos
        # En Odoo 17.0 no es necesario llamar a _post_validate, 
        # la actualización de cantidades facturadas se hace automáticamente
        # gracias al campo sale_line_ids
        
        # Crear registros de relación para cada pedido
        group_vals = []
        for order in self.sale_order_ids:
            group_vals.append({
                'sale_order_id': order.id,
                'invoice_id': invoice.id,
                'consolidation_mode': self.consolidation_mode,
            })
        
        self.env['sale.order.invoice.group'].create(group_vals)
        
        return invoice
    
    def action_create_invoice(self):
        """Acción para crear o modificar la factura consolidada"""
        self.ensure_one()
        
        # Verificar que haya pedidos seleccionados
        if not self.sale_order_ids:
            raise UserError(_('Debe seleccionar al menos un pedido para facturar'))
        
        # Crear factura o añadir a existente
        if self.use_existing_invoice:
            invoice = self._add_to_existing_invoice()
        else:
            invoice = self._create_invoice()
            
        self.invoice_id = invoice.id
        
        # Retornar acción para ver la factura
        action = {
            'name': _('Factura Consolidada'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'context': {'create': False},
        }
        
        return action

    def check_and_fix_duplicates(self):
        """
        Script para verificar y corregir posibles registros duplicados
        de relación entre pedidos y facturas
        """
        # Buscar posibles grupos duplicados
        query = """
            SELECT sale_order_id, invoice_id, COUNT(*) as count
            FROM sale_order_invoice_group
            GROUP BY sale_order_id, invoice_id
            HAVING COUNT(*) > 1
        """
        self.env.cr.execute(query)
        duplicates = self.env.cr.dictfetchall()
        
        # Eliminar duplicados dejando solo un registro por relación
        for dup in duplicates:
            groups = self.env['sale.order.invoice.group'].search([
                ('sale_order_id', '=', dup['sale_order_id']),
                ('invoice_id', '=', dup['invoice_id'])
            ], order='date_created')
            
            # Mantener el registro más antiguo, eliminar el resto
            if len(groups) > 1:
                groups[1:].unlink()
        
        return len(duplicates)

    def _add_to_existing_invoice(self):
        """Añade los pedidos seleccionados a una factura existente"""
        self.ensure_one()
        
        if not self.existing_invoice_id:
            raise UserError(_('Debe seleccionar una factura existente'))
            
        if self.existing_invoice_id.state != 'draft':
            raise UserError(_('Solo se pueden modificar facturas en estado borrador'))
            
        # Verificar que la factura es del mismo cliente
        if self.existing_invoice_id.partner_id != self.partner_id:
            raise UserError(_('La factura seleccionada debe ser del mismo cliente'))
            
        # Obtener líneas a añadir
        invoice_lines = self._get_grouped_lines()
        
        # Añadir líneas a la factura existente
        for line in invoice_lines:
            line['move_id'] = self.existing_invoice_id.id
            self.env['account.move.line'].create(line)
            
        # Actualizar el estado de facturación de los pedidos
        # En Odoo 17.0 no es necesario llamar a _post_validate, 
        # la actualización de cantidades facturadas se hace automáticamente
        # gracias al campo sale_line_ids
        
        # Crear registros de relación para cada pedido
        for order in self.sale_order_ids:
            self.env['sale.order.invoice.group'].create({
                'sale_order_id': order.id,
                'invoice_id': self.existing_invoice_id.id,
                'consolidation_mode': self.consolidation_mode,
            })
            
            # Registrar en el chatter del pedido
            order.message_post(
                body=_("Este pedido ha sido añadido a la factura existente: %s") % 
                      self.existing_invoice_id.name
            )
        
        # Registrar en el chatter de la factura
        order_names = ', '.join(self.sale_order_ids.mapped('name'))
        self.existing_invoice_id.message_post(
            body=_("Se han añadido los siguientes pedidos a esta factura: %s") % 
                  order_names
        )
            
        return self.existing_invoice_id
