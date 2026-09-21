# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models

class PurchaseTDS(models.Model):
    _name = 'purchase.tds'
    _description = 'Purchase TDS'
    _rec_name = 'reference'

    purchase_id = fields.Many2one('purchase.order', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    tax_id = fields.Many2one('account.tax', required=True)
    base = fields.Monetary(string="Base Amount")
    amount = fields.Monetary(string="TDS Amount", compute='_compute_amount', store=True)
    currency_id = fields.Many2one(
        related='purchase_id.currency_id',
        store=True,
    )
    reference = fields.Char(string="Reference")

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for wizard in self:
            tax_amount = 0.0
            if wizard.tax_id:
                tax_amount = wizard._tax_compute_all_helper(wizard.base, wizard.tax_id)
            wizard.amount = tax_amount

    # === Helper methods ====
    @api.model
    def _tax_compute_all_helper(self, base, tax_id):
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = tax_id.compute_all(
            base,
            currency=tax_id.company_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
        tax_amount = abs(tax_amount)
        return tax_amount

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not self.env.context.get('skip_tds_chatter') and record.purchase_id:
                currency = record.currency_id or record.purchase_id.currency_id
                currency_symbol = currency.symbol or ""
                body = Markup(
                    "<b>TDS Entry Added</b><br/>"
                    "• <b>Reference:</b> %(ref)s<br/>"
                    "• <b>Tax:</b> %(tax)s<br/>"
                    "• <b>Base Amount:</b> %(symbol)s %(base)s<br/>"
                    "• <b>TDS Amount:</b> %(symbol)s %(amount)s"
                ) % {
                    'ref': record.reference or _("N/A"),
                    'tax': record.tax_id.display_name if record.tax_id else _("N/A"),
                    'symbol': currency_symbol,
                    'base': f"{record.base:,.2f}",
                    'amount': f"{record.amount:,.2f}",
                }
                record.purchase_id.message_post(body=body, subtype_xmlid="mail.mt_note")
        return records

    def write(self, vals):
        tracked = {}
        for record in self:
            tracked[record.id] = {
                'base': record.base,
                'tax_id': record.tax_id,
                'amount': record.amount,
                'reference': record.reference,
            }
        res = super().write(vals)
        for record in self:
            if not self.env.context.get('skip_tds_chatter') and record.purchase_id:
                old = tracked.get(record.id, {})
                changes = []
                currency = record.currency_id or record.purchase_id.currency_id
                currency_symbol = currency.symbol or ""
                if 'base' in vals and old.get('base') != record.base:
                    changes.append(
                        Markup("• <b>Base Amount:</b> %(symbol)s %(old)s &rarr; %(symbol)s %(new)s") % {
                            'symbol': currency_symbol,
                            'old': f"{old.get('base', 0.0):,.2f}",
                            'new': f"{record.base:,.2f}",
                        }
                    )
                if 'tax_id' in vals and old.get('tax_id') != record.tax_id:
                    changes.append(
                        Markup("• <b>Tax:</b> %(old)s &rarr; %(new)s") % {
                            'old': old.get('tax_id').display_name if old.get('tax_id') else _("None"),
                            'new': record.tax_id.display_name if record.tax_id else _("None"),
                        }
                    )
                if old.get('amount') != record.amount:
                    changes.append(
                        Markup("• <b>TDS Amount:</b> %(symbol)s %(old)s &rarr; %(symbol)s %(new)s") % {
                            'symbol': currency_symbol,
                            'old': f"{old.get('amount', 0.0):,.2f}",
                            'new': f"{record.amount:,.2f}",
                        }
                    )
                if changes:
                    body = Markup(
                        "<b>TDS Entry Modified (%(ref)s)</b><br/>%(changes)s"
                    ) % {
                        'ref': record.reference or _("N/A"),
                        'changes': Markup("<br/>").join(changes),
                    }
                    record.purchase_id.message_post(body=body, subtype_xmlid="mail.mt_note")
        return res

    def unlink(self):
        orders_to_log = []
        for record in self:
            if not self.env.context.get('skip_tds_chatter') and record.purchase_id:
                currency = record.currency_id or record.purchase_id.currency_id
                currency_symbol = currency.symbol or ""
                body = Markup(
                    "<b>TDS Entry Deleted (%(ref)s)</b><br/>"
                    "• <b>Base Amount:</b> %(symbol)s %(base)s<br/>"
                    "• <b>TDS Amount:</b> %(symbol)s %(amount)s"
                ) % {
                    'ref': record.reference or _("N/A"),
                    'symbol': currency_symbol,
                    'base': f"{record.base:,.2f}",
                    'amount': f"{record.amount:,.2f}",
                }
                orders_to_log.append((record.purchase_id, body))
        res = super().unlink()
        for order, body in orders_to_log:
            order.message_post(body=body, subtype_xmlid="mail.mt_note")
        return res
