# -*- coding: utf-8 -*-
# © 2025 [TU_NOMBRE] - [TU_EMAIL]
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

import base64
import json
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError

class TestBatchExport(TransactionCase):
    """
    Tests para el módulo de exportación masiva de facturas
    
    Estos tests verifican la funcionalidad principal del wizard de exportación
    y la generación de plantillas de nomenclatura.
    """

    def setUp(self):
        super().setUp()
        
        # Modelos necesarios
        self.wizard_model = self.env['batch.export.wizard']
        self.template_model = self.env['export.template']
        self.invoice_model = self.env['account.move']
        
        # Crear empresa de prueba
        self.test_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.env.ref('base.EUR').id,
        })
        
        # Crear partner de prueba
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'is_company': True,
        })
        
        # Crear factura de prueba
        self.test_invoice = self.invoice_model.create({
            'partner_id': self.test_partner.id,
            'move_type': 'out_invoice',
            'company_id': self.test_company.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Product',
                'quantity': 1,
                'price_unit': 100.0,
            })],
        })
        
        # Crear plantilla de prueba
        self.test_template = self.template_model.create({
            'name': 'Test Template',
            'pattern': '{type}_{number}_{partner}_{date}.pdf',
            'company_id': self.test_company.id,
            'is_default': True,
        })

    def test_wizard_creation(self):
        """Test de creación básica del wizard"""
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
            'compression_format': 'zip_balanced',
        })
        
        self.assertEqual(wizard.state, 'draft')
        self.assertEqual(wizard.compression_format, 'zip_balanced')
        self.assertTrue(wizard.include_customer_invoices)
        self.assertTrue(wizard.include_vendor_bills)

    def test_template_pattern_validation(self):
        """Test de validación de patrones de plantilla"""
        # Patrón válido
        template = self.template_model.create({
            'name': 'Valid Template',
            'pattern': '{type}_{number}_{partner}.pdf',
            'company_id': self.test_company.id,
        })
        self.assertTrue(template.id)
        
        # Patrón inválido - sin {number}
        with self.assertRaises(ValidationError):
            self.template_model.create({
                'name': 'Invalid Template',
                'pattern': '{type}_{partner}.pdf',  # Falta {number}
                'company_id': self.test_company.id,
            })
        
        # Patrón inválido - variable inexistente
        with self.assertRaises(ValidationError):
            self.template_model.create({
                'name': 'Invalid Template 2',
                'pattern': '{type}_{number}_{invalid_var}.pdf',
                'company_id': self.test_company.id,
            })

    def test_template_filename_generation(self):
        """Test de generación de nombres de archivo"""
        filename = self.test_template.generate_filename(self.test_invoice)
        
        # Verificar que el nombre contiene los elementos esperados
        self.assertIn('CLIENTE', filename)  # Tipo de documento
        self.assertIn('TEST_PARTNER', filename)  # Nombre del partner
        self.assertTrue(filename.endswith('.pdf'))
        
        # Verificar que no hay caracteres problemáticos
        problematic_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in problematic_chars:
            self.assertNotIn(char, filename)

    def test_wizard_invoice_filtering(self):
        """Test de filtrado de facturas"""
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
            'include_customer_invoices': True,
            'include_vendor_bills': False,
            'state_filter': 'all',
        })
        
        invoices = wizard._get_filtered_invoices()
        
        # Debería incluir nuestra factura de cliente
        self.assertIn(self.test_invoice, invoices)
        
        # Verificar que no incluye facturas de proveedor
        vendor_invoice = self.invoice_model.create({
            'partner_id': self.test_partner.id,
            'move_type': 'in_invoice',
            'company_id': self.test_company.id,
        })
        
        invoices = wizard._get_filtered_invoices()
        self.assertNotIn(vendor_invoice, invoices)

    def test_batch_size_validation(self):
        """Test de validación del tamaño de lote"""
        # Tamaño válido
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
            'batch_size': 50,
        })
        self.assertEqual(wizard.batch_size, 50)
        
        # Tamaño inválido - demasiado pequeño
        with self.assertRaises(ValidationError):
            self.wizard_model.create({
                'company_id': self.test_company.id,
                'batch_size': 0,
            })
        
        # Tamaño inválido - demasiado grande
        with self.assertRaises(ValidationError):
            self.wizard_model.create({
                'company_id': self.test_company.id,
                'batch_size': 1001,
            })

    def test_date_range_validation(self):
        """Test de validación de rango de fechas"""
        from datetime import date, timedelta
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Rango válido
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
            'date_from': yesterday,
            'date_to': tomorrow,
        })
        self.assertTrue(wizard.id)
        
        # Rango inválido - fecha inicio posterior a fecha fin
        with self.assertRaises(ValidationError):
            self.wizard_model.create({
                'company_id': self.test_company.id,
                'date_from': tomorrow,
                'date_to': yesterday,
            })

    def test_default_template_creation(self):
        """Test de creación de plantilla por defecto"""
        # Eliminar plantilla por defecto existente
        self.test_template.write({'is_default': False})
        
        # Solicitar plantilla por defecto
        default_template = self.template_model.get_default_template(
            self.test_company.id
        )
        
        self.assertTrue(default_template.id)
        self.assertTrue(default_template.is_default)
        self.assertEqual(default_template.company_id, self.test_company)

    def test_single_default_template_constraint(self):
        """Test de constraint de una sola plantilla por defecto por empresa"""
        # Intentar crear segunda plantilla por defecto
        with self.assertRaises(ValidationError):
            self.template_model.create({
                'name': 'Second Default',
                'pattern': '{number}.pdf',
                'company_id': self.test_company.id,
                'is_default': True,  # Debería fallar
            })

    @patch('odoo.addons.invoice_batch_export.wizard.batch_export_wizard.zipfile.ZipFile')
    def test_zip_archive_creation(self, mock_zipfile):
        """Test de creación de archivo ZIP (mockeado)"""
        # Configurar mock
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
            'compression_format': 'zip_balanced',
            'invoice_ids': [(6, 0, [self.test_invoice.id])],
        })
        
        # Mock del método de generación de PDF
        with patch.object(wizard, '_generate_invoice_pdf') as mock_pdf:
            mock_pdf.return_value = b'fake_pdf_content'
            
            # Ejecutar creación de archivo
            result = wizard._create_zip_archive([self.test_invoice], self.test_template)
            
            # Verificar que se llamó al ZIP
            mock_zip.writestr.assert_called_once()
            mock_pdf.assert_called_once_with(self.test_invoice)

    def test_file_extension_detection(self):
        """Test de detección de extensión de archivo"""
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
        })
        
        test_cases = [
            ('zip_fast', 'zip'),
            ('zip_balanced', 'zip'),
            ('7z_normal', '7z'),
            ('tar_gz', 'tar.gz'),
        ]
        
        for format_name, expected_ext in test_cases:
            wizard.compression_format = format_name
            ext = wizard._get_file_extension()
            self.assertEqual(ext, expected_ext)

    def test_wizard_with_preselected_invoices(self):
        """Test del wizard con facturas preseleccionadas"""
        wizard = self.wizard_model.with_context(
            active_model='account.move',
            active_ids=[self.test_invoice.id]
        ).create({
            'company_id': self.test_company.id,
        })
        
        # Verificar que las facturas fueron preseleccionadas
        self.assertIn(self.test_invoice, wizard.invoice_ids)

    def test_template_usage_stats_update(self):
        """Test de actualización de estadísticas de uso de plantilla"""
        initial_count = self.test_template.usage_count
        initial_last_used = self.test_template.last_used
        
        # Generar nombre de archivo (debería actualizar estadísticas)
        self.test_template.generate_filename(self.test_invoice)
        
        # Verificar actualización
        self.assertEqual(self.test_template.usage_count, initial_count + 1)
        self.assertNotEqual(self.test_template.last_used, initial_last_used)

    def test_compression_format_selection_validation(self):
        """Test de validación de formatos de compresión disponibles"""
        wizard = self.wizard_model.create({
            'company_id': self.test_company.id,
        })
        
        # Obtener formatos disponibles
        formats = wizard._get_available_compression_formats()
        
        # Verificar que hay formatos básicos
        format_values = [f[0] for f in formats]
        self.assertIn('zip_balanced', format_values)
        self.assertIn('tar_gz', format_values)
        
        # Los formatos 7z dependen de si py7zr está instalado
        # No fallará si no está disponible

    def tearDown(self):
        """Limpieza después de cada test"""
        # Los datos de prueba se limpian automáticamente por TransactionCase
        super().tearDown()


