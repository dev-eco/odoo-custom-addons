# -*- coding: utf-8 -*-
# © 2025 ECOCAUCHO - https://ecocaucho.org
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models, _

class AccountMove(models.Model):
    """
    Extensión del modelo de facturas (account.move) para añadir campos personalizados
    útiles para el negocio de EcoCaucho.
    
    IMPORTANTE - Cambios en v2.0:
    ==============================
    Se ha ELIMINADO el método action_invoice_print() que estaba presente en v1.0.
    
    ¿Por qué?
    ---------
    En v1.0, ese método forzaba a todas las facturas a usar siempre la plantilla
    personalizada, sin dar opción al usuario. Esto causaba problemas:
    
    1. No se podía usar la plantilla estándar aunque se quisiera
    2. Al desinstalar el módulo, las facturas quedaban rotas
    3. No era flexible ni respetaba las preferencias del usuario
    
    En v2.0, este comportamiento se ha eliminado completamente. Ahora:
    - El usuario puede elegir qué plantilla usar (estándar o EcoCaucho)
    - Ambas plantillas coexisten pacíficamente
    - El módulo es completamente desinstalable
    
    Los campos personalizados se mantienen porque son útiles y no causan problemas.
    """
    
    _inherit = 'account.move'

    # =========================================================================
    # CAMPOS PERSONALIZADOS
    # =========================================================================
    # Estos campos añaden información útil que no existe en el modelo estándar
    # de Odoo pero que es necesaria para el flujo de trabajo de EcoCaucho
    # =========================================================================
    
    referencia_cliente = fields.Char(
        string="Referencia Cliente", 
        index=True,  # Indexado para búsquedas rápidas
        help="Referencia o número de pedido proporcionado por el cliente. "
             "Por ejemplo, si el cliente tiene su propio sistema de numeración "
             "de órdenes de compra, ese número se registra aquí."
    )
    
    instrucciones_especiales = fields.Text(
        string="Instrucciones Especiales",
        help="Notas o instrucciones especiales para esta factura que aparecerán "
             "en la versión impresa. Por ejemplo: 'Entregar en almacén B', "
             "'Requiere firma del responsable de compras', etc."
    )
    
    contacto_facturacion = fields.Many2one(
        'res.partner',
        string="Contacto de Facturación",
        domain="[('parent_id', '=', partner_id), ('type', '=', 'invoice')]",
        help="Contacto específico dentro de la empresa cliente que debe recibir "
             "esta factura. Útil cuando el cliente tiene múltiples departamentos "
             "o personas responsables de facturación."
    )
    
    # Campo calculado que muestra los pedidos relacionados con esta factura
    # Este campo es especialmente útil cuando una factura agrupa varios pedidos
    pedidos_relacionados = fields.Char(
        string="Pedidos Relacionados",
        compute='_compute_pedidos_relacionados',
        store=True,  # Se guarda en BD para mejorar rendimiento
        help="Lista de números de pedido de venta relacionados con esta factura. "
             "Se calcula automáticamente a partir de las líneas de factura."
    )
    
    # =========================================================================
    # MÉTODOS AUXILIARES PARA ORGANIZACIÓN DE DATOS
    # =========================================================================
    
    def _get_invoice_lines_by_order(self):
        """
        Agrupa las líneas de factura según el pedido de venta del que provienen.
        
        Este método es útil cuando se quiere mostrar la factura organizada por
        pedidos, lo cual es común cuando una factura incluye productos de
        múltiples pedidos diferentes.
        
        Returns:
            dict: Diccionario donde las claves son objetos sale.order y los
                  valores son recordsets de account.move.line
                  
        Ejemplo de uso:
            lines_by_order = invoice._get_invoice_lines_by_order()
            for order, lines in lines_by_order.items():
                print(f"Pedido {order.name} tiene {len(lines)} líneas")
        """
        self.ensure_one()  # Este método solo funciona con un registro a la vez
        result = {}
        
        # Paso 1: Recopilar todos los pedidos únicos relacionados con esta factura
        # Cada línea de factura puede estar vinculada a una línea de pedido,
        # y cada línea de pedido pertenece a un pedido completo
        orders = self.env['sale.order']
        for line in self.invoice_line_ids:
            for sale_line in line.sale_line_ids:
                if sale_line.order_id not in orders:
                    orders |= sale_line.order_id
        
        # Paso 2: Para cada pedido encontrado, agrupar sus líneas de factura
        for order in orders:
            result[order] = self.invoice_line_ids.filtered(
                lambda l: any(sl.order_id == order for sl in l.sale_line_ids)
            )
        
        # Paso 3: Capturar líneas que no están relacionadas con ningún pedido
        # Esto puede ocurrir cuando se añaden líneas manualmente a la factura
        no_order_lines = self.invoice_line_ids.filtered(
            lambda l: not l.sale_line_ids and l.display_type not in ('line_section', 'line_note')
        )
        if no_order_lines:
            result['no_order'] = no_order_lines
        
        return result

    @api.depends('invoice_origin', 'invoice_line_ids.sale_line_ids.order_id')
    def _compute_pedidos_relacionados(self):
        """
        Calcula y formatea los números de pedido relacionados con cada factura.
        
        Este método se ejecuta automáticamente cada vez que:
        - Se crea o modifica una factura
        - Se modifican las líneas de la factura
        - Se modifican los pedidos relacionados
        
        El campo calculado 'pedidos_relacionados' mostrará algo como:
        "SO001, SO002, SO003" si hay varios pedidos relacionados
        """
        for move in self:
            # Obtener todos los pedidos únicos vinculados a las líneas de factura
            order_ids = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            
            if order_ids:
                # Extraer los nombres de los pedidos (ej: SO001, SO002)
                order_refs = order_ids.mapped('name')
                
                # Eliminar duplicados usando set y convertir de vuelta a lista
                unique_refs = list(set(order_refs))
                
                # Unir en una cadena separada por comas
                move.pedidos_relacionados = ', '.join(sorted(unique_refs))
            else:
                # Si no hay pedidos vinculados, usar el campo invoice_origin
                # que a veces contiene referencias manuales de pedidos
                move.pedidos_relacionados = move.invoice_origin or ''
    
    def _get_report_base_filename(self):
        """
        Define el nombre base del archivo cuando se descarga el PDF de la factura.
        
        Este método se llama automáticamente por Odoo cuando el usuario descarga
        un reporte PDF. El nombre del archivo será el retornado aquí más la
        extensión .pdf
        
        Ejemplos de nombres generados:
        - Factura de cliente: "Factura - INV/2024/0001.pdf"
        - Factura de proveedor: "Factura Proveedor - BILL/2024/0050.pdf"
        - Asiento contable: "Asiento - MISC/2024/0123.pdf"
        """
        self.ensure_one()
        
        if self.is_sale_document():
            # Facturas y notas de crédito de clientes
            return 'Factura - %s' % (self.name)
        elif self.is_purchase_document():
            # Facturas y notas de crédito de proveedores
            return 'Factura Proveedor - %s' % (self.name)
        else:
            # Otros asientos contables
            return 'Asiento - %s' % (self.name)


