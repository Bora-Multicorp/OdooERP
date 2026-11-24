# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
import odoo.addons.l10n_in_withholding.wizard.l10n_in_withhold_wizard as orig_wizard


class L10nInWithholdWizard(models.TransientModel):
    _inherit = 'l10n_in.withhold.wizard'

    @api.model
    def default_get(self, fields_list):
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids', [])
        if active_model == 'account.move' and active_ids and len(active_ids) == 1:
            active_record = self.env['account.move'].browse(active_ids[0])
            if active_record.move_type in ('in_invoice', 'in_refund') and active_record.state in ('draft', 'bill_approval_pending'):
                # Bypass the state == 'posted' UserError check in l10n_in_withholding
                result = super(orig_wizard.L10nInWithholdWizard, self).default_get(fields_list)
                ref_name = active_record.name if (active_record.name and active_record.name != '/') else (active_record.ref or _("Draft Bill"))
                result['reference'] = _("TDS of %s", ref_name)
                result['related_move_id'] = active_record.id

                # Link TDS from purchase orders if not yet linked
                active_record._link_purchase_tds()

                if active_record.purchase_tds_ids:
                    po_tds = active_record.purchase_tds_ids[0]
                    if po_tds.date:
                        result['date'] = po_tds.date
                    if po_tds.reference and (not active_record.name or active_record.name == '/'):
                        result['reference'] = po_tds.reference
                    lines = []
                    for tds in active_record.purchase_tds_ids:
                        base = active_record.amount_untaxed if active_record.amount_untaxed > 0 else tds.base
                        tax = tds.tax_id
                        calc_amount = self.env['l10n_in.withhold.wizard.line']._tax_compute_all_helper(base, tax) if tax else 0.0
                        lines.append(Command.create({
                            'tax_id': tax.id,
                            'base': base,
                            'amount': calc_amount,
                        }))
                    result['withhold_line_ids'] = lines
                return result

        result = super().default_get(fields_list)
        if active_model == 'account.move' and active_ids and len(active_ids) == 1:
            active_record = self.env['account.move'].browse(active_ids[0])
            if active_record.move_type in ('in_invoice', 'in_refund'):
                active_record._link_purchase_tds()
                if active_record.purchase_tds_ids and not result.get('withhold_line_ids'):
                    lines = []
                    for tds in active_record.purchase_tds_ids:
                        base = active_record.amount_untaxed if active_record.amount_untaxed > 0 else tds.base
                        tax = tds.tax_id
                        calc_amount = self.env['l10n_in.withhold.wizard.line']._tax_compute_all_helper(base, tax) if tax else 0.0
                        lines.append(Command.create({
                            'tax_id': tax.id,
                            'base': base,
                            'amount': calc_amount,
                        }))
                    result['withhold_line_ids'] = lines
                if active_record.purchase_tds_ids:
                    po_tds = active_record.purchase_tds_ids[0]
                    if po_tds.date and not result.get('date'):
                        result['date'] = po_tds.date
        return result

    def action_create_and_post_withhold(self):
        self.ensure_one()
        # Fallback for company withholding account if not set in settings
        withholding_account_id = self.company_id.l10n_in_withholding_account_id
        if not withholding_account_id:
            fallback_acc = self.env['account.account'].search([
                ('company_id', '=', self.company_id.id),
                '|', ('name', 'ilike', 'withholding'), ('name', 'ilike', 'TDS'),
            ], limit=1)
            if fallback_acc:
                self.company_id.sudo().l10n_in_withholding_account_id = fallback_acc.id
                withholding_account_id = fallback_acc

        if self.related_move_id and self.related_move_id.state != 'posted':
            self._validate_withhold_data_on_post(withholding_account_id)

            vals = self._prepare_withhold_header()
            move_lines = self._prepare_withhold_move_lines(withholding_account_id)
            vals['line_ids'] = [Command.create(line) for line in move_lines]
            withhold = self.with_company(self.company_id).env['account.move'].create(vals)
            withhold.action_post()

            # Bill is not posted yet, so defer reconciliation until the bill is posted.
            related_record = self.related_move_id or self.related_payment_id
            msg_body = Markup("%s %s: <a href='#' data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
                _("TDS created from"),
                self.type_name,
                related_record._name,
                related_record.id,
                related_record.name or related_record.ref or _("Bill")
            )
            withhold.message_post(body=msg_body)
            self.related_move_id.message_post(
                body=Markup("%s: <a href='#' data-oe-model='%s' data-oe-id='%s'>%s</a>") % (
                    _("TDS Entry Created"),
                    withhold._name,
                    withhold.id,
                    withhold.name
                )
            )
            return withhold

        return super().action_create_and_post_withhold()
