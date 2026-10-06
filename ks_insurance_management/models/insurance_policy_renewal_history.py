# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InsurancePolicyRenewalHistory(models.Model):
    _name = 'insurance.policy.renewal.history'
    _description = 'Insurance Policy Renewal History'
    _order = 'create_date desc'

    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='policy_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )
    expired_policy_number = fields.Char(
        string='Expired Policy No',
        required=True,
        help='Policy number of the expired/prior policy period.',
    )
    start_date = fields.Date(
        string='Expired Policy Start Date',
        help='Start date of the expired policy period.',
    )
    end_date = fields.Date(
        string='Expired Policy End Date',
        help='End date of the expired policy period.',
    )
    policy_type = fields.Selection([
        ('individual', 'Individual'),
        ('floater', 'Floater'),
    ], string='Policy Type')

    insurance_type_id = fields.Many2one(
        'insurance.type',
        string='Insurance Type',
    )
    description = fields.Char(
        string='Description',
        compute='_compute_description',
        store=True,
        readonly=False,
    )
    renewal_premium = fields.Float(
        string='Renewal Premium',
    )
    new_start_date = fields.Date(
        string='Renewal Start Date',
    )
    new_end_date = fields.Date(
        string='Renewal End Date',
    )
    new_sum_insured = fields.Float(
        string='Renewal Sum Insured',
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Linked Payment',
        copy=False,
    )
    payment_state = fields.Selection([
        ('draft', 'Draft'),
        ('in_process', 'In Process'),
        ('posted', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Payment Status', compute='_compute_payment_state', store=True, readonly=True)

    is_policy_number_updated = fields.Boolean(
        string='Policy Number Updated',
        default=False,
        copy=False,
        help='Indicates whether fresh policy number has been updated for this renewal.',
    )
    can_update_policy_no = fields.Boolean(
        string='Can Update Policy No',
        compute='_compute_can_update_policy_no',
    )

    @api.depends('insurance_type_id', 'policy_id', 'policy_id.insurance_type_id')
    def _compute_description(self):
        for rec in self:
            if rec.insurance_type_id:
                rec.description = rec.insurance_type_id.name
            elif rec.policy_id and rec.policy_id.insurance_type_id:
                rec.description = rec.policy_id.insurance_type_id.name
            else:
                rec.description = False

    @api.depends('payment_id', 'payment_id.state')
    def _compute_payment_state(self):
        for rec in self:
            rec.payment_state = rec.payment_id.state if rec.payment_id else False

    @api.depends(
        'is_policy_number_updated',
        'payment_id',
        'payment_id.state',
        'policy_id.payment_status',
        'policy_id.is_paid',
    )
    def _compute_can_update_policy_no(self):
        for rec in self:
            if rec.is_policy_number_updated:
                rec.can_update_policy_no = False
                continue

            # Linked payment must be in 'Paid' status ('posted' in account.payment)
            if rec.payment_id:
                rec.can_update_policy_no = (rec.payment_id.state == 'posted')
            else:
                rec.can_update_policy_no = bool(
                    rec.policy_id and (rec.policy_id.payment_status == 'paid' or rec.policy_id.is_paid)
                )

    def action_update_policy_number(self):
        self.ensure_one()
        if not self.can_update_policy_no:
            if self.is_policy_number_updated:
                raise UserError(_("The policy number for this renewal has already been updated."))
            payment_status_label = self.payment_state or (self.policy_id.payment_status if self.policy_id else 'draft')
            raise UserError(_(
                "Cannot update policy number while linked payment is in '%s' status. "
                "Update is only allowed when payment is marked as 'Paid'."
            ) % (payment_status_label.title() if payment_status_label else 'Draft'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Policy Number'),
            'res_model': 'insurance.update.policy.number.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_renewal_history_id': self.id,
                'default_policy_id': self.policy_id.id,
                'default_old_policy_number': self.expired_policy_number or self.policy_id.policy_number,
            },
        }
