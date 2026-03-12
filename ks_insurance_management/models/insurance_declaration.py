# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class InsuranceDeclaration(models.Model):
    _name = 'insurance.declaration'
    _description = 'Insurance Declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(string='Reference', default='New', copy=False)
    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        ondelete='cascade',
    )
    insurance_type_id = fields.Many2one(
        related='policy_id.insurance_type_id',
        string='Insurance Type',
        store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    declaration_type = fields.Selection([
        ('marine', 'Marine'), ('fire_burglary', 'Fire & Burglary'),
    ], string='Declaration Type', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    sales_amount = fields.Float(string='Sales Amount (Incl. GST)')
    marine_applicability = fields.Selection([
        ('exim', 'EXIM'), ('domestic', 'Domestic'),
        ('both', 'Both'), ('russia', 'Russia Only'),
    ], string='Marine Applicability')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    avg_inventory_value = fields.Float(string='Average Inventory Value')
    declaration_amount = fields.Float(string='Declaration Amount', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('sent', 'Sent'),
    ], default='draft', string='Status', tracking=True)
    email_to = fields.Char(string='Email To')
    notes = fields.Text(string='Notes')

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
        self.sales_amount = sum(invoices.mapped('amount_total'))
        self.declaration_amount = self.sales_amount

    def _compute_avg_inventory(self):
        if not self.warehouse_id:
            return
        quants = self.env['stock.quant'].search(
            [('location_id', 'child_of', self.warehouse_id.lot_stock_id.id)])
        total = sum(q.quantity * q.product_id.standard_price for q in quants)
        self.avg_inventory_value = total
        self.declaration_amount = total

    def _get_marine_invoice_lines(self):
        """Invoice-wise lines for Marine Declaration report (xlsx-style format). Returns account.move recordset."""
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

    def action_draft_email(self):
        self.ensure_one()
        template = self._get_declaration_mail_template()
        if template and not template.report_template_ids:
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
