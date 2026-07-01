# -*- coding: utf-8 -*-

import base64
import io
import zipfile
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ===== Document Fields =====
    ks_document_ids = fields.One2many(
        comodel_name='ks.sale.document',
        inverse_name='sale_order_id',
        string='Documents',
        copy=False,
        help='Documents attached to this sale order',
    )
    ks_document_count = fields.Integer(
        string='Document Count',
        compute='_compute_ks_document_count',
        store=True,
    )
    ks_documents_sent = fields.Boolean(
        string='Documents Sent',
        default=False,
        copy=False,
        help='Indicates if documents have been sent to the customer',
    )
    ks_documents_sent_date = fields.Datetime(
        string='Documents Sent Date',
        copy=False,
    )

    @api.depends('ks_document_ids')
    def _compute_ks_document_count(self):
        """Compute the number of documents attached"""
        for order in self:
            order.ks_document_count = len(order.ks_document_ids)

    def action_view_documents(self):
        """View all documents attached to this sale order"""
        self.ensure_one()
        action = {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.document',
            'context': {'default_sale_order_id': self.id},
        }
        
        if self.ks_document_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.ks_document_ids.id
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('sale_order_id', '=', self.id)]
        
        return action

    def action_send_documents(self):
        """
        Send all documents to the customer as a ZIP file via email.
        
        This method:
        1. Validates that documents exist
        2. Creates a ZIP file containing all documents
        3. Creates an email with the ZIP attached
        4. Sends the email to the customer
        """
        self.ensure_one()
        
        # Validate documents exist
        if not self.ks_document_ids:
            raise UserError(_('No documents have been uploaded for this sale order. Please upload documents before sending.'))
        
        # Validate customer email
        if not self.partner_id.email:
            raise UserError(_('The customer does not have an email address. Please add an email address to the customer record.'))
        
        # Create ZIP file
        zip_data = self._create_documents_zip()
        
        # Get email template
        template = self.env.ref('ks_doc.email_template_sale_documents', raise_if_not_found=False)
        if not template:
            raise UserError(_('Email template not found. Please ensure the module is properly installed.'))
        
        # Create the ZIP attachment
        zip_filename = self._get_zip_filename()
        attachment = self.env['ir.attachment'].create({
            'name': zip_filename,
            'type': 'binary',
            'datas': base64.b64encode(zip_data),
            'res_model': 'sale.order',
            'res_id': self.id,
            'mimetype': 'application/zip',
        })
        
        # Send email with attachment
        template.send_mail(
            self.id,
            force_send=True,
            email_values={
                'attachment_ids': [(4, attachment.id)],
            }
        )
        
        # Update sent status
        self.write({
            'ks_documents_sent': True,
            'ks_documents_sent_date': fields.Datetime.now(),
        })
        
        # Log in chatter
        doc_count = len(self.ks_document_ids)
        doc_types = ', '.join(set(doc._get_document_type_label() for doc in self.ks_document_ids))
        self.message_post(
            body=_('Documents sent to customer %s.<br/>'
                   '<b>Documents:</b> %s file(s)<br/>'
                   '<b>Types:</b> %s<br/>'
                   '<b>ZIP File:</b> %s') % (
                self.partner_id.name,
                doc_count,
                doc_types,
                zip_filename
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # Show success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Documents Sent'),
                'message': _('%s document(s) have been sent to %s.') % (doc_count, self.partner_id.name),
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_documents_zip(self):
        """
        Create a ZIP file containing all documents.
        
        Returns:
            bytes: The ZIP file content as bytes
        """
        self.ensure_one()
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for doc in self.ks_document_ids:
                if doc.file and doc.file_name:
                    # Decode the base64 file content
                    file_content = base64.b64decode(doc.file)
                    
                    # Create a unique filename with document type prefix
                    doc_type_label = doc._get_document_type_label()
                    # Clean the filename
                    safe_filename = self._sanitize_filename(doc.file_name)
                    # Create path in ZIP: DocumentType/filename
                    zip_path = f"{doc_type_label}/{safe_filename}"
                    
                    # Add to ZIP
                    zip_file.writestr(zip_path, file_content)
        
        # Get the ZIP content
        zip_buffer.seek(0)
        return zip_buffer.read()

    def _get_zip_filename(self):
        """Generate the ZIP filename"""
        self.ensure_one()
        date_str = datetime.now().strftime('%Y%m%d')
        # Clean the order name for use in filename
        order_name = self.name.replace('/', '-').replace('\\', '-')
        return f"Documents_{order_name}_{date_str}.zip"

    def _sanitize_filename(self, filename):
        """Sanitize filename to remove invalid characters"""
        if not filename:
            return 'document'
        # Replace invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename

    def action_open_send_documents_wizard(self):
        """Open the send documents confirmation wizard"""
        self.ensure_one()
        
        if not self.ks_document_ids:
            raise UserError(_('No documents have been uploaded for this sale order. Please upload documents before sending.'))
        
        if not self.partner_id.email:
            raise UserError(_('The customer does not have an email address. Please add an email address to the customer record.'))
        
        # Directly send documents (can be changed to open a wizard if preview is needed)
        return self.action_send_documents()

