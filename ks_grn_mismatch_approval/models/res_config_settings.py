# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ks_grn_responsible_user_id = fields.Many2one(
        'res.users',
        string='GRN / Receipt Responsible User',
        related='company_id.ks_grn_responsible_user_id',
        readonly=False,
        help='User to notify when a GRN mismatch is approved (e.g. warehouse responsible).',
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    ks_grn_responsible_user_id = fields.Many2one(
        'res.users',
        string='GRN / Receipt Responsible User',
        help='User to notify when a GRN mismatch approval is completed (e.g. warehouse responsible).',
    )
