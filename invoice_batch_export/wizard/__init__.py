# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

"""
Wizards Package - Invoice Batch Export
======================================

This package contains transient models (wizards) that guide users through
complex processes like batch export configuration and execution.

Wizards included:
----------------
• batch_export_wizard.py - Main export wizard with multi-format support

Wizard Design Principles:
------------------------
• Transient models: Data is automatically cleaned up after use
• Step-by-step guidance: Complex processes broken into logical steps
• Input validation: Prevent errors before processing starts
• Progress feedback: Users see what's happening during long operations
• Error resilience: Handle failures gracefully with clear messages

Wizard Lifecycle:
----------------
1. Creation: User opens wizard (either from menu or action)
2. Configuration: User sets filters and options
3. Validation: System checks inputs and availability
4. Processing: Actual work is performed (export generation)
5. Results: User downloads file and sees summary
6. Cleanup: Transient records are automatically removed

Performance Considerations:
--------------------------
• Large exports are processed in batches to avoid memory issues
• PDF generation is optimized with caching where possible
• Progress tracking allows users to monitor long-running exports
• Error handling ensures partial results are not lost
"""

# Import all wizard models
from . import batch_export_wizard

# Future wizards (uncomment when implemented):
# from . import bulk_import_wizard
# from . import template_builder_wizard
# from . import migration_wizard
