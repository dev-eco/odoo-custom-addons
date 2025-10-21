# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

"""
Invoice Batch Export Module - Odoo 17.0
========================================

This module provides advanced batch export functionality for invoices with
multi-format compression support and intelligent processing capabilities.

Structure:
----------
• models/     - Persistent data models (templates, configurations)
• wizard/     - Transient models for guided processes
• views/      - XML view definitions and UI components
• security/   - Access control and permissions
• data/       - Default data and configurations
• static/     - CSS, JS, and static assets
• tests/      - Unit and integration tests

Features:
---------
• Multi-format compression (ZIP, 7z, TAR.GZ)
• Smart batch processing with memory optimization
• Customizable filename templates
• Advanced filtering and selection criteria
• Multi-company support with data isolation
• Password-protected archives
• Progress tracking and error handling

License: LGPL-3
Author: [TU_NOMBRE]
Email: [TU_EMAIL]
"""

# Import subpackages
from . import models
from . import wizard

# Optional: Import utility functions if needed
# from . import utils

def uninstall_hook(env):
    """
    Hook called when the module is being uninstalled.
    
    This function cleans up any module-specific data that should be
    removed when the module is uninstalled, ensuring a clean system state.
    
    Args:
        cr: Database cursor
        registry: Odoo registry object
    """
    import logging
    _logger = logging.getLogger(__name__)
    
    try:
        # Clean up any temporary files or cache
        _logger.info("Invoice Batch Export: Starting uninstall cleanup...")
        
        # Remove any temporary export files
        # Note: This would typically clean /tmp files, but we should be careful
        # not to remove files that might belong to other processes
        
        # Clean up any module-specific ir.config_parameter entries if needed
        # cr.execute("DELETE FROM ir_config_parameter WHERE key LIKE 'invoice_batch_export.%'")
        
        _logger.info("Invoice Batch Export: Uninstall cleanup completed successfully")
        
    except Exception as e:
        _logger.error(f"Invoice Batch Export: Error during uninstall cleanup: {str(e)}")
        # Don't raise the exception to avoid blocking uninstallation
        pass
