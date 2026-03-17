# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InsuranceDeclaration(models.Model):
    _name = 'insurance.declaration'
    _description = 'Insurance Declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(
        string='Reference',
        default='New',
        copy=False,
        help='Auto-generated unique reference for this declaration (e.g. DECL/2025/0001).',
    )
    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        ondelete='cascade',
        help='The insurance policy against which this declaration is being submitted. '
             'Only Marine or Fire & Burglary policies are applicable.',
    )
    insurance_type_id = fields.Many2one(
        related='policy_id.insurance_type_id',
        string='Insurance Type',
        store=True,
        help='Insurance type auto-fetched from the selected policy for reference.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='The company for which this declaration is being filed. '
             'Auto-populated from the selected policy.',
    )
    declaration_type = fields.Selection([
        ('marine', 'Marine'), ('fire_burglary', 'Fire & Burglary'),
    ], string='Declaration Type', required=True,
        help='Marine: declaration based on sales turnover (invoices) for the period.\n'
             'Fire & Burglary: declaration based on average inventory value held at a warehouse.',
    )
    date_from = fields.Date(
        string='Date From',
        required=True,
        help='Start date of the declaration period. '
             'For Marine: sales invoices from this date are included. '
             'For Fire & Burglary: inventory is valued as of this date range.',
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        help='End date of the declaration period. '
             'The declaration letter will show this as the "Date of Declaration".',
    )
    sales_amount = fields.Float(
        string='Sales Amount (Incl. GST)',
        help='Total value of all posted customer invoices (minus credit notes) '
             'for the selected period. Auto-computed for Marine declarations.',
    )
    marine_applicability = fields.Selection([
        ('exim', 'EXIM'), ('domestic', 'Domestic'),
        ('both', 'Both'), ('russia', 'Russia Only'),
    ], string='Marine Applicability',
        help='Scope of marine coverage for this declaration:\n'
             'EXIM – Export/Import shipments only.\n'
             'Domestic – Within-India transit only.\n'
             'Both – All shipments.\n'
             'Russia Only – Specific to Russia trade route.',
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='The warehouse whose inventory value is used for a Fire & Burglary declaration. '
             'Auto-populated from the policy\'s covered location.',
    )
    avg_inventory_value = fields.Float(
        string='Average Inventory Value',
        help='Current stock-on-hand value at the selected warehouse, '
             'computed as: Σ (qty × standard price) for all products in stock. '
             'Used as the declaration amount for Fire & Burglary.',
    )
    declaration_amount = fields.Float(
        string='Declaration Amount',
        tracking=True,
        help='The amount being declared to the insurer for this period.\n'
             'Marine: equals the total sales amount (incl. GST).\n'
             'Fire & Burglary: equals the average inventory value at the warehouse.\n'
             'For Marine policies, confirming this declaration will deduct this amount '
             'from the policy\'s Balance Sum Insured.',
    )
    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('sent', 'Sent'),
    ], default='draft', string='Status', tracking=True,
        help='Draft: declaration is created but not yet confirmed.\n'
             'Confirmed: declaration is approved; balance deducted from Marine policy.\n'
             'Sent: declaration letter has been emailed to the insurer.',
    )
    email_to = fields.Char(
        string='Email To',
        help='Email address of the insurance company contact to whom the declaration will be sent. '
             'Auto-populated from the insurer\'s email address on the policy.',
    )
    notes = fields.Text(
        string='Notes',
        help='Internal remarks about this declaration '
             '(e.g. pending invoices, adjustments, special consignments).',
    )

    @api.onchange('policy_id')
    def _onchange_policy_id(self):
        """Auto-populate fields from the selected policy."""
        if not self.policy_id:
            return
        policy = self.policy_id
        if policy.company_id:
            self.company_id = policy.company_id
        if policy.is_marine:
            self.declaration_type = 'marine'
        elif policy.is_fire_burglary:
            self.declaration_type = 'fire_burglary'
        if policy.insurance_company_id and policy.insurance_company_id.email:
            self.email_to = policy.insurance_company_id.email
        if policy.insurance_type_id and policy.insurance_type_id.marine_applicability:
            self.marine_applicability = policy.insurance_type_id.marine_applicability
        if policy.is_fire_burglary and not policy.floater_location_ids:
            warehouses = self.env['stock.warehouse'].search(
                [('company_id', '=', policy.company_id.id)], limit=1)
            if warehouses:
                self.warehouse_id = warehouses[0]

    @api.onchange('declaration_type', 'date_from', 'date_to', 'warehouse_id')
    def _onchange_compute_amounts(self):
        if not self.date_from or not self.date_to:
            return
        if self.declaration_type == 'marine':
            self._compute_marine_sales()
        elif self.declaration_type == 'fire_burglary':
            self._compute_avg_inventory()

    def _compute_marine_sales(self):
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        invoices = self.env['account.move'].search(domain)
        total = 0.0
        for inv in invoices:
            if inv.move_type == 'out_invoice':
                total += inv.amount_total
            else:
                total -= inv.amount_total
        self.sales_amount = total
        self.declaration_amount = total

    def _compute_avg_inventory(self):
        if not self.warehouse_id or not self.warehouse_id.lot_stock_id:
            return
        quants = self.env['stock.quant'].search(
            [('location_id', 'child_of', self.warehouse_id.lot_stock_id.id)])
        total = sum(q.quantity * q.product_id.standard_price for q in quants)
        self.avg_inventory_value = total
        self.declaration_amount = total

    def _get_marine_invoice_lines(self):
        """Invoice-wise lines for Marine Declaration report. Returns account.move recordset."""
        self.ensure_one()
        if self.declaration_type != 'marine':
            return self.env['account.move']
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        return self.env['account.move'].search(domain, order='invoice_date, name')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'insurance.declaration') or 'New'
        return super().create(vals_list)

    @api.constrains('date_from', 'date_to')
    def _check_declaration_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError(_("Date To must be on or after Date From."))

    def action_confirm(self):
        self.state = 'confirmed'
        if self.declaration_type == 'marine' and self.policy_id.is_marine:
            self.policy_id.deduct_from_balance(self.declaration_amount)

    def action_mark_sent(self):
        """Manually mark this declaration as Sent after emailing."""
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'sent'
                rec.message_post(
                    body=_("Declaration marked as Sent."),
                    subtype_xmlid='mail.mt_note',
                )

    def action_draft_email(self):
        self.ensure_one()
        template = self._get_declaration_mail_template()
        if template:
            self._fix_template_lang(template)
            if not template.report_template_ids:
                self._attach_declaration_report_to_template(template)
        ctx = {
            'default_model': 'insurance.declaration',
            'default_res_ids': [self.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'target': 'new',
            'context': ctx,
        }

    def _get_declaration_mail_template(self):
        """Resolve declaration email template by ref or by name (avoids External ID not found)."""
        template = self.env.ref(
            'ks_insurance_management.email_template_declaration',
            raise_if_not_found=False,
        )
        if not template:
            template = self.env['mail.template'].search(
                [
                    ('model_id.model', '=', 'insurance.declaration'),
                    ('name', '=', 'Insurance: Declaration Email'),
                ],
                limit=1,
            )
        return template

    def _fix_template_lang(self, template):
        """Patch lang and body_html if DB still has broken values from before the fix."""
        vals = {}
        correct_lang = '{{ object.company_id.partner_id.lang or object.env.user.lang }}'
        if template.lang != correct_lang and (
            not template.lang
            or ('company_id.lang' in template.lang and 'partner_id' not in template.lang)
            or 'object.env.lang' in template.lang
        ):
            vals['lang'] = correct_lang
        body = template.body_html or ''
        if 'partner_id.signature' in body:
            import re
            body = re.sub(
                r'\s*<t t-if="object\.company_id\.partner_id and object\.company_id\.partner_id\.signature">.*?</t>',
                '', body, flags=re.DOTALL,
            )
            vals['body_html'] = body
        if vals:
            template.sudo().write(vals)

    def _attach_declaration_report_to_template(self, template):
        """Ensure the declaration letter report is linked to the template so it is sent as attachment."""
        report = self.env['ir.actions.report'].search(
            [('report_name', '=', 'ks_insurance_management.report_declaration_letter_template')],
            limit=1,
        )
        if report and report not in template.report_template_ids:
            template.report_template_ids = [(4, report.id)]

    def action_print_declaration(self):
        report = self.env['ir.actions.report'].search(
            [('report_name', '=', 'ks_insurance_management.report_declaration_letter_template')],
            limit=1,
        )
        if not report:
            raise UserError(
                _('Declaration Letter report not found. Please upgrade the Insurance Management module.')
            )
        return report.report_action(self)
