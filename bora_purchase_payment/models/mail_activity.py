# -*- coding: utf-8 -*-
from odoo import models, _


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_feedback(self, feedback=False, attachment_ids=None):
        if not self.env.context.get('skip_activity_approval_hook'):
            for activity in self:
                if (
                    activity.res_model == 'account.payment'
                    and activity.res_id
                    and 'Payment Approval' in (activity.summary or '')
                ):
                    payment = self.env['account.payment'].browse(activity.res_id)
                    if payment.exists() and payment.state == 'pending_approval':
                        my_line = payment.approval_line_ids.filtered(
                            lambda l: l.user_id == activity.user_id and l.state == 'pending'
                        )
                        if my_line:
                            payment.with_context(skip_activity_approval_hook=True)._do_approve(
                                feedback or _('Approved via activity')
                            )
                            return True
        return super().action_feedback(feedback=feedback, attachment_ids=attachment_ids)
