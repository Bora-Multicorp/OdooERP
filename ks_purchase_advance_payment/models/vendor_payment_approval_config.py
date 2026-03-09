# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class VendorPaymentApprovalConfig(models.Model):
    _name = 'vendor.payment.approval.config'
    _description = 'Vendor Payment Approval Settings'
    _rec_name = 'user_id'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default=10)
    user_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True,
        help='User who can approve or reject vendor payment requests.',
    )
    approver_type = fields.Selection(
        [
            ('approver1', 'Approver 1'),
            ('approver2', 'Approver 2'),
        ],
        string='Approver Type',
        required=True,
        help='Approval order: Approver 1 must approve before Approver 2.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'user_id_uniq',
            'unique(user_id)',
            'Each user can only be assigned once in Vendor Payment Approval Settings.',
        ),
    ]
