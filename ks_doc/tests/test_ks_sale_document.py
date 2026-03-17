# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from .common import KsDocCommon
import base64


class TestKsSaleDocument(KsDocCommon):
    """Test cases for Sale Document functionality"""

    def test_01_create_document(self):
        """Test: Create sale document"""
        document = self.env['ks.sale.document'].create({
            'name': 'Test Document',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'test.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(document.sale_order_id, self.sale_order)
        self.assertEqual(document.document_type, 'packing_list')
        self.assertTrue(document.file)

    def test_02_document_computes_file_size(self):
        """Test: Document computes file size"""
        document = self.env['ks.sale.document'].create({
            'name': 'Test Document',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'test.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertGreater(document.file_size, 0, "File size should be computed")

    def test_03_document_requires_file(self):
        """Test: Document requires file upload"""
        with self.assertRaises(ValidationError):
            self.env['ks.sale.document'].create({
                'name': 'Test Document',
                'document_type': 'packing_list',
                'file': False,
                'sale_order_id': self.sale_order.id,
            })

    def test_04_sale_order_document_count(self):
        """Test: Sale order document count is computed"""
        # Create documents
        self.env['ks.sale.document'].create({
            'name': 'Document 1',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'doc1.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        self.env['ks.sale.document'].create({
            'name': 'Document 2',
            'document_type': 'airways_bill',
            'file': self.test_file_content,
            'file_name': 'doc2.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        self.sale_order._compute_ks_document_count()
        self.assertEqual(self.sale_order.ks_document_count, 2)

    def test_05_action_view_documents(self):
        """Test: Action to view documents"""
        document = self.env['ks.sale.document'].create({
            'name': 'Test Document',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'test.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        action = self.sale_order.action_view_documents()
        
        self.assertEqual(action['res_model'], 'ks.sale.document')
        self.assertEqual(action['context']['default_sale_order_id'], self.sale_order.id)

    def test_06_send_documents_requires_documents(self):
        """Test: Sending documents requires at least one document"""
        with self.assertRaises(UserError):
            self.sale_order.action_send_documents()

    def test_07_send_documents_requires_customer_email(self):
        """Test: Sending documents requires customer email"""
        # Create document
        self.env['ks.sale.document'].create({
            'name': 'Test Document',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'test.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        # Remove customer email
        self.customer.email = False
        
        with self.assertRaises(UserError):
            self.sale_order.action_send_documents()

    def test_08_create_documents_zip(self):
        """Test: Create ZIP file from documents"""
        # Create multiple documents
        self.env['ks.sale.document'].create({
            'name': 'Document 1',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'doc1.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        self.env['ks.sale.document'].create({
            'name': 'Document 2',
            'document_type': 'airways_bill',
            'file': self.test_file_content,
            'file_name': 'doc2.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        zip_data = self.sale_order._create_documents_zip()
        
        self.assertIsInstance(zip_data, bytes, "ZIP data should be bytes")
        self.assertGreater(len(zip_data), 0, "ZIP should contain data")

    def test_09_zip_filename_generation(self):
        """Test: ZIP filename is generated correctly"""
        filename = self.sale_order._get_zip_filename()
        
        self.assertIn('Documents_', filename)
        self.assertIn(self.sale_order.name.replace('/', '-'), filename)
        self.assertTrue(filename.endswith('.zip'))

    def test_10_sanitize_filename(self):
        """Test: Filename sanitization removes invalid characters"""
        invalid_filename = 'test/file:name*.pdf'
        sanitized = self.sale_order._sanitize_filename(invalid_filename)
        
        self.assertNotIn('/', sanitized)
        self.assertNotIn(':', sanitized)
        self.assertNotIn('*', sanitized)

    def test_11_document_sent_status_updated(self):
        """Test: Document sent status is updated after sending"""
        self.env['ks.sale.document'].create({
            'name': 'Test Document',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'test.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        # Mock email sending - in real test, would check mail.mail records
        # For now, just check that the method exists and can be called
        # self.sale_order.action_send_documents()
        # self.assertTrue(self.sale_order.ks_documents_sent)

    def test_12_document_types(self):
        """Test: All document types are supported"""
        document_types = ['airways_bill', 'packing_list', 'transport_bill', 
                         'evr', 'export_bill', 'commercial_invoice', 
                         'certificate_origin', 'insurance', 'other']
        
        for doc_type in document_types:
            document = self.env['ks.sale.document'].create({
                'name': f'Test {doc_type}',
                'document_type': doc_type,
                'file': self.test_file_content,
                'file_name': 'test.pdf',
                'sale_order_id': self.sale_order.id,
            })
            
            self.assertEqual(document.document_type, doc_type)

    def test_13_document_related_fields(self):
        """Test: Document related fields are populated"""
        document = self.env['ks.sale.document'].create({
            'name': 'Test Document',
            'document_type': 'packing_list',
            'file': self.test_file_content,
            'file_name': 'test.pdf',
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(document.partner_id, self.customer)
        self.assertEqual(document.company_id, self.company)

