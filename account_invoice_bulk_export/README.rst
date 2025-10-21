====================
Invoice Batch Export
====================

Advanced batch export module for Odoo 17.0 with multi-format compression support
and intelligent processing capabilities.

Features
========

🚀 **Multi-Format Compression**
   * ZIP (Fast, Balanced, Maximum compression)
   * 7-Zip (Normal, Ultra compression)
   * TAR.GZ (Unix/Linux standard)
   * Password-protected archives

📊 **Smart Processing**
   * Configurable batch sizes for memory optimization
   * Progress tracking for large exports
   * Robust error handling with detailed logging
   * Resume functionality for interrupted exports

🎯 **Advanced Filtering**
   * Date ranges with flexible criteria
   * Document types (invoices, bills, credit notes)
   * Partner-specific filtering
   * Multi-company support with data isolation

📝 **Intelligent Filename Generation**
   * Customizable naming templates
   * Company-specific patterns
   * Automatic conflict resolution
   * Special character sanitization

Installation
============

1. Install Python dependencies::

    pip install py7zr

2. Copy module to your Odoo addons directory
3. Update app list in Odoo
4. Install "Invoice Batch Export" module

Usage
=====

**From Invoice List View:**
1. Select invoices in list view
2. Use "Action" → "📦 Export in Batch"
3. Configure compression and options
4. Download generated archive

**From Accounting Menu:**
1. Go to Accounting → Reports → 📦 Batch Export
2. Configure filters and criteria
3. Select compression format
4. Process and download

Configuration
=============

**Naming Templates:**
Create custom filename templates in:
Accounting → Reports → 📦 Batch Export → ⚙️ Configuration → Naming Templates

**Available Variables:**
* ``{type}`` - Document type (CUSTOMER, VENDOR, etc.)
* ``{number}`` - Invoice number  
* ``{partner}`` - Partner name
* ``{date}`` - Invoice date (YYYY-MM-DD)
* ``{year}`` - Year (YYYY)
* ``{month}`` - Month (MM)
* ``{company}`` - Company name
* ``{reference}`` - Partner reference

**Example Templates:**
* Standard: ``{type}_{number}_{partner}_{date}.pdf``
* Date organized: ``{year}-{month}/{type}_{number}_{partner}.pdf``
* Client focused: ``{partner}_{reference}_{type}_{number}.pdf``

Performance
===========

**Recommended Limits:**
* 1-50 invoices: Instant processing
* 51-200 invoices: Fast processing (1-5 minutes)
* 201-500 invoices: Moderate processing (5-15 minutes)
* 500+ invoices: Use date range filtering

**Memory Usage:**
* Batch size 50: ~100MB RAM
* Batch size 100: ~200MB RAM
* 7-Zip compression: +50% processing time, -30% file size

Security
========

**Access Control:**
* Account Users: Can use export wizard
* Account Managers: Can manage templates and configuration
* Multi-company: Automatic data isolation

**Data Protection:**
* Password-protected archives available
* Audit trail of all exports
* No temporary files left on server

Troubleshooting
===============

**Common Issues:**

*Module not visible:*
  Check that ``py7zr`` is installed and Odoo service restarted

*PDF generation errors:*
  Verify ``wkhtmltopdf`` is properly installed with patched qt

*Memory errors with large exports:*
  Reduce batch size or use date range filtering

*7-Zip format unavailable:*
  Install py7zr: ``pip install py7zr``

Support
=======

:Author: [TU_NOMBRE]
:Email: tu.email@dominio.com
:Website: https://tu-sitio-web.com
:Documentation: https://tu-sitio-web.com/docs/invoice-batch-export
:License: LGPL-3

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/tu-usuario/invoice-batch-export/issues>`_.
Please check existing issues before creating new ones.

Credits
=======

**Contributors:**
* [TU_NOMBRE] <tu.email@dominio.com>

**Libraries:**
* py7zr - 7-Zip compression support
* Odoo - ERP framework

**Inspiration:**
* Community requests for better invoice export functionality
* Accounting firms workflow optimization needs
