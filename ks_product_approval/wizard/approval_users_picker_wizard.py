# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ApprovalUsersPicker(models.TransientModel):
    _name = 'product.approval.user.picker.wizard'
    _description = 'Product approval users picker'

    product_id = fields.Many2one('product.template', string="Approval for Product Confirmation")
    approver1_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='compute_approver_user_ids',
        string="Available Approver 1 Users",
        store=False
    )
    
    approver2_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='compute_approver_user_ids',
        string="Available Approver 2 Users",
        store=False
    )

    approver1_user = fields.Many2one(
        comodel_name='res.users',
        string="Approver 1",
        required=True
    )

    approver2_user = fields.Many2one(
        comodel_name='res.users',
        string="Approver 2",
        required=True
    )

    add_button_disabled = fields.Boolean(
        string="Disable Add Button",
        compute='_compute_add_button_disabled'
    )

    @api.depends('product_id')
    def compute_approver_user_ids(self):
        for rec in self:
            approver1_configs = self.env['product.approval.config'].search([
                ('approver_type', '=', 'approver1'),
            ])
            rec.approver1_user_ids = approver1_configs.mapped('user_id')

            # Get users configured as Approver 2
            approver2_configs = self.env['product.approval.config'].search([
                ('approver_type', '=', 'approver2'),
            ])
            rec.approver2_user_ids = approver2_configs.mapped('user_id')

    @api.depends('approver1_user', 'approver2_user')
    def _compute_add_button_disabled(self):
        for rec in self:
            rec.add_button_disabled = not (rec.approver1_user or rec.approver2_user)

    @api.onchange('approver1_user')
    def _onchange_approver1_user(self):
        if self.approver1_user and self.approver2_user == self.approver1_user:
            self.approver2_user = False
        # Validate that selected user is in the approver1 list
        if self.approver1_user:
            approver1_configs = self.env['product.approval.config'].search([
                ('approver_type', '=', 'approver1'),
                ('user_id', '=', self.approver1_user.id)
            ])
            # if not approver1_configs:
            #     return {
            #         'warning': {
            #             'title': 'Invalid Selection',
            #             'message': 'Selected user is not configured as Approver 1 for this company.'
            #         }
            #     }

    @api.onchange('approver2_user')
    def _onchange_approver2_user(self):
        if self.approver2_user and self.approver1_user == self.approver2_user:
            self.approver1_user = False
        # Validate that selected user is in the approver2 list
        if self.approver2_user:
            approver2_configs = self.env['product.approval.config'].search([
                ('approver_type', '=', 'approver2'),
                ('user_id', '=', self.approver2_user.id)
            ])
            # if not approver2_configs:
            #     return {
            #         'warning': {
            #             'title': 'Invalid Selection',
            #             'message': 'Selected user is not configured as Approver 2 for this company.'
            #         }
            #     }

    def add_users_for_approval(self):
        approvers = []
        if self.approver1_user:
            approvers.append({
                'user_id': self.approver1_user.id,
                'approval_type': 'approver1'
            })
        if self.approver2_user:
            approvers.append({
                'user_id': self.approver2_user.id,
                'approval_type': 'approver2'
            })

        is_update = self.env.context.get('ks_is_update', False)
        if is_update and approvers:
            # Cancel old pending activities ONLY when user clicks OK (not on wizard Cancel)
            self.product_id._ks_cancel_pending_product_approval_activities()
            # Clear existing approval lines so assign_users starts fresh
            self.product_id.write({'approval_users_ids': [(5, 0, 0)], 'assigned_to': False})
            self.product_id.message_post(
                body=_("Approval request updated by %s. Previous approvers cancelled.") % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

        if approvers:
            self.product_id.assign_users(approvers)

    # @api.model
    # def default_get(self, fields):
    #     res = super().default_get(fields)
    #     # No prefill needed - user will select from the filtered list
    #     return res
