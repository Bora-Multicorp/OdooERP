# -*- coding: utf-8 -*-

from odoo import fields, models

class RejectProductWizard(models.TransientModel):
    _name = 'reject.product.wizard'
    _description = 'Reject product Form'

    product_approval_id = fields.Many2one('product.template', string="Rejection of Product",
                                      domain="[('id', '=', active_id)]")
    remark = fields.Char('Remark', required=True)

    def action_reject_product(self):
        self.ensure_one()
        approval = self.product_approval_id
        current_user = self.env.user

        # Find the matching approval line for the currently assigned user
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            # Recompute the next approver
            approval._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}
