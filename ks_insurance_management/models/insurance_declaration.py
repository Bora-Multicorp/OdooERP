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
        template = self.env.ref(
            'ks_insurance_management.email_template_declaration',
            raise_if_not_found=False,
        )
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

    def action_print_declaration(self):
        return self.env.ref(
            'ks_insurance_management.action_report_declaration_letter'
        ).report_action(self)
