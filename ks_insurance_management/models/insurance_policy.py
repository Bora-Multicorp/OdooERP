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

    name = fields.Char(
        string='Reference',
        default='New',
        readonly=True,
        copy=False,
        help='Auto-generated unique reference number for this insurance policy (e.g. INS/2025/0001).',
    )
    policy_number = fields.Char(
        string='Policy Number',
        tracking=True,
        help='Official policy number issued by the insurance company. '
             'This is entered manually after receiving the policy document.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='The legal entity (your company) for which this insurance policy is taken.',
    )
    insurance_type_id = fields.Many2one(
        'insurance.type',
        string='Insurance Type',
        required=True,
        tracking=True,
        help='The specific type of insurance (e.g. Marine Open Cover, Fire Insurance, GMC). '
             'The type determines the category and applicable report.',
    )
    insurance_category_id = fields.Many2one(
        related='insurance_type_id.category_id',
        string='Category',
        store=True,
        help='High-level category automatically derived from the Insurance Type '
             '(e.g. Marine, Fire, GMC). Used for report grouping.',
    )
    insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
        required=True,
        help='The insurer (insurance provider) who issued this policy '
             '(e.g. New India Assurance, United India Insurance).',
    )
    agent_id = fields.Many2one(
        'insurance.agent',
        string='Agent',
        help='The insurance broker or agent who arranged this policy. '
             'Used for contact and commission tracking.',
    )
    policy_type = fields.Selection([
        ('individual', 'Individual'), ('floater', 'Floater'),
    ], string='Policy Type', default='individual', required=True,
        help='Individual: covers a single location/entity.\n'
             'Floater: a single policy that covers multiple warehouse locations '
             'of the same company under one sum insured.',
    )
    floater_location_ids = fields.Many2many(
        'stock.warehouse',
        string='Covered Locations',
        help='Applicable only for Floater policies. '
             'Select all warehouse locations covered under this single floater policy.',
    )
    sum_insured = fields.Float(
        string='Sum Insured',
        tracking=True,
        help='The maximum amount the insurer will pay in case of a claim. '
             'For Marine policies, this also acts as the opening balance '
             'that gets reduced with each declaration.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
        help='Currency in which the sum insured and premium are denominated.',
    )
    sum_insured_words = fields.Char(
        string='Sum Insured (in Words)',
        compute='_compute_sum_insured_words',
        store=True,
        help='Sum Insured converted to English words (Indian format) for use in official letters and certificates.',
    )
    premium = fields.Float(
        string='Premium (Incl. GST)',
        tracking=True,
        help='Total premium amount paid for this policy, inclusive of GST. '
             'Auto-filled from the linked payment.',
    )
    premium_percentage = fields.Float(
        string='Premium %',
        compute='_compute_premium_pct',
        store=True,
        help='Premium as a percentage of the Sum Insured. '
             'Formula: (Premium / Sum Insured) × 100. Used in insurance reports.',
    )
    balance_sum_insured = fields.Float(
        string='Balance Sum Insured',
        tracking=True,
        help='Remaining sum insured balance. For Marine policies, '
             'this is reduced automatically each time a declaration is confirmed. '
             'Resets to 0 when the policy expires.',
    )
    start_date = fields.Date(
        string='Start Date',
        default=fields.Date.today,
        help='Date from which this insurance policy is effective.',
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        required=True,
        tracking=True,
        help='Date on which this policy expires. '
             'An automated job checks daily and marks policies as Expired. '
             'A 30-day reminder notification is also sent automatically.',
    )
    state = fields.Selection([
        ('active', 'Active'), ('expired', 'Expired'),
    ], string='Status', default='active', tracking=True,
        help='Active: policy is valid and in force.\n'
             'Expired: policy has passed its expiry date or was manually expired. '
             'Expired policies remain in the system for audit but are hidden from default views.',
    )
    is_marine = fields.Boolean(
        related='insurance_type_id.is_marine',
        store=True,
        help='Indicates this is a Marine insurance policy. '
             'Marine policies track balance sum insured and require periodic sales declarations.',
    )
    is_fire_burglary = fields.Boolean(
        related='insurance_type_id.is_fire_burglary',
        store=True,
        help='Indicates this is a Fire & Burglary insurance policy. '
             'These policies require inventory-based declarations.',
    )
    is_misc = fields.Boolean(
        related='insurance_category_id.is_misc',
        store=True,
        help='Indicates this policy belongs to a Miscellaneous category '
             '(e.g. GMC, GPA, Vehicle). These appear in the Miscellaneous Insurance Report.',
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Source Payment',
        help='The original payment from which this policy was created via the Insurance Details popup.',
    )
    payment_ids = fields.One2many(
        'account.payment',
        'insurance_policy_id',
        string='Payments',
        help='All premium payments linked to this policy. '
             'New top-up or renewal payments can be linked here.',
    )
    total_premium_paid = fields.Float(
        string='Total Premium Paid',
        compute='_compute_total_premium',
        store=True,
        help='Sum of all linked payment amounts. Provides the total premium outflow for this policy.',
    )
    declaration_ids = fields.One2many(
        'insurance.declaration',
        'policy_id',
        string='Declarations',
        help='Periodic declarations submitted to the insurer. '
             'Marine policies require monthly/weekly sales declarations; '
             'Fire & Burglary require inventory declarations.',
    )
    notes = fields.Text(
        string='Notes',
        help='Internal remarks or additional details about this policy '
             '(e.g. special clauses, renewal conditions, coverage exclusions).',
    )

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
            days_left = (pol.expiry_date - today).days
            pol.message_post(
                body=(
                    f"<b>Insurance Policy Expiry Reminder</b><br/>"
                    f"Policy <b>{pol.policy_number or pol.name}</b> "
                    f"({pol.insurance_type_id.name}) is expiring on "
                    f"<b>{pol.expiry_date}</b> — "
                    f"<b>{days_left} day(s)</b> remaining. Please initiate renewal."
                ),
                subject="Insurance Policy Expiry Reminder",
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

    def action_renew_policy(self):
        """Open a new policy form pre-filled with this policy's details for renewal."""
        self.ensure_one()
        ctx = {
            'default_insurance_type_id': self.insurance_type_id.id,
            'default_insurance_company_id': self.insurance_company_id.id,
            'default_agent_id': self.agent_id.id if self.agent_id else False,
            'default_policy_type': self.policy_type,
            'default_floater_location_ids': [(6, 0, self.floater_location_ids.ids)],
            'default_sum_insured': self.sum_insured,
            'default_currency_id': self.currency_id.id,
            'default_company_id': self.company_id.id,
            'default_notes': self.notes or '',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renew Policy',
            'res_model': 'insurance.policy',
            'view_mode': 'form',
            'context': ctx,
        }

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
            if not wh.lot_stock_id:
                continue
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
