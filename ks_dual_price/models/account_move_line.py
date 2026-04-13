from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    price_unit_incl = fields.Float(
        string="Unit Price (Incl. GST)",
        digits="Product Price",
        compute="_compute_price_unit_incl",
        inverse="_inverse_price_unit_incl",
        store=True,
    )

    @api.depends("price_unit", "tax_ids", "move_id.currency_id")
    def _compute_price_unit_incl(self):
        for line in self:
            taxes = line.tax_ids
            currency = line.currency_id
            if not taxes:
                line.price_unit_incl = line.price_unit
            else:
                result = taxes.compute_all(
                    line.price_unit,
                    currency=currency,
                    quantity=1.0,
                    product=line.product_id,
                    partner=line.move_id.partner_id,
                )
                line.price_unit_incl = result["total_included"]

    def _inverse_price_unit_incl(self):
        for line in self:
            line._set_price_unit_from_incl()

    @api.onchange("price_unit_incl")
    def _onchange_price_unit_incl(self):
        self._set_price_unit_from_incl()

    def _set_price_unit_from_incl(self):
        taxes = self.tax_ids
        currency = self.currency_id
        if not taxes:
            self.price_unit = self.price_unit_incl
        else:
            factor = taxes.compute_all(
                1.0, currency=currency, quantity=1.0
            )["total_included"]
            price_excl = self.price_unit_incl / factor if factor else self.price_unit_incl
            self.price_unit = currency.round(price_excl) if currency else round(price_excl, 2)
