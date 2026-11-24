# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    purchase_tds_ids = fields.One2many(
        'purchase.tds',
        'bill_id',
        string='Purchase TDS Entries',
    )
    purchase_tds_count = fields.Integer(
        string='PO TDS Count',
        compute='_compute_purchase_tds_count',
    )
    po_tds_amount = fields.Monetary(
        string="PO TDS Amount",
        compute='_compute_purchase_tds_details',
        currency_field='currency_id',
    )
    po_tds_base = fields.Monetary(
        string="PO TDS Base Amount",
        compute='_compute_purchase_tds_details',
        currency_field='currency_id',
    )
    po_tds_tax_id = fields.Many2one(
        'account.tax',
        string="PO TDS Tax",
        compute='_compute_purchase_tds_details',
    )
    po_tds_section = fields.Many2one(
        'l10n_in.section.alert',
        string="PO TDS Section",
        compute='_compute_purchase_tds_details',
    )
    po_tds_purchase_id = fields.Many2one(
        'purchase.order',
        string="Purchase Order",
        compute='_compute_purchase_tds_details',
    )
    po_tds_reference = fields.Char(
        string="PO TDS Reference",
        compute='_compute_purchase_tds_details',
    )
    po_tds_date = fields.Date(
        string="PO TDS Date",
        compute='_compute_purchase_tds_details',
    )

    def _link_purchase_tds(self):
        for move in self:
            if move.move_type == 'in_invoice' and move.id and not isinstance(move.id, models.NewId):
                source_pos = move.invoice_line_ids.mapped('purchase_line_id.order_id')
                if not source_pos and move.invoice_origin:
                    pos = self.env['purchase.order'].search([
                        ('name', '=', move.invoice_origin),
                        ('company_id', '=', move.company_id.id),
                    ])
                    source_pos |= pos
                unlinked_tds = source_pos.mapped('tds_ids').filtered(lambda t: not t.bill_id)
                if unlinked_tds:
                    unlinked_tds.sudo().write({'bill_id': move.id})

    @api.depends('purchase_tds_ids', 'invoice_line_ids.purchase_line_id', 'invoice_origin')
    def _compute_purchase_tds_count(self):
        for move in self:
            move._link_purchase_tds()
            move.purchase_tds_count = len(move.purchase_tds_ids)

    @api.depends(
        'purchase_tds_ids',
        'purchase_tds_ids.amount',
        'purchase_tds_ids.base',
        'purchase_tds_ids.tax_id',
        'purchase_tds_ids.date',
        'purchase_tds_ids.reference',
        'purchase_tds_ids.purchase_id',
    )
    def _compute_purchase_tds_details(self):
        for move in self:
            if move.purchase_tds_ids:
                tds = move.purchase_tds_ids[0]
                move.po_tds_amount = sum(move.purchase_tds_ids.mapped('amount'))
                move.po_tds_base = tds.base
                move.po_tds_tax_id = tds.tax_id
                move.po_tds_section = tds.tax_id.l10n_in_section_id
                move.po_tds_purchase_id = tds.purchase_id
                move.po_tds_reference = tds.reference
                move.po_tds_date = tds.date
            else:
                move.po_tds_amount = 0.0
                move.po_tds_base = 0.0
                move.po_tds_tax_id = False
                move.po_tds_section = False
                move.po_tds_purchase_id = False
                move.po_tds_reference = False
                move.po_tds_date = False

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._link_purchase_tds()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('invoice_line_ids', 'invoice_origin')):
            self._link_purchase_tds()
        return res

    def action_post(self):
        for move in self:
            if move.move_type in ('in_invoice', 'in_refund') and move.purchase_tds_count > 0:
                posted_tds_moves = move.l10n_in_withhold_move_ids.filtered(lambda m: m.state == 'posted')
                if not posted_tds_moves:
                    po_ref = move.po_tds_purchase_id.name or move.po_tds_reference or _("Purchase Order")
                    raise UserError(_(
                        "TDS was deducted on the Purchase Order (%(po_ref)s). "
                        "You must create a TDS Entry before posting this bill. "
                        "Please click the 'TDS Entry' button to create and confirm the TDS entry."
                    ) % {'po_ref': po_ref})
        res = super().action_post()
        for move in self:
            if move.move_type in ('in_invoice', 'in_refund'):
                posted_tds_moves = move.l10n_in_withhold_move_ids.filtered(lambda m: m.state == 'posted')
                if posted_tds_moves:
                    inv_lines = move.line_ids.filtered(
                        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                    )
                    wh_lines = posted_tds_moves.line_ids.filtered(
                        lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                    )
                    if inv_lines and wh_lines:
                        (inv_lines + wh_lines).reconcile()
        return res

    def bora_action_approve_bill(self):
        self.ensure_one()
        if self.move_type in ('in_invoice', 'in_refund') and self.purchase_tds_count > 0:
            posted_tds_moves = self.l10n_in_withhold_move_ids.filtered(lambda m: m.state == 'posted')
            if not posted_tds_moves:
                po_ref = self.po_tds_purchase_id.name or self.po_tds_reference or _("Purchase Order")
                raise UserError(_(
                    "TDS was deducted on the Purchase Order (%(po_ref)s). "
                    "Please create the TDS Entry using the 'TDS Entry' button before approving this bill."
                ) % {'po_ref': po_ref})
        return super().bora_action_approve_bill()

    def _bora_do_approve_bill_with_reason(self, reason, current_user):
        self.ensure_one()
        if self.move_type in ('in_invoice', 'in_refund') and self.purchase_tds_count > 0:
            posted_tds_moves = self.l10n_in_withhold_move_ids.filtered(lambda m: m.state == 'posted')
            if not posted_tds_moves:
                po_ref = self.po_tds_purchase_id.name or self.po_tds_reference or _("Purchase Order")
                raise UserError(_(
                    "TDS was deducted on the Purchase Order (%(po_ref)s). "
                    "Please create the TDS Entry using the 'TDS Entry' button before approving this bill."
                ) % {'po_ref': po_ref})
        return super()._bora_do_approve_bill_with_reason(reason, current_user)

    def action_view_purchase_tds(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Purchase TDS'),
            'res_model': 'purchase.tds',
            'view_mode': 'list,form',
            'domain': [('bill_id', '=', self.id)],
            'context': {
                'default_bill_id': self.id,
            },
        }
        if len(self.purchase_tds_ids) == 1:
            form_view = self.env.ref('purchase_tds.view_purchase_tds_form', raise_if_not_found=False)
            action['views'] = [(form_view.id, 'form')] if form_view else [(False, 'form')]
            action['res_id'] = self.purchase_tds_ids.id
        return action
