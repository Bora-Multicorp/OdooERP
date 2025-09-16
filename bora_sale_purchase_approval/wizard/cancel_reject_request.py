from odoo import fields, models

class SOConfirmRejectWizard(models.TransientModel):
    _name = 'reject.cancel.so.wizard'
    _description = 'Rejection for Sale Order Cancellation'

    sale_id = fields.Many2one('sale.order', string="Rejection for Sale Order Cancellation")

    remark = fields.Char('Remark', required=True)

    def action_reject_so_cancellation(self):
        self.ensure_one()

        # 1. Find the matching approval line for the currently assigned user and mark it as rejected
        approval_line = self.sale_id.so_approval_users_ids_for_cancellation.filtered(
            lambda l: l.user_id == self.env.user and not l.state
        )

        approval_line = approval_line[-1] if approval_line else False

        if approval_line:
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })

        # 2. grab all remaining users can mark their status as suspended
        pending_users_lines = self.sale_id.so_approval_users_ids_for_cancellation.filtered(
            lambda l: not l.state
        )

        if pending_users_lines:
            pending_users_lines.write({
                'state': 'suspended',
                'remark': "Rejected by previous authority.",
                'action_date': fields.Datetime.now(),
            })



            # Recompute the next approver
            self.sale_id._update_assigned_to_form_SO_cancellation()
            self.sale_id._send_notification_on_rejection_of_SO_cancellation()

        return {'type': 'ir.actions.act_window_close'}