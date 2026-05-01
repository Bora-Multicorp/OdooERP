from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    price_unit_incl = fields.Float(
        string="Unit Price (Incl. GST)",
        digits="Product Price",
        store=True,
    )
    ks_editing_from_incl = fields.Boolean(default=False, store=False)

    @api.onchange("price_unit", "taxes_id", "order_id.currency_id")
    def _onchange_compute_price_incl(self):
        if self.ks_editing_from_incl:
            self.ks_editing_from_incl = False
            return
        taxes = self.taxes_id
        currency = self.currency_id
        if not taxes:
            self.price_unit_incl = self.price_unit
        else:
            result = taxes.compute_all(
                self.price_unit, currency=currency, quantity=1.0,
                product=self.product_id, partner=self.order_id.partner_id,
            )
            self.price_unit_incl = result["total_included"]

    @api.onchange("price_unit_incl")
    def _onchange_price_unit_incl(self):
        taxes = self.taxes_id
        currency = self.currency_id
        if taxes:
            expected = taxes.compute_all(
                self.price_unit, currency=currency, quantity=1.0,
                product=self.product_id, partner=self.order_id.partner_id,
            )["total_included"]
            if currency:
                expected = currency.round(expected)
            if abs(self.price_unit_incl - expected) < (currency.rounding if currency else 0.01):
                return
        elif abs(self.price_unit_incl - self.price_unit) < 0.01:
            return
        self.ks_editing_from_incl = True
        self._set_price_unit_from_incl()

    def _set_price_unit_from_incl(self):
        taxes = self.taxes_id
        currency = self.currency_id
        if not taxes:
            self.price_unit = self.price_unit_incl
        else:
            factor = taxes.compute_all(
                1.0, currency=currency, quantity=1.0,
                product=self.product_id, partner=self.order_id.partner_id,
            )["total_included"]
            price_excl = self.price_unit_incl / factor if factor else self.price_unit_incl
            self.price_unit = currency.round(price_excl) if currency else round(price_excl, 2)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if 'price_unit_incl' not in vals:
                record._sync_price_incl()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('_skip_price_incl_sync'):
            if ('price_unit' in vals or 'taxes_id' in vals) and 'price_unit_incl' not in vals:
                for record in self:
                    record._sync_price_incl()
        return res

    def _sync_price_incl(self):
        taxes = self.taxes_id
        currency = self.currency_id
        if not taxes:
            incl = self.price_unit
        else:
            result = taxes.compute_all(
                self.price_unit, currency=currency, quantity=1.0,
                product=self.product_id, partner=self.order_id.partner_id,
            )
            incl = result["total_included"]
        self.with_context(_skip_price_incl_sync=True).write({'price_unit_incl': incl})
