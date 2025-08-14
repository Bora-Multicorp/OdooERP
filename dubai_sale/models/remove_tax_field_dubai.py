
from odoo import fields, models, api

class RemoveTaxFieldForDubai(models.Model):
    _inherit = "sale.order"

    hide_tax_column = fields.Boolean(
        compute='_compute_hide_tax_column_if_both_dubai'
    )

    @api.depends('partner_id.country_id.code')
    def _compute_hide_tax_column_if_both_dubai(self):
        for order in self:
            customer_country_is_dubai = False
            seller_country_is_dubai = False

            # Safely check customer's country
            if order.partner_id and order.partner_id.country_id:
                customer_country_is_dubai = (order.partner_id.country_id.code == 'AE')

            # Safely check seller's (company's) country
            if order.company_id and order.company_id.country_id:
                seller_country_is_dubai = (order.company_id.country_id.code == 'AE')
            
            # Assign the computed value for the current order
            if customer_country_is_dubai and seller_country_is_dubai:
                order.hide_tax_column = True
            else:
                order.hide_tax_column = False