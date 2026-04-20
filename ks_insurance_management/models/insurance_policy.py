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
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='For individual policies: the warehouse this policy covers.\n'
             'Marine: Sum Insured reduces as goods are shipped out from this warehouse '
             '(excluding same-premises transfers).\n'
             'Fire & Burglary: Balance Sum Insured = Sum Insured minus current stock value here.',
    )

    # ── Original policy limit (manually entered at creation, never auto-changed) ──────────
    initial_sum_insured = fields.Float(
        string='Sum Insured',
        required=True,
        tracking=True,
        help='The maximum amount purchased from the insurer (the policy limit).\n'
             'Marine: this is the opening coverage; it reduces as goods are shipped out.\n'
             'Fire & Burglary: this stays fixed; the Balance Sum Insured reflects available capacity.',
    )

    # ── Effective / remaining sum insured (computed) ──────────────────────────────────────
    # Marine   : initial_sum_insured − total value of goods shipped from the warehouse
    #            (same-premises transfers are excluded — goods must physically leave).
    # F&B      : same as initial_sum_insured (no shipment-based deduction).
    # Others   : same as initial_sum_insured.
    sum_insured = fields.Float(
        string='Remaining Sum Insured',
        compute='_compute_sum_insured',
        store=False,
        help='Marine: the policy limit after deducting the value of goods already shipped '
             'from the covered warehouse. Reduces with each outgoing delivery.\n'
             'Fire & Burglary / Others: same as the original Sum Insured (no deduction).',
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
        help='Original Sum Insured converted to English words (Indian format) '
             'for use in official letters and certificates.',
    )
    premium = fields.Float(
        string='Premium (Incl. GST)',
        required=True,
        tracking=True,
        help='Total premium amount paid for this policy, inclusive of GST. '
             'Auto-filled from the linked payment.',
    )
    premium_percentage = fields.Float(
        string='Premium %',
        compute='_compute_premium_pct',
        store=True,
        help='Premium as a percentage of the original Sum Insured. '
             'Formula: (Premium / Sum Insured) × 100. Used in insurance reports.',
    )

    # ── Balance sum insured (computed, Fire & Burglary only) ─────────────────────────────
    # F&B: initial_sum_insured − current inventory value at the covered warehouse(es).
    #      Increases when goods are shipped out; decreases when goods arrive.
    # Marine / Others: not applicable (shown as 0).
    balance_sum_insured = fields.Float(
        string='Balance Sum Insured',
        compute='_compute_balance_sum_insured',
        store=False,
        help='Fire & Burglary: Sum Insured minus the current inventory value at the '
             'covered warehouse. Reflects how much coverage is available above the '
             'stock currently held (increases when goods ship out, decreases when stock arrives).\n'
             'Marine: not applicable — use Remaining Sum Insured instead.\n'
             'Returns 0 when the policy is expired.',
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
        ('draft', 'Inactive'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True,
        help='Inactive: policy created but premium not yet paid.\n'
             'Active: policy is valid and in force (set automatically after payment).\n'
             'Expired: policy has passed its expiry date or was manually expired.',
    )
    payment_status = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Payment Requested'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], string='Payment Status', default='draft', tracking=True,
        copy=False,
        help='Tracks the premium payment lifecycle for this policy.\n'
             'Draft: no payment request raised yet.\n'
             'Payment Requested: request submitted and pending approver action.\n'
             'Approved: approver has approved; awaiting banking team to post payment.\n'
             'Paid: payment posted and confirmed by the banking team.',
    )
    is_paid = fields.Boolean(
        string='Is Paid',
        default=False,
        copy=False,
        tracking=True,
        help='Set to True once the banking team confirms premium payment. '
             'A policy cannot be manually set to Active state unless this flag is True.',
    )
    topup_flag = fields.Boolean(
        string='Has Top-up',
        default=False,
        copy=False,
        help='Automatically set to True when any top-up is approved on this policy.',
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
    pending_topup_amount = fields.Float(
        string='Pending Top-up Amount',
        default=0.0,
        copy=False,
        help='Internal: stores the top-up amount between wizard confirm and approval.',
    )
    payment_count = fields.Integer(
        string='Payments',
        compute='_compute_payment_count',
    )

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    # ── Payment workflow helpers ──────────────────────────────────────────────

    def _get_approver(self):
        """Return the single active approver for this policy's company."""
        return self.env['insurance.payment.approver'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)

    def _is_insurance_admin(self):
        """True if the current user is an Insurance Administrator."""
        return self.env.user.has_group('ks_insurance_management.group_insurance_admin')

    def _notify_approver(self, approver, summary, note):
        """Create a To-Do activity on this policy for the approver."""
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=approver.user_id.id,
            summary=summary,
            note=note,
        )

    def _notify_banking_team(self, payment):
        """Create a To-Do activity on the payment for every accounting user."""
        banking_group = self.env.ref('account.group_account_user', raise_if_not_found=False)
        users = banking_group.users if banking_group else self.env['res.users'].browse(
            self.env.ref('base.user_admin').id)
        for user in users:
            payment.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=f'Insurance Payment to Post — {self.name}',
                note=(
                    f'A draft insurance payment has been created for policy '
                    f'<b>{self.name}</b> ({self.insurance_type_id.name}).<br/>'
                    f'Amount: <b>₹{payment.amount:,.2f}</b><br/>'
                    f'Please post this payment in the accounting system.'
                ),
            )

    def _notify_insurance_team(self):
        """Create a To-Do activity on this policy for every insurance user."""
        ins_group = self.env.ref(
            'ks_insurance_management.group_insurance_user', raise_if_not_found=False)
        if not ins_group:
            return
        for user in ins_group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=f'Insurance Payment Completed — {self.name}',
                note=f'Payment for policy <b>{self.name}</b> has been posted and confirmed.',
            )

    # ── Payment workflow actions ──────────────────────────────────────────────

    def action_request_payment(self):
        """Open the payment request wizard. Works from form (single) and list (multi-select)."""
        # Pre-fill the active approver for this company
        approver = self._get_approver()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request Payment',
            'res_model': 'insurance.payment.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_policy_ids': self.ids,
                'default_approver_id': approver.id if approver else False,
            },
        }

    def action_approve_payment(self):
        """Approver (or admin) approves: create draft account.payment, notify banking team."""
        self.ensure_one()
        approver = self._get_approver()
        if not self._is_insurance_admin():
            if not approver or approver.user_id != self.env.user:
                raise UserError("Only the designated payment approver can approve this request.")
        if self.payment_status != 'requested':
            raise UserError("This policy does not have a pending payment request.")

        is_topup = self.pending_topup_amount > 0
        amount = self.pending_topup_amount if is_topup else self.premium
        if not amount:
            raise UserError(
                "No payment amount found. "
                "Please set a Premium on the policy or re-submit the top-up request."
            )

        # Find a bank/cash journal for this company
        journal = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(
                "No bank or cash journal found for this company. "
                "Please configure one in Accounting → Configuration → Journals."
            )

        payment_label = (
            f"Insurance {'Top-up' if is_topup else 'Premium'} — "
            f"{self.policy_number or self.name}"
        )
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'amount': amount,
            'date': fields.Date.today(),
            'journal_id': journal.id,
            'memo': payment_label,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'is_insurance_payment': True,
            'is_topup': is_topup,
            'insurance_policy_id': self.id,
        })

        self.write({'payment_status': 'approved'})

        # Mark approver's activity as done
        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Approved by {self.env.user.name}',
        )

        # Notify banking team via activity on the payment record
        self._notify_banking_team(payment)

        self.message_post(
            body=(
                f'Payment approved by <b>{self.env.user.name}</b>. '
                f'Draft payment <b>{payment.memo}</b> created. '
                f'Banking team notified.'
            ),
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Draft Payment',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reject_payment(self):
        """Approver (or admin) rejects the payment request. Rolls back top-up if applicable."""
        self.ensure_one()
        approver = self._get_approver()
        if not self._is_insurance_admin():
            if not approver or approver.user_id != self.env.user:
                raise UserError("Only the designated payment approver can reject this request.")
        if self.payment_status != 'requested':
            raise UserError("This policy does not have a pending payment request.")

        vals = {}

        # Roll back top-up sum insured increase if this was a top-up request
        if self.pending_topup_amount > 0:
            completed_topups = self.payment_ids.filtered(
                lambda p: p.is_topup and p.state == 'posted'
            )
            vals.update({
                'initial_sum_insured': self.initial_sum_insured - self.pending_topup_amount,
                'pending_topup_amount': 0.0,
                'topup_flag': bool(completed_topups),
            })

        # Restore appropriate payment status
        vals['payment_status'] = 'paid' if self.is_paid else 'draft'
        self.write(vals)

        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Rejected by {self.env.user.name}',
        )
        self.message_post(
            body=f'Payment request <b>rejected</b> by <b>{self.env.user.name}</b>.',
        )

    def action_topup_addon(self):
        """Open the top-up wizard. Policy must be active and paid."""
        self.ensure_one()
        if not self.is_paid:
            raise UserError(
                "Top-up is only available on paid policies. "
                "Please complete the premium payment first."
            )
        if self.state != 'active':
            raise UserError("Top-up is only allowed on active policies.")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Top Up Addon',
            'res_model': 'insurance.policy.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_policy_id': self.id},
        }

    def action_view_policy_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('insurance_policy_id', '=', self.id)],
            'context': {
                'default_insurance_policy_id': self.id,
                'default_is_insurance_payment': True,
            },
        }

    tolerance_percent = fields.Float(
        string='Tolerance (%)',
        default=20.0,
        help='Alert threshold as a percentage of the original Sum Insured.\n'
             'Marine: a notification is sent to the Insurance team when the '
             'Remaining Sum Insured drops to or below this percentage.\n'
             'Fire & Burglary: notification is sent when the Balance Sum Insured '
             'drops to or below this percentage.\n'
             'Set to 0 to disable tolerance alerts for this policy.',
    )
    tolerance_notified = fields.Boolean(
        string='Tolerance Alert Sent',
        default=False,
        copy=False,
        help='Internal flag. Set when a tolerance-breach notification has already been '
             'sent for the current breach. Automatically reset when the remaining coverage '
             'recovers above the threshold (e.g. for F&B when stock ships out).',
    )
    notes = fields.Text(
        string='Notes',
        help='Internal remarks or additional details about this policy '
             '(e.g. special clauses, renewal conditions, coverage exclusions).',
    )

    # ── Compute: sum_insured (remaining, Marine-specific) ────────────────────────────────

    @api.depends('initial_sum_insured', 'warehouse_id', 'is_marine', 'state', 'start_date')
    def _compute_sum_insured(self):
        for rec in self:
            if rec.is_marine and rec.warehouse_id and rec.state == 'active':
                rec.sum_insured = rec._get_marine_remaining()
            else:
                rec.sum_insured = rec.initial_sum_insured

    def _get_marine_remaining(self):
        """
        Marine sum_insured = initial_sum_insured − value of goods that physically left
        this warehouse since the policy start date.

        Same-premises rule: if the destination location belongs to the SAME warehouse's
        location tree, the goods have not physically moved — skip those pickings.
        This covers inter-company transfers where both companies share the same warehouse
        (e.g. Bora LLP Lullanagar → Arya Enterprise Pune using the same Warehouse A).
        Only when they use DIFFERENT warehouses (Warehouse B → Warehouse C) does the
        shipment count against the insured amount.
        """
        self.ensure_one()
        # Build the set of all locations that belong to this warehouse.
        view_loc = self.warehouse_id.view_location_id
        if view_loc:
            same_premises_ids = set(
                self.env['stock.location'].sudo().search(
                    [('id', 'child_of', view_loc.id)]
                ).ids
            )
        else:
            same_premises_ids = set()

        domain = [
            ('picking_type_id.warehouse_id', '=', self.warehouse_id.id),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
        ]
        if self.start_date:
            domain.append(('date_done', '>=', fields.Datetime.to_datetime(self.start_date)))

        pickings = self.env['stock.picking'].sudo().search(domain)
        total_shipped = 0.0
        for picking in pickings:
            # Destination is within the same warehouse → goods never left → skip.
            if picking.location_dest_id.id in same_premises_ids:
                continue
            for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                # Odoo 18: move.quantity is the done qty.
                done_qty = getattr(move, 'quantity', None) or getattr(move, 'quantity_done', 0.0)
                total_shipped += done_qty * move.product_id.lst_price

        return max(self.initial_sum_insured - total_shipped, 0.0)

    # ── Compute: balance_sum_insured (F&B only) ──────────────────────────────────────────

    @api.depends('initial_sum_insured', 'warehouse_id', 'floater_location_ids',
                 'is_fire_burglary', 'state', 'policy_type')
    def _compute_balance_sum_insured(self):
        for rec in self:
            if not rec.is_fire_burglary or rec.state == 'expired':
                rec.balance_sum_insured = 0.0
            else:
                rec.balance_sum_insured = rec._get_fb_balance()

    def _get_fb_balance(self):
        """
        F&B balance_sum_insured = initial_sum_insured − current inventory value.

        The sum_insured for F&B is NEVER reduced by shipments. Instead, the balance
        shows how much coverage sits above the stock currently held in the warehouse:
          • When inventory = 1 L and sum_insured = 2 L → balance = 1 L.
          • When goods worth 50 K are shipped out, inventory drops to 50 K → balance = 1.5 L.
        """
        self.ensure_one()
        if self.policy_type == 'individual' and self.warehouse_id:
            warehouses = self.warehouse_id
        elif self.policy_type == 'floater' and self.floater_location_ids:
            warehouses = self.floater_location_ids
        else:
            warehouses = self.env['stock.warehouse'].search(
                [('company_id', '=', self.company_id.id)])

        total_inventory = 0.0
        for wh in warehouses:
            if not wh.lot_stock_id:
                continue
            quants = self.env['stock.quant'].sudo().search(
                [('location_id', 'child_of', wh.lot_stock_id.id)])
            total_inventory += sum(q.quantity * q.product_id.lst_price for q in quants)

        return max(self.initial_sum_insured - total_inventory, 0.0)

    # ── Other computes ───────────────────────────────────────────────────────────────────

    @api.depends('initial_sum_insured')
    def _compute_sum_insured_words(self):
        for rec in self:
            try:
                from num2words import num2words
                rec.sum_insured_words = (
                    num2words(int(rec.initial_sum_insured), lang='en_IN').title() + ' Rupees Only'
                ) if rec.initial_sum_insured else ''
            except Exception:
                rec.sum_insured_words = ''

    @api.depends('premium', 'initial_sum_insured')
    def _compute_premium_pct(self):
        for rec in self:
            rec.premium_percentage = (
                rec.premium / rec.initial_sum_insured * 100
            ) if rec.initial_sum_insured else 0.0

    @api.depends('payment_ids.amount')
    def _compute_total_premium(self):
        for rec in self:
            rec.total_premium_paid = sum(rec.payment_ids.mapped('amount'))

    # ── ORM overrides ────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('insurance.policy') or 'New'
                )
        return super().create(vals_list)

    # ── ORM overrides ─────────────────────────────────────────────────────────────────────

    def write(self, vals):
        # Enforce: policy cannot be set to Active state unless premium is paid.
        # This only applies to explicit state changes (not on create).
        if vals.get('state') == 'active':
            for rec in self:
                new_is_paid = vals.get('is_paid', rec.is_paid)
                if not new_is_paid:
                    raise UserError(
                        f"Policy '{rec.name}' cannot be set to Active until the "
                        f"insurance premium is paid. Please complete the payment "
                        f"request and approval process first."
                    )
        return super().write(vals)

    # ── Actions ──────────────────────────────────────────────────────────────────────────

    def action_mark_expired(self):
        for rec in self:
            rec.state = 'expired'
            # sum_insured and balance_sum_insured are computed fields;
            # switching state to 'expired' causes them to return their zero/fallback values.

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

    def action_check_tolerance(self):
        """Evaluate tolerance breach on the current recordset.

        Called automatically after a stock picking is validated (real-time).
        Each policy is evaluated independently:
          - Marine (with warehouse): alert when Remaining Sum Insured ≤ tolerance % of limit.
          - F&B: alert when Balance Sum Insured ≤ tolerance % of limit.
          - Alert latch (tolerance_notified) prevents repeated notifications for the same breach.
          - Latch resets when coverage recovers above the threshold (mainly relevant for F&B
            as inventory can fluctuate — rising stock lowers the balance, shipping raises it).
        """
        for policy in self:
            if not policy.tolerance_percent or not policy.initial_sum_insured:
                continue
            if policy.state != 'active':
                continue

            if policy.is_marine and policy.warehouse_id:
                remaining = policy.sum_insured          # computed: initial − shipped
            elif policy.is_fire_burglary:
                remaining = policy.balance_sum_insured  # computed: initial − inventory
            else:
                continue

            threshold_amount = policy.initial_sum_insured * policy.tolerance_percent / 100.0
            breached = remaining <= threshold_amount

            if breached and not policy.tolerance_notified:
                policy._send_tolerance_alert(remaining, threshold_amount)
                policy.tolerance_notified = True
            elif not breached and policy.tolerance_notified:
                # Coverage recovered — reset latch so the next breach sends a fresh alert.
                policy.tolerance_notified = False

    def _send_tolerance_alert(self, remaining, threshold_amount):
        """Post a chatter message and notify all Insurance team members."""
        self.ensure_one()

        # Collect partner IDs of all users in both insurance groups.
        admin_group = self.env.ref(
            'ks_insurance_management.group_insurance_admin', raise_if_not_found=False)
        user_group = self.env.ref(
            'ks_insurance_management.group_insurance_user', raise_if_not_found=False)
        partners = self.env['res.partner']
        for group in filter(None, [admin_group, user_group]):
            partners |= group.users.mapped('partner_id')
        partner_ids = partners.ids

        if self.is_marine:
            field_label = 'Remaining Sum Insured'
        else:
            field_label = 'Balance Sum Insured'

        body = (
            f"<b>\u26a0\ufe0f Insurance Tolerance Alert</b><br/>"
            f"Policy <b>{self.policy_number or self.name}</b> "
            f"({self.insurance_type_id.name}) has reached the configured tolerance level.<br/><br/>"
            f"<b>{field_label}:</b> \u20b9{remaining:,.2f}<br/>"
            f"<b>Tolerance threshold ({self.tolerance_percent:.1f}% of Sum Insured):</b> "
            f"\u20b9{threshold_amount:,.2f}<br/>"
            f"<b>Original Sum Insured:</b> \u20b9{self.initial_sum_insured:,.2f}<br/><br/>"
            f"Please review the policy and consider renewal or top-up."
        )
        self.message_post(
            body=body,
            subject=f"Insurance Tolerance Alert \u2014 {self.policy_number or self.name}",
            partner_ids=partner_ids,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
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
            'default_initial_sum_insured': self.initial_sum_insured,
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
        """Legacy no-op. sum_insured (Marine) and balance_sum_insured (F&B) are now
        computed automatically from stock data and cannot be written to directly."""
        pass

    def _get_avg_inventory(self):
        """Used by declaration reports to get current inventory value."""
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

    # ── Constraints ──────────────────────────────────────────────────────────────────────

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
