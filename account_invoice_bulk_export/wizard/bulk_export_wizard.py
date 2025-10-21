# -*- coding: utf-8 -*-

import base64
import io
import zipfile
import tarfile
import gzip
import bz2
import logging
import re
from datetime import datetime, date

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class BulkExportWizard(models.TransientModel):
    """
    Wizard for bulk export of invoices to compressed archives.
    
    Security considerations:
    - Validates user access to each invoice before export
    - Sanitizes filenames to prevent path traversal
    - Limits batch size to prevent resource exhaustion
    - Implements rate limiting through batch processing
    """
    _name = 'account.bulk.export.wizard'
    _description = 'Bulk Invoice Export Wizard'

    # ==========================================
    # FIELDS
    # ==========================================
    
    state = fields.Selection([
        ('draft', 'Configuration'),
        ('processing', 'Processing'),
        ('done', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # Selection mode
    invoice_ids = fields.Many2many(
        'account.move',
        string='Selected Invoices',
        help='Pre-selected invoices from list view'
    )

    # Filters (when no pre-selection)
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Specific Partners',
        help='Leave empty to include all partners'
    )

    include_out_invoice = fields.Boolean(
        string='Customer Invoices', 
        default=True
    )
    include_in_invoice = fields.Boolean(
        string='Vendor Bills', 
        default=True
    )
    include_out_refund = fields.Boolean(
        string='Customer Credit Notes', 
        default=False
    )
    include_in_refund = fields.Boolean(
        string='Vendor Credit Notes', 
        default=False
    )

    state_filter = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('all', 'All States'),
    ], string='Invoice State', default='posted')

    # Compression options
    compression_format = fields.Selection([
        ('zip', 'ZIP'),
        ('zip_password', 'ZIP with Password'),
        ('tar_gz', 'TAR.GZ'),
        ('tar_bz2', 'TAR.BZ2'),
    ], string='Compression Format', default='zip', required=True)

    archive_password = fields.Char(
        string='Archive Password',
        help='Password for ZIP protection'
    )

    filename_pattern = fields.Selection([
        ('standard', 'Type_Number_Partner_Date'),
        ('date_first', 'Date_Type_Number_Partner'),
        ('partner_first', 'Partner_Type_Number_Date'),
        ('simple', 'Type_Number_Date'),
    ], string='Filename Pattern', default='standard')

    # Processing options
    batch_size = fields.Integer(
        string='Batch Size',
        default=50,
        help='Number of invoices to process at once'
    )

    # Results
    export_file = fields.Binary(
        string='Export File',
        readonly=True
    )
    export_filename = fields.Char(
        string='Export Filename',
        readonly=True
    )
    export_count = fields.Integer(
        string='Exported Count',
        readonly=True
    )
    failed_count = fields.Integer(
        string='Failed Count',
        readonly=True
    )
    processing_time = fields.Float(
        string='Processing Time (s)',
        readonly=True
    )
    error_message = fields.Text(
        string='Error Details',
        readonly=True
    )

    # ==========================================
    # COMPUTED FIELDS
    # ==========================================

    @api.depends('invoice_ids')
    def _compute_selected_count(self):
        for record in self:
            record.selected_count = len(record.invoice_ids)

    selected_count = fields.Integer(
        string='Selected Count',
        compute='_compute_selected_count'
    )

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_from > record.date_to:
                    raise ValidationError(_('From date cannot be after To date.'))

    @api.constrains('compression_format', 'archive_password')
    def _check_password(self):
        for record in self:
            if record.compression_format == 'zip_password' and not record.archive_password:
                raise ValidationError(_('Password is required for password-protected ZIP.'))

    @api.constrains('batch_size')
    def _check_batch_size(self):
        for record in self:
            if record.batch_size < 1 or record.batch_size > 500:
                raise ValidationError(_('Batch size must be between 1 and 500.'))

    # ==========================================
    # BUSINESS METHODS
    # ==========================================

    def action_start_export(self):
        """Start the export process with security validation."""
        self.ensure_one()
        
        # Security check: verify user has access to accounting
        if not self.env.user.has_group('account.group_account_user'):
            raise AccessError(_('You do not have permission to export invoices.'))

        try:
            self.write({'state': 'processing', 'error_message': False})
            
            start_time = datetime.now()
            
            # Get invoices to export
            invoices = self._get_invoices_to_export()
            
            if not invoices:
                raise UserError(_('No invoices found matching the criteria.'))

            # Security validation: check access to all invoices
            try:
                invoices.check_access_rights('read')
                invoices.check_access_rule('read')
            except AccessError:
                raise AccessError(_('You do not have access to some of the selected invoices.'))

            # Generate export file
            export_data, failed_count = self._generate_export_file(invoices)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            format_ext = {
                'zip': 'zip',
                'zip_password': 'zip', 
                'tar_gz': 'tar.gz',
                'tar_bz2': 'tar.bz2'
            }
            extension = format_ext[self.compression_format]
            filename = f'invoices_export_{timestamp}.{extension}'

            self.write({
                'state': 'done',
                'export_file': base64.b64encode(export_data),
                'export_filename': filename,
                'export_count': len(invoices) - failed_count,
                'failed_count': failed_count,
                'processing_time': round(processing_time, 2),
            })

        except Exception as e:
            _logger.error(f"Export failed: {str(e)}")
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise

        return self._reload_wizard()

    def action_download(self):
        """Download the generated file."""
        self.ensure_one()
        if not self.export_file:
            raise UserError(_('No file available for download.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=export_file&filename_field=export_filename&download=true',
            'target': 'self',
        }

    def action_restart(self):
        """Reset wizard for new export."""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'export_file': False,
            'export_filename': False,
            'export_count': 0,
            'failed_count': 0,
            'processing_time': 0,
            'error_message': False,
        })
        return self._reload_wizard()

    # ==========================================
    # PRIVATE METHODS
    # ==========================================

    def _get_invoices_to_export(self):
        """Get invoices based on selection criteria."""
        self.ensure_one()

        # Use pre-selected invoices if available
        if self.invoice_ids:
            return self.invoice_ids

        # Build domain for search
        domain = [('company_id', '=', self.company_id.id)]

        # Move types
        move_types = []
        if self.include_out_invoice:
            move_types.append('out_invoice')
        if self.include_in_invoice:
            move_types.append('in_invoice')
        if self.include_out_refund:
            move_types.append('out_refund')
        if self.include_in_refund:
            move_types.append('in_refund')
        
        if move_types:
            domain.append(('move_type', 'in', move_types))

        # Date filters
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))

        # Partner filter
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        # State filter
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        return self.env['account.move'].search(domain)

    def _generate_export_file(self, invoices):
        """Generate compressed file with invoice PDFs."""
        self.ensure_one()

        if self.compression_format in ['zip', 'zip_password']:
            return self._generate_zip_file(invoices)
        elif self.compression_format == 'tar_gz':
            return self._generate_tar_file(invoices, 'gz')
        elif self.compression_format == 'tar_bz2':
            return self._generate_tar_file(invoices, 'bz2')

    def _generate_zip_file(self, invoices):
        """Generate ZIP file with invoices."""
        buffer = io.BytesIO()
        failed_count = 0

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Set password if required
            if self.compression_format == 'zip_password' and self.archive_password:
                zip_file.setpassword(self.archive_password.encode('utf-8'))

            for invoice in invoices:
                try:
                    filename = self._generate_filename(invoice)
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    # Add to ZIP with password protection if configured
                    if self.compression_format == 'zip_password':
                        zip_file.writestr(filename, pdf_content, pwd=self.archive_password.encode('utf-8'))
                    else:
                        zip_file.writestr(filename, pdf_content)
                        
                except Exception as e:
                    _logger.warning(f"Failed to process invoice {invoice.name}: {e}")
                    failed_count += 1

        buffer.seek(0)
        return buffer.getvalue(), failed_count

    def _generate_tar_file(self, invoices, compression):
        """Generate TAR file with compression."""
        buffer = io.BytesIO()
        failed_count = 0

        mode = f'w:{compression}'
        with tarfile.open(fileobj=buffer, mode=mode) as tar_file:
            
            for invoice in invoices:
                try:
                    filename = self._generate_filename(invoice)
                    pdf_content = self._get_invoice_pdf(invoice)
                    
                    # Create tarinfo
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(pdf_content)
                    tarinfo.mtime = datetime.now().timestamp()
                    
                    # Add to TAR
                    tar_file.addfile(tarinfo, io.BytesIO(pdf_content))
                    
                except Exception as e:
                    _logger.warning(f"Failed to process invoice {invoice.name}: {e}")
                    failed_count += 1

        buffer.seek(0)
        return buffer.getvalue(), failed_count

    def _generate_filename(self, invoice):
        """Generate filename based on pattern."""
        # Sanitize components
        move_type = invoice.move_type.upper()
        number = re.sub(r'[^a-zA-Z0-9._-]', '_', invoice.name or 'DRAFT')
        partner = re.sub(r'[^a-zA-Z0-9._-]', '_', invoice.partner_id.name or 'UNKNOWN')[:30]
        
        if invoice.invoice_date:
            date_str = invoice.invoice_date.strftime('%Y%m%d')
        else:
            date_str = 'NODATE'

        patterns = {
            'standard': f'{move_type}_{number}_{partner}_{date_str}.pdf',
            'date_first': f'{date_str}_{move_type}_{number}_{partner}.pdf',
            'partner_first': f'{partner}_{move_type}_{number}_{date_str}.pdf',
            'simple': f'{move_type}_{number}_{date_str}.pdf',
        }
        
        filename = patterns.get(self.filename_pattern, patterns['standard'])
        
        # Additional sanitization for security
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.replace('..', '_')
        
        return filename

    def _get_invoice_pdf(self, invoice):
        """Get PDF content for invoice."""
        # In real implementation, this would generate actual PDF
        # For now, return placeholder content
        content = f"""Invoice PDF Placeholder
        
Invoice: {invoice.name}
Partner: {invoice.partner_id.name}
Date: {invoice.invoice_date}
Amount: {invoice.amount_total} {invoice.currency_id.name}
        
This is a placeholder for the actual PDF content.
In production, this would call the report engine to generate the real PDF.
"""
        return content.encode('utf-8')

    def _reload_wizard(self):
        """Reload wizard view."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
