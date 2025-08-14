from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_exchange = fields.Boolean(
        string='Apply Manual Currency',
        help='Enable this to apply a manual currency rate to order lines.'
    )
    manual_exchange_rate = fields.Float(
        string='Manual Exchange Rate',
        digits='Product Price',
        help='Specify the manual currency rate for this order.',
        default=0.0
    )
    is_bora_electronics = fields.Boolean(
        string="Is Bora Electronics Company",
        compute='_compute_is_bora_electronics',
        store=False
    )

    @api.depends('company_id')
    def _compute_is_bora_electronics(self):
        """
        Check if the current company is 'Bora Electronics FZCO' or its child.
        """
        for order in self:
            user_company = order.company_id or self.env.user.company_id
            if user_company.name == "Bora Electronics FZCO" or (user_company.parent_id and user_company.parent_id.name == "Bora Electronics FZCO"):
                order.is_bora_electronics = True
            else:
                order.is_bora_electronics = False

    @api.onchange('is_exchange', 'manual_exchange_rate')
    def _onchange_manual_rate_recalculate_prices(self):
        """
        Recalculate order line prices when the manual rate or flag changes.
        This updates the price_unit field on the order lines for display.
        """


        for line in self.order_line:
            product_price_in_currency = line.product_id.lst_price

            if self.is_exchange and self.manual_exchange_rate > 0:
                line.price_unit = product_price_in_currency / self.manual_exchange_rate
            else:
                line.price_unit = product_price_in_currency

    def _get_manual_currency_rate(self):
        self.ensure_one()
        if self.is_exchange and self.manual_exchange_rate > 0:
            return self.manual_exchange_rate
        return super()._get_manual_currency_rate()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom_qty', 'price_unit', 'order_id.pricelist_id', 'order_id.is_exchange', 'order_id.manual_exchange_rate')
    def _compute_amount(self):
        # First, let Odoo's standard method compute the amount
        super()._compute_amount()

        for line in self:
            if line.order_id.is_exchange and line.order_id.manual_exchange_rate > 0:
                product_price_aed = line.product_id.lst_price
                line.price_unit = product_price_aed / line.order_id.manual_exchange_rate
