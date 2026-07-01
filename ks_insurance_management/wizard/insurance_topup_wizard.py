# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class InsuranceTopupWizard(models.TransientModel):
    _name = 'insurance.topup.wizard'
    _description = 'Top-up Policy Wizard'

    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        readonly=True,
    )
    current_sum_insured = fields.Float(
        string='Current Sum Insured',
        related='policy_id.initial_sum_insured',
        readonly=True,
    )
    amount = fields.Float(
        string='Top-up Amount',
        required=True,
        help='Amount to be added to the current Sum Insured upon approval.',
    )
    new_sum_insured = fields.Float(
        string='New Sum Insured (Preview)',
        compute='_compute_new_sum_insured',
    )
    approver_id = fields.Many2one(
        'insurance.payment.approver',
        string='Approver',
        required=True,
        help='Single approver who must approve this top-up.',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain=[('type', 'in', ['bank', 'cash'])],
    )
    payment_date = fields.Date(
        string='Payment Date',
        default=fields.Date.today,
    )
    currency_id = fields.Many2one(
        related='policy_id.currency_id',
        readonly=True,
    )
    notes = fields.Text(string='Notes')

    @api.depends('policy_id.initial_sum_insured', 'amount')
    def _compute_new_sum_insured(self):
        for rec in self:
            rec.new_sum_insured = (rec.policy_id.initial_sum_insured or 0.0) + (rec.amount or 0.0)

    def action_create_topup(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError("Top-up amount must be greater than zero.")

        topup = self.env['insurance.topup'].create({
            'policy_id': self.policy_id.id,
            'amount': self.amount,
            'approver_id': self.approver_id.id,
            'journal_id': self.journal_id.id if self.journal_id else False,
            'payment_date': self.payment_date,
            'notes': self.notes,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Top-up Request',
            'res_model': 'insurance.topup',
            'res_id': topup.id,
            'view_mode': 'form',
            'target': 'current',
        }
