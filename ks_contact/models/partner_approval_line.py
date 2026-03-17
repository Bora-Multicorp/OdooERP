# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartnerApprovalLine(models.Model):
    """
    Approval lines for Contact (res.partner) approval flow.
    Same concept as approval.users on KYC: sequence, user_id, state, remark.
    """
    _name = 'res.partner.approval.line'
    _description = 'Partner Approval Line'
    _order = 'sequence'

    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    sequence = fields.Integer(default=1)
    user_id = fields.Many2one('res.users', string='Approver', required=True)
    state = fields.Selection([
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('suspended', 'Suspended'),
    ], string='Status')
    remark = fields.Text('Remarks', tracking=True)
    action_date = fields.Datetime()
    is_active = fields.Boolean(default=True)
