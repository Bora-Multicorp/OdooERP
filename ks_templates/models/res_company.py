# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    stamp_image = fields.Binary(
        string="Company Stamp",
        attachment=True,
        help="Upload/save company stamp image to be displayed on PDF reports.",
    )

    effective_stamp_image = fields.Binary(
        string="Effective Company Stamp",
        compute="_compute_effective_stamp_image",
        help="Returns stamp_image of current company/branch, or parent company if not set.",
    )

    @api.depends('stamp_image', 'parent_id', 'parent_id.stamp_image')
    def _compute_effective_stamp_image(self):
        for company in self:
            stamp = False
            curr = company
            while curr:
                if curr.stamp_image:
                    stamp = curr.stamp_image
                    break
                curr = curr.parent_id
            company.effective_stamp_image = stamp
