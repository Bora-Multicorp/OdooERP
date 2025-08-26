
from odoo import fields, models, api

class HideTaxFieldFormSaleOrder(models.Model):
    _inherit = "sale.order"

    hide_tax_column = fields.Boolean(
        compute='_compute_hide_tax_column_if_both_dubai'
    )

    @api.depends('partner_id.country_id.code')
    def _compute_hide_tax_column_if_both_dubai(self):
        for order in self:
            order.hide_tax_column = False

            company_registry = order.company_id.company_registry

            if company_registry:
                is_ayaan_impex = (company_registry == '1804237.01')
                is_bora_electronics_fzco = (company_registry == '3892')

            if is_ayaan_impex or is_bora_electronics_fzco:
                order.hide_tax_column = True
                continue



class HideTacFieldFromProductTemplate(models.Model):
    _inherit = "product.template"

    hide_tax_fields = fields.Boolean(
        compute='_show_tax_field_if_any_company_is_not_dubai'
    )

    @api.depends('company_ids')
    def _show_tax_field_if_any_company_is_not_dubai(self):
        print('_show_tax_field_if_any_company_is_not_dubai')
        for product in self:
            product.hide_tax_fields = True

            for company in product.company_ids:
                company_registry = company.company_registry
                print('-------------- company_registry =>', company_registry)

                # if there is any company other then dubai company found
                if company_registry != "1804237.01" and company_registry != "3892":
                    product.hide_tax_fields = False
                    break
            print('-------------- hide tax fields for product =>', product.hide_tax_fields)