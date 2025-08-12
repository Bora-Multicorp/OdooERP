from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_exchange = fields.Boolean(
        string='Apply Manual Currency',
        help='Enable this to apply a manual currency rate to order lines.'
    )
    rate = fields.Float(
        string='Manual Exchange Rate',
        help='Specify the manual currency rate for this order',
        default=1
    )

    is_bora_company = fields.Boolean(
        string="Is Bora Electronic Focz",
        compute='_compute_is_bora_company',
        store=False
    )

    @api.depends('company_id')
    def _compute_is_bora_company(self):
        for record in self:
            user_company = self.env.user.company_id

            # Use 'ilike' to find a company name that contains "Bora Electronic Focz"
            # This is a robust way to handle slight variations in the name.
            if 'bora electronic focz' in user_company.name.lower():
                record.is_bora_company = True
            elif user_company.parent_id and 'bora electronic focz' in user_company.parent_id.name.lower():
                record.is_bora_company = True
            else:
                record.is_bora_company = False

    @api.onchange('rate', 'is_exchange')
    def _onchange_rate(self):
        """Recalculate unit price in UI when manual rate changes."""
        self._apply_manual_rate()

    @api.model
    def create(self, vals):
        order = super().create(vals)
        order._apply_manual_rate()
        return order

    def write(self, vals):
        res = super().write(vals)
        self._apply_manual_rate()
        return res


    def _apply_manual_rate(self):
        """Apply manual exchange rate to order lines."""
        for order in self:
            if order.is_exchange and order.rate > 0:
                for line in order.order_line:
                    if line.product_id:
                        base_price_aed = line.product_id.list_price
                        line.price_unit = base_price_aed * order.rate
            elif not order.is_exchange:
                for line in order.order_line:
                    if line.product_id:
                        line.price_unit = line.product_id.list_price


    def _get_currency_rate(self):
        """Ensure manual rate is used in accounting/invoicing."""
        self.ensure_one()
        if self.is_exchange and self.rate > 0:
            return self.rate
        return super()._get_currency_rate()
