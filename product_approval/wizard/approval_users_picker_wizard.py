# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ApprovalUsersPicker(models.TransientModel):
    _name = 'product.approval.user.picker.wizard'
    _description = 'Product approval users picker'

    product_id = fields.Many2one('product.template', string="Approval for Product Confirmation")

    group1_users = fields.Many2many(
        comodel_name='product.approval.config',
        relation='product_approval_picker_wizard_group1_rel',   # custom relation table
        column1='wizard_id',                   # FK to wizard
        column2='approver_id',                 # FK to approver
        string="Group 1"
    )

    group2_users = fields.Many2many(
        comodel_name='product.approval.config',
        relation='product_approval_picker_wizard_group2_rel',   # DIFFERENT relation table
        column1='wizard_id',
        column2='approver_id',
        string="Group 2"
    )

    add_button_disabled = fields.Boolean(
        string="Disable Add Button",
        compute='_compute_add_button_disabled'
    )

    @api.depends('group1_users', 'group2_users')
    def _compute_add_button_disabled(self):
        for rec in self:
            rec.add_button_disabled = not (rec.group1_users or rec.group2_users)

    def add_users_for_approval(self):
        approvers = self.group1_users | self.group2_users
        self.product_id.assign_users(approvers)


    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        Approver = self.env['product.approval.config']

        # Prefill Group 1 with only the default approvers
        group1_ids = Approver.search([
            ('group', '=', 'group1'), 
            ('default_user', '=', True)
        ]).ids
        res['group1_users'] = [(6, 0, group1_ids)]

        # Prefill Group 2 with only the default approvers
        group2_ids = Approver.search([
            ('group', '=', 'group2'), 
            ('default_user', '=', True)
        ]).ids
        res['group2_users'] = [(6, 0, group2_ids)]

        return res
