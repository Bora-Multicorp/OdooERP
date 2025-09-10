# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SOUnlockApprovalUsersPicker(models.TransientModel):
    _name = 'so.unlock.approval.user.picker.wizard'
    _description = 'unlock approval users picker'

    order_id = fields.Many2one('sale.order', string="Cancelation for Purchase Order Unlock")

    group1_users = fields.Many2many(
        comodel_name='pi.unlock.approvers',
        relation='so_picker_wizard_group1_rel_unlock',   # custom relation table
        column1='wizard_id',                   # FK to wizard
        column2='approver_id',                 # FK to approver
        string="Group 1"
    )

    group2_users = fields.Many2many(
        comodel_name='pi.unlock.approvers',
        relation='so_picker_wizard_group2_rel_unlock',   # DIFFERENT relation table
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
        self.order_id.assign_unlock_users(approvers)


    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        Approver = self.env['pi.unlock.approvers']

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
