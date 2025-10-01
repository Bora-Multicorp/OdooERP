# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SOConfirmationApprovalUsersPicker(models.TransientModel):
    _name = 'so.confirmation.approval.user.picker.wizard'
    _description = 'Confirmation approval users picker'
    user_ids_according_to_user_selection = fields.Char(store=True)

    sale_id = fields.Many2one('sale.order', string="Approval for Sale Order Confirmation")

    approver1_users = fields.Many2many(
        comodel_name='sale.order.approval.config',
        relation='picker_wizard_so_confirm_approver1_rel',   # custom relation table
        column1='wizard_id',                   # FK to wizard
        column2='approver_id',                 # FK to approver
        string="Approver 1"
    )

    approver2_users = fields.Many2many(
        comodel_name='sale.order.approval.config',
        relation='picker_wizard_so_confirm_approver2_rel',   # DIFFERENT relation table
        column1='wizard_id',
        column2='approver_id',
        string="Approver 2"
    )

    add_button_disabled = fields.Boolean(
        string="Disable Add Button",
        compute='_compute_add_button_disabled'
    )

    @api.depends('approver1_users', 'approver2_users')
    def _compute_add_button_disabled(self):
        for rec in self:
            rec.add_button_disabled = not (rec.approver1_users or rec.approver2_users)

    def add_users_for_approval(self):
        user_id_strings = self.user_ids_according_to_user_selection.split(',')
        id_list = [int(id_str.strip()) for id_str in user_id_strings]
        approvers = self.env['sale.order.approval.config'].browse(id_list)
        self.sale_id.assign_users(approvers)

    @api.onchange('approver1_users', 'approver2_users')
    def _user_change(self):
        approvers = self.approver1_users | self.approver2_users
        self.user_ids_according_to_user_selection = ','.join(str(u.id) for u in approvers)
        self.user_ids_according_to_user_selection = self.user_ids_according_to_user_selection.replace("NewId_", "")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        Approver = self.env['sale.order.approval.config']

        # Prefill Approver 1 with only the default approvers
        approver1_ids = Approver.search([
            ('default_approver', '=', 'approver1')
        ]).ids
        res['approver1_users'] = [(6, 0, approver1_ids)]

        # Prefill Approver 2 with only the default approvers
        approver2_ids = Approver.search([
            ('default_approver', '=', 'approver2')
        ]).ids
        res['approver2_users'] = [(6, 0, approver2_ids)]

        return res