class TestExportTemplate(TransactionCase):
    """Tests específicos para el modelo de plantillas de exportación"""

    def setUp(self):
        super().setUp()
        self.template_model = self.env['export.template']
        self.company = self.env.ref('base.main_company')

    def test_sanitize_filename(self):
        """Test de sanitización de nombres de archivo"""
        template = self.template_model.create({
            'name': 'Test Template',
            'pattern': '{number}.pdf',
            'company_id': self.company.id,
        })
        
        test_cases = [
            ('Normal Name', 'Normal_Name'),
            ('Name/With\\Slashes', 'Name_With_Slashes'),
            ('Name:With*Special?Chars', 'Name_With_Special_Chars'),
            ('Name   With   Spaces', 'Name_With_Spaces'),
            ('___Multiple___Underscores___', 'Multiple_Underscores'),
        ]
        
        for input_name, expected_output in test_cases:
            result = template._sanitize_filename(input_name)
            self.assertEqual(result, expected_output)

    def test_document_type_detection(self):
        """Test de detección de tipo de documento"""
        template = self.template_model.create({
            'name': 'Test Template',
            'pattern': '{type}.pdf',
            'company_id': self.company.id,
        })
        
        # Mock de facturas con diferentes tipos
        mock_invoices = [
            MagicMock(move_type='out_invoice'),
            MagicMock(move_type='out_refund'),
            MagicMock(move_type='in_invoice'),
            MagicMock(move_type='in_refund'),
        ]
        
        expected_types = ['CLIENTE', 'NC_CLIENTE', 'PROVEEDOR', 'NC_PROVEEDOR']
        
        for mock_invoice, expected_type in zip(mock_invoices, expected_types):
            result = template._get_document_type(mock_invoice)
            self.assertEqual(result, expected_type)

    def test_example_output_computation(self):
        """Test de cálculo de ejemplo de salida"""
        template = self.template_model.create({
            'name': 'Test Template',
            'pattern': '{type}_{number}_{partner}_{date}.pdf',
            'company_id': self.company.id,
        })
        
        # El ejemplo debería generarse automáticamente
        self.assertTrue(template.example_output)
        self.assertIn('CLIENTE', template.example_output)
        self.assertIn('INV-2024-001', template.example_output)
        self.assertTrue(template.example_output.endswith('.pdf'))
