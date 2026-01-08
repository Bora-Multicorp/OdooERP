# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleDocument(models.Model):
    _name = 'ks.sale.document'
    _description = 'Sale Order Document'
    _order = 'sequence, id'

    name = fields.Char(
        string='Document Name',
        required=True,
        help='Name or description of the document',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    document_type = fields.Selection([
        ('airways_bill', 'Airways Bill'),
        ('packing_list', 'Packing List'),
        ('transport_bill', 'Transport Bill'),
        ('evr', 'EVR (Export Verification Report)'),
        ('export_bill', 'Export Bill'),
        ('commercial_invoice', 'Commercial Invoice'),
        ('certificate_origin', 'Certificate of Origin'),
        ('insurance', 'Insurance Document'),
        ('other', 'Other'),
    ], string='Document Type', required=True, default='other',
       help='Type of the document being uploaded')
    
    file = fields.Binary(
        string='File',
        required=True,
        attachment=True,
        help='Upload the document file',
    )
    file_name = fields.Char(
        string='File Name',
        help='Name of the uploaded file',
    )
    file_size = fields.Integer(
        string='File Size',
        compute='_compute_file_size',
        store=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        related='sale_order_id.partner_id',
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='sale_order_id.company_id',
        store=True,
    )
    upload_date = fields.Datetime(
        string='Upload Date',
        default=fields.Datetime.now,
        readonly=True,
    )
    uploaded_by = fields.Many2one(
        comodel_name='res.users',
        string='Uploaded By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this document',
    )

    @api.depends('file')
    def _compute_file_size(self):
        """Compute the file size in bytes"""
        for doc in self:
            if doc.file:
                import base64
                doc.file_size = len(base64.b64decode(doc.file))
            else:
                doc.file_size = 0

    @api.constrains('file')
    def _check_file(self):
        """Validate that file is uploaded"""
        for doc in self:
            if not doc.file:
                raise ValidationError(_('Please upload a file for the document "%s".') % doc.name)

    def _get_document_type_label(self):
        """Get the display label for the document type"""
        self.ensure_one()
        return dict(self._fields['document_type'].selection).get(self.document_type, self.document_type)

