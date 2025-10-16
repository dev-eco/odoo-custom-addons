# -*- coding: utf-8 -*-
import io
import base64
import zipfile
import re
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class InvoiceExportWizard(models.TransientModel):
    """
    Wizard para exportar múltiples facturas en formato ZIP.
    
    ¿Por qué un TransientModel?
    - Los wizards en Odoo son modelos transitorios que solo existen temporalmente
    - Se eliminan automáticamente después de un tiempo (por defecto tras cerrar)
    - Son perfectos para acciones que no requieren almacenamiento permanente
    - Más eficientes en memoria que los modelos persistentes
    """
    _name = 'invoice.export.wizard'
    _description = 'Wizard para exportar facturas en ZIP'

    # CAMPOS DEL WIZARD
    # =================
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Seleccionadas',
        help='Las facturas que se exportarán al archivo ZIP'
    )
    
    include_customer_invoices = fields.Boolean(
        string='Incluir Facturas de Cliente',
        default=True,
        help='Si está marcado, exportará las facturas de venta (clientes)'
    )
    
    include_vendor_bills = fields.Boolean(
        string='Incluir Facturas de Proveedor',
        default=True,
        help='Si está marcado, exportará las facturas de compra (proveedores)'
    )
    
    date_from = fields.Date(
        string='Fecha Desde',
        help='Filtrar facturas desde esta fecha (opcional)'
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        help='Filtrar facturas hasta esta fecha (opcional)'
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicadas'),
        ('all', 'Todas')
    ], string='Estado', default='posted',
       help='Filtrar facturas por estado')
    
    zip_file = fields.Binary(
        string='Archivo ZIP',
        readonly=True,
        help='El archivo ZIP generado con las facturas'
    )
    
    zip_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
        help='Nombre del archivo ZIP descargado'
    )
    
    export_count = fields.Integer(
        string='Facturas Exportadas',
        readonly=True,
        help='Número de facturas incluidas en el ZIP'
    )

    # MÉTODOS DE VALIDACIÓN
    # =====================
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """
        Validar que el rango de fechas sea coherente.
        
        ¿Por qué usar @api.constrains?
        - Es un decorador que se ejecuta automáticamente cuando cambian estos campos
        - Garantiza la integridad de los datos antes de cualquier operación
        - Proporciona feedback inmediato al usuario si hay errores
        """
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                if wizard.date_from > wizard.date_to:
                    raise ValidationError(_(
                        'La fecha inicial no puede ser posterior a la fecha final.'
                    ))

    # MÉTODOS AUXILIARES PRIVADOS
    # ===========================
    
    def _sanitize_filename(self, name):
        """
        Limpiar un string para usarlo como nombre de archivo.
        
        Elimina o reemplaza caracteres que pueden causar problemas:
        - Caracteres especiales del sistema de archivos (/, \, :, etc.)
        - Espacios múltiples
        - Acentos y caracteres no ASCII (opcional)
        
        Args:
            name (str): El nombre original a limpiar
            
        Returns:
            str: El nombre sanitizado y seguro para usar en archivos
        """
        if not name:
            return 'sin_nombre'
        
        # Remover o reemplazar caracteres problemáticos
        # Los caracteres peligrosos incluyen: / \ : * ? " < > |
        name = re.sub(r'[/\\:*?"<>|]', '_', name)
        
        # Reemplazar espacios múltiples por uno solo
        name = re.sub(r'\s+', '_', name)
        
        # Eliminar guiones bajos múltiples
        name = re.sub(r'_+', '_', name)
        
        # Eliminar guiones bajos al inicio y final
        name = name.strip('_')
        
        # Limitar longitud (nombres de archivo muy largos causan problemas)
        # Dejamos espacio para el resto del nombre (fecha, número, etc.)
        if len(name) > 50:
            name = name[:50]
        
        return name or 'sin_nombre'

    def _generate_invoice_filename(self, invoice):
        """
        Generar un nombre descriptivo e informativo para cada factura.
        
        Formato: [TIPO]_[NÚMERO]_[PARTNER]_[FECHA].pdf
        
        Este formato es ideal porque:
        1. Comienza con el tipo (facilita agrupación alfabética)
        2. Incluye el número único de la factura (trazabilidad)
        3. Muestra el partner (identificación rápida)
        4. Termina con la fecha (orden cronológico)
        
        Args:
            invoice (account.move): La factura para la que generar el nombre
            
        Returns:
            str: Nombre de archivo formateado y sanitizado
        """
        # Determinar el tipo de documento
        if invoice.move_type == 'out_invoice':
            doc_type = 'CLIENTE'
        elif invoice.move_type == 'out_refund':
            doc_type = 'NC_CLIENTE'  # Nota de Crédito Cliente
        elif invoice.move_type == 'in_invoice':
            doc_type = 'PROVEEDOR'
        elif invoice.move_type == 'in_refund':
            doc_type = 'NC_PROVEEDOR'  # Nota de Crédito Proveedor
        else:
            doc_type = 'DOCUMENTO'
        
        # Obtener el número de factura (sin espacios ni caracteres raros)
        invoice_number = self._sanitize_filename(invoice.name or 'SIN_NUMERO')
        
        # Obtener el nombre del partner (cliente o proveedor)
        partner_name = self._sanitize_filename(
            invoice.partner_id.name or 'SIN_PARTNER'
        )
        
        # Formatear la fecha de la factura
        invoice_date = invoice.invoice_date or fields.Date.today()
        date_str = invoice_date.strftime('%Y-%m-%d')
        
        # Construir el nombre final
        filename = f"{doc_type}_{invoice_number}_{partner_name}_{date_str}.pdf"
        
        return filename

    def _get_invoice_pdf(self, invoice):
        """
        Obtener el PDF de una factura.
        
        Odoo almacena los PDFs de dos formas posibles:
        1. Como adjuntos (ir.attachment) vinculados a la factura
        2. Generándolos on-the-fly con el sistema de informes
        
        Este método intenta primero buscar el PDF ya generado (más rápido),
        y si no existe, lo genera utilizando el motor de reportes de Odoo.
        
        Args:
            invoice (account.move): La factura de la cual obtener el PDF
            
        Returns:
            bytes: El contenido del PDF en formato binario
            
        Raises:
            UserError: Si no se puede generar o encontrar el PDF
        """
        # Buscar primero si ya existe un PDF adjunto
        # ¿Por qué buscar primero? Porque es mucho más rápido que regenerar
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1, order='create_date desc')
        
        if attachment and attachment.datas:
            # Decodificar el base64 a bytes
            return base64.b64decode(attachment.datas)
        
        # Si no existe adjunto, generar el PDF usando el sistema de reportes
        # ¿Qué es 'account.account_invoices'?
        # Es el ID XML del reporte de facturas definido en el módulo account
        try:
            pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                'account.account_invoices',
                invoice.ids
            )
            return pdf_content
            
        except Exception as e:
            _logger.error(
                f"Error generando PDF para factura {invoice.name}: {str(e)}"
            )
            raise UserError(_(
                'No se pudo generar el PDF para la factura %s. '
                'Error: %s'
            ) % (invoice.name, str(e)))

    def _filter_invoices(self):
        """
        Filtrar las facturas según los criterios seleccionados en el wizard.
        
        Este método construye dinámicamente un domain de Odoo basado en:
        - Las facturas ya seleccionadas (si las hay)
        - Los tipos de documentos a incluir (cliente/proveedor)
        - El rango de fechas
        - El estado de las facturas
        
        Returns:
            recordset: Las facturas filtradas que cumplen todos los criterios
        """
        domain = []
        
        # Si hay facturas preseleccionadas, usar solo esas
        if self.invoice_ids:
            domain.append(('id', 'in', self.invoice_ids.ids))
        
        # Filtrar por tipo de documento
        move_types = []
        if self.include_customer_invoices:
            move_types.extend(['out_invoice', 'out_refund'])
        if self.include_vendor_bills:
            move_types.extend(['in_invoice', 'in_refund'])
        
        if move_types:
            domain.append(('move_type', 'in', move_types))
        else:
            # Si no se seleccionó ningún tipo, retornar vacío
            return self.env['account.move']
        
        # Filtrar por fechas
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        
        # Filtrar por estado
        if self.state == 'draft':
            domain.append(('state', '=', 'draft'))
        elif self.state == 'posted':
            domain.append(('state', '=', 'posted'))
        # Si es 'all' no añadimos filtro de estado
        
        # Buscar facturas que cumplan todos los criterios
        invoices = self.env['account.move'].search(domain)
        
        return invoices

    # ACCIÓN PRINCIPAL
    # ================
    
    def action_export_invoices(self):
        """
        Acción principal que ejecuta todo el proceso de exportación.
        
        Este método orquesta todo el flujo:
        1. Validar que haya facturas para exportar
        2. Filtrar las facturas según criterios
        3. Crear el archivo ZIP en memoria
        4. Generar PDFs y añadirlos al ZIP
        5. Preparar el archivo para descarga
        6. Mostrar resultado al usuario
        
        El uso de un buffer en memoria (io.BytesIO) es importante porque:
        - No requiere escribir archivos temporales en disco
        - Es más rápido y seguro
        - Se limpia automáticamente de la memoria
        - Funciona bien en entornos con múltiples workers
        
        Returns:
            dict: Acción de Odoo para mostrar el wizard con el archivo descargable
        """
        self.ensure_one()  # Asegurar que solo se procesa un wizard a la vez
        
        # Obtener las facturas a exportar
        invoices = self._filter_invoices()
        
        # Validar que haya facturas
        if not invoices:
            raise UserError(_(
                'No se encontraron facturas para exportar con los criterios seleccionados.\n'
                'Por favor, ajusta los filtros e intenta nuevamente.'
            ))
        
        _logger.info(f"Iniciando exportación de {len(invoices)} facturas")
        
        # Crear un buffer en memoria para el ZIP
        # ¿Por qué io.BytesIO? Porque necesitamos un objeto tipo file en memoria
        # sin crear archivos temporales en el disco
        zip_buffer = io.BytesIO()
        
        # Contador de facturas exportadas exitosamente
        successful_exports = 0
        failed_exports = []
        
        # Crear el archivo ZIP
        # ¿Por qué ZIP_DEFLATED? Es el método de compresión estándar y eficiente
        # Compresslevel=6 balancea velocidad y tamaño (0=sin compresión, 9=máxima)
        with zipfile.ZipFile(
            zip_buffer,
            'w',
            zipfile.ZIP_DEFLATED,
            compresslevel=6
        ) as zip_file:
            
            # Procesar cada factura
            for invoice in invoices:
                try:
                    # Generar nombre de archivo descriptivo
                    filename = self._generate_invoice_filename(invoice)
                    
                    # Obtener el PDF de la factura
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    # Añadir el PDF al ZIP con su nombre personalizado
                    # writestr escribe datos binarios directamente sin crear archivo
                    zip_file.writestr(filename, pdf_content)
                    
                    successful_exports += 1
                    _logger.info(f"Factura {invoice.name} exportada como {filename}")
                    
                except Exception as e:
                    # Registrar error pero continuar con las demás facturas
                    failed_exports.append((invoice.name, str(e)))
                    _logger.error(
                        f"Error exportando factura {invoice.name}: {str(e)}"
                    )
        
        # Si todas las facturas fallaron, mostrar error
        if successful_exports == 0:
            error_msg = _('No se pudo exportar ninguna factura.\n\nDetalles:\n')
            for invoice_name, error in failed_exports:
                error_msg += f"- {invoice_name}: {error}\n"
            raise UserError(error_msg)
        
        # Obtener el contenido del ZIP del buffer
        zip_content = zip_buffer.getvalue()
        
        # Cerrar el buffer (liberar memoria)
        zip_buffer.close()
        
        # Generar nombre para el archivo ZIP
        # Incluye fecha y hora para evitar conflictos y facilitar organización
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"facturas_export_{timestamp}.zip"
        
        # Guardar el ZIP en el wizard para descarga
        # base64.b64encode porque Odoo almacena archivos binarios en base64
        self.write({
            'zip_file': base64.b64encode(zip_content),
            'zip_filename': zip_filename,
            'export_count': successful_exports,
        })
        
        # Mostrar advertencia si algunas facturas fallaron
        if failed_exports:
            error_list = '\n'.join([
                f"- {name}: {error}" for name, error in failed_exports
            ])
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Exportación Parcialmente Exitosa'),
                    'message': _(
                        f'Se exportaron {successful_exports} de {len(invoices)} facturas.\n\n'
                        f'Facturas con errores:\n{error_list}'
                    ),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        _logger.info(
            f"Exportación completada: {successful_exports} facturas "
            f"en {zip_filename}"
        )
        
        # Retornar la acción para mostrar el wizard con el botón de descarga
        # ¿Por qué este retorno? Permite al usuario ver el resultado y descargar
        return {
            'type': 'ir.actions.act_window',
            'name': _('Exportación Completada'),
            'res_model': 'invoice.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',  # Abrir en modal
            'context': self.env.context,
        }

    # MÉTODO PARA INICIALIZACIÓN DESDE VISTA DE LISTA
    # ===============================================
    
    @api.model
    def default_get(self, fields_list):
        """
        Método especial que se llama cuando se crea el wizard.
        
        ¿Para qué sirve default_get?
        - Se ejecuta automáticamente al abrir el wizard
        - Permite preconfigurarlo con datos del contexto
        - En este caso, obtiene las facturas seleccionadas en la lista
        
        El contexto 'active_ids' es mágico en Odoo:
        - Se llena automáticamente con los IDs de registros seleccionados
        - Solo existe cuando el wizard se abre desde una acción en la lista
        - Es None si se abre desde el menú o sin selección previa
        
        Args:
            fields_list (list): Lista de campos a obtener valores por defecto
            
        Returns:
            dict: Diccionario con valores por defecto para los campos del wizard
        """
        res = super(InvoiceExportWizard, self).default_get(fields_list)
        
        # Obtener las facturas seleccionadas del contexto
        # El contexto es un diccionario especial de Odoo que viaja con cada acción
        invoice_ids = self.env.context.get('active_ids', [])
        
        if invoice_ids and 'invoice_ids' in fields_list:
            # Verificar que los IDs corresponden a facturas válidas
            invoices = self.env['account.move'].browse(invoice_ids)
            
            # Filtrar solo documentos que sean realmente facturas
            # (no asientos contables regulares)
            valid_invoices = invoices.filtered(
                lambda inv: inv.move_type in [
                    'out_invoice', 'out_refund',
                    'in_invoice', 'in_refund'
                ]
            )
            
            if valid_invoices:
                res['invoice_ids'] = [(6, 0, valid_invoices.ids)]
                # ¿Qué significa (6, 0, ids)?
                # Es la sintaxis especial de Odoo para Many2many:
                # 6 = reemplazar toda la lista con estos IDs
                # 0 = ID del comando (siempre 0 para el comando 6)
                # ids = lista de IDs a establecer
                
                _logger.info(
                    f"Wizard inicializado con {len(valid_invoices)} "
                    f"facturas preseleccionadas"
                )
        
        return res
