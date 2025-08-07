# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductApprovalConfig(models.Model): 
    _name = "product.approval.config"
    _description = "Product Approval Settings"
    _rec_name = 'user_id'

    sequence = fields.Integer(string='Sequence', readonly=True)
    user_id = fields.Many2one('res.users', string='Approval User', required=True)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approval user must be unique.'),
        ('unique_sequence', 'unique(sequence)', 'Each sequence must be unique.'),
    ]

    def _validate_unique_user(self, user_id, exclude_ids=None):
        domain = [('user_id', '=', user_id)]
        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))
        if self.search_count(domain):
            raise ValidationError(_("This user is already added to the approval list."))

    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        max_sequence = self.search([], order="sequence desc", limit=1).sequence
        defaults['sequence'] = max_sequence + 1 if max_sequence else 1
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._validate_unique_user(vals.get('user_id'))


        res_list = super(ProductApprovalConfig, self).create(vals_list)
        for res in res_list:
            res._update_draft_product_approvals()
        return res_list

    def write(self, vals):
        for rec in self:
            if 'user_id' in vals:
                rec._validate_unique_user(vals['user_id'], exclude_ids=rec.ids)

        res = super().write(vals)
        self._update_draft_product_approvals()
        return res

    def unlink(self):
        res = super().unlink()
        self._update_draft_product_approvals()
        return res

    def _update_draft_product_approvals(self):
        """Update approval_users_ids on draft product records."""
        product_approvals = self.env['product.template'].search([('state', '=', 'draft'),('active', '=', False),('is_hidden_for_approval', '=', True)])
        config_users = self.search([]).sorted(key=lambda r: r.sequence)

        for product in product_approvals:
            approval_lines = [(5, 0, 0)]  # Clear existing first
            for config in config_users:
                approval_lines.append((0, 0, {
                    'sequence': config.sequence,
                    'user_id': config.user_id.id,
                }))
            product.write({'approval_users_ids': approval_lines})