class AccountMoveLine(models.Model):
    """
    Extensión del modelo de líneas de factura para facilitar la visualización
    de pedidos relacionados en cada línea.
    
    Este modelo es secundario pero útil para mostrar claramente en cada línea
    de qué pedido proviene el producto facturado.
    """
    
    _inherit = 'account.move.line'
    
    sale_order_reference = fields.Char(
        string="Pedido",
        compute='_compute_sale_order_reference',
        help="Número de pedido de venta relacionado con esta línea de factura. "
             "Si la línea proviene de múltiples pedidos (raro pero posible), "
             "se mostrarán todos separados por comas."
    )
    
    @api.depends('sale_line_ids')
    def _compute_sale_order_reference(self):
        """
        Calcula el número de pedido relacionado con cada línea de factura.
        
        Este campo calculado facilita mostrar en la plantilla de factura
        de qué pedido proviene cada producto, lo cual es muy útil cuando
        una factura agrupa productos de múltiples pedidos.
        """
        for line in self:
            if line.sale_line_ids:
                # Obtener todos los pedidos únicos relacionados con esta línea
                orders = line.sale_line_ids.mapped('order_id')
                # Crear string con los nombres separados por comas
                line.sale_order_reference = ', '.join(orders.mapped('name'))
            else:
                # Esta línea no está vinculada a ningún pedido
                line.sale_order_reference = ''
