# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class InsuranceUpdatePolicyNumberWizard(models.TransientModel):
    _name = 'insurance.update.policy.number.wizard'
    _description = 'Update Insurance Policy Number and Date Wizard'

    renewal_history_id = fields.Many2one(
        'insurance.policy.renewal.history',
        string='Renewal Record',
        required=False,
        readonly=True,
    )
    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        readonly=True,
    )
    old_policy_number = fields.Char(
        string='Expired Policy No',
        readonly=True,
    )
    new_policy_number = fields.Char(
        string='Policy Number',
        required=True,
        help='Enter the fresh policy number issued by the insurer.',
    )
    new_expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        help='Enter the expiry date issued by the insurer.',
    )

    def action_confirm(self):
        self.ensure_one()
        new_no = (self.new_policy_number or '').strip()
        if not new_no:
            raise UserError(_("Please enter a valid Policy Number."))
        if not self.new_expiry_date:
            raise UserError(_("Please enter the Expiry Date."))

        policy = self.policy_id
        hist = self.renewal_history_id

        if hist and new_no == self.old_policy_number:
            raise UserError(_("The new policy number must be different from the expired policy number."))

        if hist and hist.new_start_date and self.new_expiry_date <= hist.new_start_date:
            raise UserError(_("New Expiry Date must be after New Start Date (%s).") % hist.new_start_date)
        elif not hist and policy.start_date and self.new_expiry_date <= policy.start_date:
            raise UserError(_("Expiry Date must be after Start Date (%s).") % policy.start_date)

        # Check uniqueness constraint across other policies
        duplicate = self.env['insurance.policy'].search([
            ('policy_number', '=', new_no),
            ('id', '!=', policy.id),
        ], limit=1)
        if duplicate:
            raise UserError(_(
                "Policy Number '%s' is already in use by policy '%s'. "
                "Each policy must have a unique policy number."
            ) % (new_no, duplicate.policy_number))

        if hist:
            # Renewal flow
            update_vals = {
                'policy_number': new_no,
                'expiry_date': self.new_expiry_date,
                'state': 'active',
            }
            if hist.new_start_date:
                update_vals['start_date'] = hist.new_start_date
            if hist.new_sum_insured:
                update_vals['initial_sum_insured'] = hist.new_sum_insured
            if hist.renewal_premium:
                update_vals['premium'] = hist.renewal_premium

            policy.with_context(from_renewal_update=True).write(update_vals)

            hist.write({
                'is_policy_number_updated': True,
                'new_policy_number': new_no,
                'new_end_date': self.new_expiry_date,
            })

            policy.message_post(
                body=_(
                    "<b>Policy Renewed:</b> Fresh policy number <b>%s</b> has been assigned. "
                    "New Expiry Date: <b>%s</b>. Expired policy number <b>%s</b> preserved in Renewal History."
                ) % (new_no, self.new_expiry_date, self.old_policy_number),
                subtype_xmlid='mail.mt_note',
            )
        else:
            # New policy flow
            update_vals = {
                'policy_number': new_no,
                'expiry_date': self.new_expiry_date,
            }
            policy.with_context(from_renewal_update=True).write(update_vals)

            policy.message_post(
                body=_(
                    "<b>Policy Details Updated:</b> Policy number updated to <b>%s</b> and "
                    "Expiry Date set to <b>%s</b>."
                ) % (new_no, self.new_expiry_date),
                subtype_xmlid='mail.mt_note',
            )

        return {'type': 'ir.actions.act_window_close'}
