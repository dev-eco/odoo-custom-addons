# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

"""
Models Package - Invoice Batch Export
=====================================

This package contains persistent data models that store configuration
and template information for the batch export functionality.

Models included:
---------------
• export_template.py - Templates for filename generation patterns
• compression_config.py - Configuration for compression algorithms
• export_history.py - Audit trail of export operations (future)

Model Hierarchy:
---------------
┌─ res.company
├─ export.template (Many2one to res.company)
├─ compression.config (Many2one to res.company)  
└─ export.history (Many2one to res.users, res.company)

Design Principles:
-----------------
• Multi-company support: All models include company_id field
• Audit trail: Track who, when, and what was exported
• Extensibility: Easy to add new template variables
• Performance: Efficient queries with proper indexing
• Security: Access control integrated at model level
"""

# Import all model files
from . import export_template

# Future models (uncomment when implemented):
# from . import compression_config
# from . import export_history
