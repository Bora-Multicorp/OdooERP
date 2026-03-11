# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'
    _description = 'Insurance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)
    policy_number = fields.Char(string='Policy Number', tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    insurance_type_id = fields.Many2one(
        'insurance.type',
        string='Insurance Type',
        required=True,
        tracking=True,
    )
    insurance_category_id = fields.Many2one(
        related='insurance_type_id.category_id',
        string='Category',
        store=True,
    )
    insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
        required=True,
    )
    agent_id = fields.Many2one('insurance.agent', string='Agent')
    policy_type = fields.Selection([
        ('individual', 'Individual'), ('floater', 'Floater'),
    ], string='Policy Type', default='individual', required=True)
    floater_location_ids = fields.Many2many('stock.warehouse', string='Covered Locations')
    sum_insured = fields.Float(string='Sum Insured', tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    sum_insured_words = fields.Char(
        string='Sum Insured (in Words)',
        compute='_compute_sum_insured_words',
        store=True,
    )
    premium = fields.Float(string='Premium (Incl. GST)', tracking=True)
    premium_percentage = fields.Float(
        string='Premium %',
        compute='_compute_premium_pct',
        store=True,
    )
    balance_sum_insured = fields.Float(string='Balance Sum Insured', tracking=True)
    start_date = fields.Date(string='Start Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    state = fields.Selection([
        ('active', 'Active'), ('expired', 'Expired'),
    ], string='Status', default='active', tracking=True)
    is_marine = fields.Boolean(related='insurance_type_id.is_marine', store=True)
    is_fire_burglary = fields.Boolean(related='insurance_type_id.is_fire_burglary', store=True)
    is_misc = fields.Boolean(related='insurance_category_id.is_misc', store=True)
    payment_id = fields.Many2one('account.payment', string='Source Payment')
    payment_ids = fields.One2many('account.payment', 'insurance_policy_id', string='Payments')
    total_premium_paid = fields.Float(
        string='Total Premium Paid',
        compute='_compute_total_premium',
        store=True,
    )
    declaration_ids = fields.One2many(
        'insurance.declaration',
        'policy_id',
        string='Declarations',
    )
    notes = fields.Text(string='Notes')

    @api.depends('sum_insured')
    def _compute_sum_insured_words(self):
        for rec in self:
            try:
                from num2words import num2words
                rec.sum_insured_words = (
                    num2words(int(rec.sum_insured), lang='en_IN').title() + ' Rupees Only'
                ) if rec.sum_insured else ''
            except Exception:
                rec.sum_insured_words = ''

    @api.depends('premium', 'sum_insured')
    def _compute_premium_pct(self):
        for rec in self:
            rec.premium_percentage = (
                rec.premium / rec.sum_insured * 100) if rec.sum_insured else 0.0

    @api.depends('payment_ids.amount')
    def _compute_total_premium(self):
        for rec in self:
            rec.total_premium_paid = sum(rec.payment_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('insurance.policy') or 'New'
                )
            if 'sum_insured' in vals and 'balance_sum_insured' not in vals:
                vals['balance_sum_insured'] = vals['sum_insured']
        return super().create(vals_list)

    def action_mark_expired(self):
        for rec in self:
            rec.state = 'expired'
            if rec.is_marine:
                rec.balance_sum_insured = 0.0

    def action_check_expiry(self):
        today = fields.Date.today()
        expired = self.search([('state', '=', 'active'), ('expiry_date', '<', today)])
        expired.action_mark_expired()

    def action_send_expiry_reminders(self):
        today = fields.Date.today()
        threshold = today + timedelta(days=30)
        expiring = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<=', threshold),
            ('expiry_date', '>=', today),
        ])
        for pol in expiring:
            pol.message_post(
                body=(
                    f"⚠️ Policy <b>{pol.policy_number or pol.name}</b> is expiring on "
                    f"<b>{pol.expiry_date}</b>. Please renew."
                ),
                subject="Insurance Policy Expiry Reminder",
                message_type='email',
            )

    def deduct_from_balance(self, amount):
        self.ensure_one()
        if not self.is_marine:
            return
        self.balance_sum_insured = max(self.balance_sum_insured - amount, 0.0)
        self.message_post(
            body=(
                f"Balance deducted by \u20b9{amount:,.2f}. "
                f"New balance: \u20b9{self.balance_sum_insured:,.2f}"
            ),
        )

    def _get_avg_inventory(self):
        self.ensure_one()
        total = 0.0
        locations = self.floater_location_ids or self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)])
        for wh in locations:
            quants = self.env['stock.quant'].search(
                [('location_id', 'child_of', wh.lot_stock_id.id)])
            total += sum(q.quantity * q.product_id.standard_price for q in quants)
        return total

    def action_view_declarations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Declarations',
            'res_model': 'insurance.declaration',
            'view_mode': 'list,form',
            'domain': [('policy_id', '=', self.id)],
            'context': {'default_policy_id': self.id},
        }

    @api.constrains('policy_type', 'floater_location_ids')
    def _check_floater_locations(self):
        for rec in self:
            if rec.policy_type == 'floater' and not rec.floater_location_ids:
                raise UserError(
                    "Floater policy must have at least one covered location."
                )

    @api.constrains('start_date', 'expiry_date')
    def _check_policy_dates(self):
        for rec in self:
            if rec.start_date and rec.expiry_date and rec.expiry_date < rec.start_date:
                raise UserError("Expiry Date must be on or after Start Date.")
