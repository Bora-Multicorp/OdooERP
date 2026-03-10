# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class VendorPaymentApprovalConfig(models.Model):
    _name = 'vendor.payment.approval.config'
    _description = 'Vendor Payment Approval Settings'
    _rec_name = 'user_id'
    _order = 'approval_type, sequence, approver_type'

    approval_type = fields.Selection(
        [
            ('without_bill', 'Payment approval without bill for purchase'),
            ('with_bill', 'Payment approval with bill for purchase'),
        ],
        string='Approval Type',
        required=True,
        default='without_bill',
        help='Without bill: for advance payment. With bill: for payment from vendor bill.',
    )
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
            'approval_approver_uniq',
            'unique(approval_type, user_id, approver_type)',
            'Each approval type can have only one Approver 1 and one Approver 2.',
        ),
    ]
