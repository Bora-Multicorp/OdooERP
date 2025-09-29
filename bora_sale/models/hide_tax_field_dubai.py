from odoo import fields, models, api, _
from collections import defaultdict
from odoo.tools.float_utils import float_repr


# hide tax fields from purchase order form
class HideTaxFieldFromPurchaseOrderForm(models.Model):
    _inherit = "purchase.order"

    hide_tax_column = fields.Boolean(
        compute='_compute_hide_tax_column_if_both_dubai'
    )

    @api.depends('partner_id.country_id.code','order_line.product_id.product_tmpl_id')
    def _compute_hide_tax_column_if_both_dubai(self):
        for order in self:
            order.hide_tax_column = False

            # 1. check if there is any product in orderline with service exist
            is_taxable_item_exist_in_orderline = False
            for line in order.order_line:
                if line.product_id:
                    if line.product_id.product_tmpl_id.type == 'service' or line.product_id.product_tmpl_id.type == 'combo':
                        is_taxable_item_exist_in_orderline = True
                        break
            if is_taxable_item_exist_in_orderline == True:
                continue


            # 2. if all product type are goods, then search for tax free companies
            is_ayaan_impex = False
            is_bora_electronics_fzco = False

            company_registry = order.company_id.company_registry

            if company_registry:
                is_ayaan_impex = (company_registry == '1804237.01')
                is_bora_electronics_fzco = (company_registry == '3892')

            if is_ayaan_impex or is_bora_electronics_fzco:
                order.hide_tax_column = True
                continue

            # 3. Check if current copmany is India and customer is not from india
            selling_company_country_code = order.company_id.country_id.code
            customer_country_code = order.partner_id.country_id.code
            
            if selling_company_country_code == 'IN' and customer_country_code != 'IN':
                order.hide_tax_column = True
                continue



# make tax field readonly for purchase order line
class ReadonlyTaxFieldFromPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    read_only_tax_field = fields.Boolean(
        compute='_compute_readonly_tax_column_if_both_dubai'
    )


    @api.depends('product_id')
    def _compute_readonly_tax_column_if_both_dubai(self):

        # 1. check if product type is goods
        self.read_only_tax_field = False
        is_product_type_goods = False
        for line in self:
            if line.product_id:
                if line.product_id.product_tmpl_id.type == 'consu':
                    is_product_type_goods = True
            company_registry = line.order_id.company_id.company_registry

            # 1. if both companies are dubai based and product type is goods then make tax field readonly
            if (company_registry == '1804237.01' or company_registry == '3892') and is_product_type_goods:
                line.read_only_tax_field = True
                continue

            # 2. if current copmany is india and customeer copmany is other then india
            selling_company_country_code = line.order_id.company_id.country_id.code
            customer_country_code = line.order_id.partner_id.country_id.code
            if selling_company_country_code == 'IN' and customer_country_code != 'IN' and is_product_type_goods:
                line.read_only_tax_field = True
                continue


# make tax field readonly for sale order line
class ReadonlyTaxFieldFromSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    read_only_tax_field = fields.Boolean(
        compute='_compute_readonly_tax_column_if_both_dubai'
    )


    @api.depends('product_id')
    def _compute_readonly_tax_column_if_both_dubai(self):

        # 1. check if product type is goods
        self.read_only_tax_field = False
        is_product_type_goods = False
        for line in self:
            if line.product_id:
                if line.product_id.product_tmpl_id.type == 'consu':
                    is_product_type_goods = True
            company_registry = line.order_id.company_id.company_registry

            # 1. if both companies are dubai based and product type is goods then make tax field readonly
            if (company_registry == '1804237.01' or company_registry == '3892') and is_product_type_goods:
                line.read_only_tax_field = True


            # 2. if current copmany is india and customeer copmany is other then india
            selling_company_country_code = line.order_id.company_id.country_id.code
            customer_country_code = line.order_id.partner_id.country_id.code
            if selling_company_country_code == 'IN' and customer_country_code != 'IN' and is_product_type_goods:
                line.read_only_tax_field = True
                continue



# hide tax fields from sale order form
class HideTaxFieldFormSaleOrder(models.Model):
    _inherit = "sale.order"

    hide_tax_column = fields.Boolean(
        compute='_compute_hide_tax_column_if_both_dubai'
    )

    @api.depends('partner_id.country_id.code','order_line.product_id.product_tmpl_id')
    def _compute_hide_tax_column_if_both_dubai(self):

        for order in self:
            order.hide_tax_column = False

            # 1. check if there is any product in orderline with service exist
            is_taxable_item_exist_in_orderline = False
            for line in order.order_line:
                if line.product_id:
                    if line.product_id.product_tmpl_id.type == 'service' or line.product_id.product_tmpl_id.type == 'combo':
                        is_taxable_item_exist_in_orderline = True
                        break
            if is_taxable_item_exist_in_orderline == True:
                continue


            # 2. if all product type are goods, then search for tax free companies
            is_ayaan_impex = False
            is_bora_electronics_fzco = False

            company_registry = order.company_id.company_registry

            if company_registry:
                is_ayaan_impex = (company_registry == '1804237.01')
                is_bora_electronics_fzco = (company_registry == '3892')

            if is_ayaan_impex or is_bora_electronics_fzco:
                order.hide_tax_column = True
                continue


            # 3. Check if current copmany is India and customer is not from india
            selling_company_country_code = order.company_id.country_id.code
            customer_country_code = order.partner_id.country_id.code
            
            if selling_company_country_code == 'IN' and customer_country_code != 'IN':
                order.hide_tax_column = True
                continue


    
# hide tax fields from product template form 
class HideTacFieldFromProductTemplate(models.Model):
    _inherit = "product.template"

    hide_tax_fields = fields.Boolean(
        compute='_show_tax_field_if_any_company_is_not_dubai'
    )

    @api.depends('company_ids', 'type')
    def _show_tax_field_if_any_company_is_not_dubai(self):
        for product in self:
            product.hide_tax_fields = True

            for company in product.company_ids:
                company_registry = company.company_registry

                # if there is any company other then dubai company found
                if company_registry != "1804237.01" and company_registry != "3892":
                    product.hide_tax_fields = False
                    break

            if product.type == 'service' or product.type == 'combo':
                product.hide_tax_fields = False



# hide tax fields from sale order total section
class HideTaxFieldFromSaleOrderTotalSection(models.Model):
    _inherit = "account.tax"

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):

        partner_id = next((line.get('partner_id') for line in base_lines if line.get('partner_id')), False)
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id.id)
        
        # Call super to get the original tax totals summary
        tax_totals_summary = super(HideTaxFieldFromSaleOrderTotalSection, self)._get_tax_totals_summary(
            base_lines, currency, company, cash_rounding=cash_rounding
        )

        # ------------------------------------------------------------------------------------------
        # -------------------------  CUSTOM WORK FOR SHOW/HIDE TAX FIELDS --------------------------
        # ------------------------------------------------------------------------------------------

        india_code = 'IN'
        
        # 1. check if there is any product in orderline with service exist
        is_taxable_item_exist_in_orderline = False
        for base_line in base_lines:
            product = base_line.get('product_id')
            if product:
                if product.product_tmpl_id.type in ('service', 'combo'):
                    is_taxable_item_exist_in_orderline = True
                    break # Optimization: stop checking once a service/combo is found


        # 2. if there is any product type service then no need to hide tax fields for any country
        if not is_taxable_item_exist_in_orderline:
            
            # 2.1 check for tax free companies (UAE case)
            is_ayaan_impex = (company.company_registry == '1804237.01')
            is_bora_electronics_fzco = (company.company_registry == '3892') 

            if is_ayaan_impex or is_bora_electronics_fzco:  
                # If any tax-free company, hide tax details
                tax_totals_summary['subtotals'] = []
            
            # 2.2 if selling company is India and customer's country is other then India then
            elif company.country_id.code == india_code and partner.country_id.code != india_code:
                # If India company exporting, hide tax details (Zero-rated export)
                tax_totals_summary['subtotals'] = []


        return tax_totals_summary


    # @api.model
    # def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
    #     """ Compute the tax totals details for the business documents.

    #     Don't forget to call '_add_tax_details_in_base_lines' and '_round_base_lines_tax_details' before calling this method.

    #     :param base_lines:          A list of base lines generated using the '_prepare_base_line_for_taxes_computation' method.
    #     :param currency:            The tax totals is only available when all base lines share the same currency.
    #                                 Since the tax totals can be computed when there is no base line at all, a currency must be
    #                                 specified explicitely for that case.
    #     :param company:             The company owning the base lines.
    #     :param cash_rounding:       A optional account.cash.rounding object. When specified, the delta base amount added
    #                                 to perform the cash rounding is specified in the results.
    #     :return: A dictionary containing:
    #         currency_id:                            The id of the currency used.
    #         currency_pd:                            The currency rounding (to be used js-side by the widget).
    #         company_currency_id:                    The id of the company's currency used.
    #         company_currency_pd:                    The company's currency rounding (to be used js-side by the widget).
    #         has_tax_groups:                         Flag indicating if there is at least one involved tax group.
    #         same_tax_base:                          Flag indicating the base amount of all tax groups are the same and it's
    #                                                 redundant to display them.
    #         base_amount_currency:                   The untaxed amount expressed in foreign currency.
    #         base_amount:                            The untaxed amount expressed in local currency.
    #         tax_amount_currency:                    The tax amount expressed in foreign currency.
    #         tax_amount:                             The tax amount expressed in local currency.
    #         total_amount_currency:                  The total amount expressed in foreign currency.
    #         total_amount:                           The total amount expressed in local currency.
    #         cash_rounding_base_amount_currency:     The delta added by 'cash_rounding' expressed in foreign currency.
    #                                                 If there is no amount added, the key is not in the result.
    #         cash_rounding_base_amount:              The delta added by 'cash_rounding' expressed in local currency.
    #                                                 If there is no amount added, the key is not in the result.
    #         subtotals:                              A list of subtotal (like "Untaxed Amount"), each one being a python dictionary
    #                                                 containing:
    #             base_amount_currency:                   The base amount expressed in foreign currency.
    #             base_amount:                            The base amount expressed in local currency.
    #             tax_amount_currency:                    The tax amount expressed in foreign currency.
    #             tax_amount:                             The tax amount expressed in local currency.
    #             tax_groups:                             A list of python dictionary, one for each tax group, containing:
    #                 id:                                     The id of the account.tax.group.
    #                 group_name:                             The name of the group.
    #                 group_label:                            The short label of the group to be displayed on POS receipt.
    #                 involved_tax_ids:                       A list of the tax ids aggregated in this tax group.
    #                 base_amount_currency:                   The base amount expressed in foreign currency.
    #                 base_amount:                            The base amount expressed in local currency.
    #                 tax_amount_currency:                    The tax amount expressed in foreign currency.
    #                 tax_amount:                             The tax amount expressed in local currency.
    #                 display_base_amount_currency:           The base amount to display expressed in foreign currency.
    #                                                         The flat base amount and the amount to be displayed are sometimes different
    #                                                         (e.g. division/fixed taxes).
    #                 display_base_amount:                    The base amount to display expressed in local currency.
    #                                                         The flat base amount and the amount to be displayed are sometimes different
    #                                                         (e.g. division/fixed taxes).
    #     """
    #     tax_totals_summary = {
    #         'currency_id': currency.id,
    #         'currency_pd': currency.rounding,
    #         'company_currency_id': company.currency_id.id,
    #         'company_currency_pd': company.currency_id.rounding,
    #         'has_tax_groups': False,
    #         'subtotals': [],
    #         'base_amount_currency': 0.0,
    #         'base_amount': 0.0,
    #         'tax_amount_currency': 0.0,
    #         'tax_amount': 0.0,
    #     }

    #     # Global tax values.
    #     def global_grouping_function(base_line, tax_data):
    #         return True if tax_data else None

    #     base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, global_grouping_function)
    #     values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
    #     for grouping_key, values in values_per_grouping_key.items():
    #         if grouping_key:
    #             tax_totals_summary['has_tax_groups'] = True
    #         tax_totals_summary['base_amount_currency'] += values['total_excluded_currency']
    #         tax_totals_summary['base_amount'] += values['total_excluded']
    #         tax_totals_summary['tax_amount_currency'] += values['tax_amount_currency']
    #         tax_totals_summary['tax_amount'] += values['tax_amount']

    #     # Tax groups.
    #     untaxed_amount_subtotal_label = _("Untaxed Amount")
    #     subtotals = defaultdict(lambda: {
    #         'tax_groups': [],
    #         'tax_amount_currency': 0.0,
    #         'tax_amount': 0.0,
    #         'base_amount_currency': 0.0,
    #         'base_amount': 0.0,
    #     })

    #     def tax_group_grouping_function(base_line, tax_data):
    #         return tax_data['tax'].tax_group_id if tax_data else None

    #     base_lines_aggregated_values = self._aggregate_base_lines_tax_details(base_lines, tax_group_grouping_function)
    #     values_per_grouping_key = self._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
    #     sorted_total_per_tax_group = sorted(
    #         [values for grouping_key, values in values_per_grouping_key.items() if grouping_key],
    #         key=lambda values: (values['grouping_key'].sequence, values['grouping_key'].id),
    #     )

    #     encountered_base_amounts = set()
    #     subtotals_order = {}
    #     for order, values in enumerate(sorted_total_per_tax_group):
    #         tax_group = values['grouping_key']

    #         # Get all involved taxes in the tax group.
    #         involved_taxes = self.env['account.tax']
    #         for base_line, taxes_data in values['base_line_x_taxes_data']:
    #             for tax_data in taxes_data:
    #                 involved_taxes |= tax_data['tax']

    #         # Compute the display base amounts.
    #         display_base_amount = values['base_amount']
    #         display_base_amount_currency = values['base_amount_currency']
    #         if set(involved_taxes.mapped('amount_type')) == {'fixed'}:
    #             display_base_amount = None
    #             display_base_amount_currency = None
    #         elif set(involved_taxes.mapped('amount_type')) == {'division'} and all(involved_taxes.mapped('price_include')):
    #             for base_line, _taxes_data in values['base_line_x_taxes_data']:
    #                 for tax_data in base_line['tax_details']['taxes_data']:
    #                     if tax_data['tax'].amount_type == 'division':
    #                         display_base_amount_currency += tax_data['tax_amount_currency']
    #                         display_base_amount += tax_data['tax_amount']

    #         if display_base_amount_currency is not None:
    #             encountered_base_amounts.add(float_repr(display_base_amount_currency, currency.decimal_places))

    #         # Order of the subtotals.
    #         preceding_subtotal = tax_group.preceding_subtotal or untaxed_amount_subtotal_label
    #         if preceding_subtotal not in subtotals_order:
    #             subtotals_order[preceding_subtotal] = order

    #         subtotals[preceding_subtotal]['tax_groups'].append({
    #             'id': tax_group.id,
    #             'involved_tax_ids': involved_taxes.ids,
    #             'tax_amount_currency': values['tax_amount_currency'],
    #             'tax_amount': values['tax_amount'],
    #             'base_amount_currency': values['base_amount_currency'],
    #             'base_amount': values['base_amount'],
    #             'display_base_amount_currency': display_base_amount_currency,
    #             'display_base_amount': display_base_amount,
    #             'group_name': tax_group.name,
    #             'group_label': tax_group.pos_receipt_label,
    #         })

    #     # Subtotals.
    #     if not subtotals:
    #         subtotals[untaxed_amount_subtotal_label]

    #     ordered_subtotals = sorted(subtotals.items(), key=lambda item: subtotals_order.get(item[0], 0))
    #     accumulated_tax_amount_currency = 0.0
    #     accumulated_tax_amount = 0.0
    #     for subtotal_label, subtotal in ordered_subtotals:
    #         subtotal['name'] = subtotal_label
    #         subtotal['base_amount_currency'] = tax_totals_summary['base_amount_currency'] + accumulated_tax_amount_currency
    #         subtotal['base_amount'] = tax_totals_summary['base_amount'] + accumulated_tax_amount
    #         for tax_group in subtotal['tax_groups']:
    #             subtotal['tax_amount_currency'] += tax_group['tax_amount_currency']
    #             subtotal['tax_amount'] += tax_group['tax_amount']
    #             accumulated_tax_amount_currency += tax_group['tax_amount_currency']
    #             accumulated_tax_amount += tax_group['tax_amount']
    #         tax_totals_summary['subtotals'].append(subtotal)

    #     # Cash rounding
    #     cash_rounding_lines = [base_line for base_line in base_lines if base_line['special_type'] == 'cash_rounding']
    #     if cash_rounding_lines:
    #         tax_totals_summary['cash_rounding_base_amount_currency'] = 0.0
    #         tax_totals_summary['cash_rounding_base_amount'] = 0.0
    #         for base_line in cash_rounding_lines:
    #             tax_details = base_line['tax_details']
    #             tax_totals_summary['cash_rounding_base_amount_currency'] += tax_details['total_excluded_currency']
    #             tax_totals_summary['cash_rounding_base_amount'] += tax_details['total_excluded']
    #     elif cash_rounding:
    #         strategy = cash_rounding.strategy
    #         cash_rounding_pd = cash_rounding.rounding
    #         cash_rounding_method = cash_rounding.rounding_method
    #         total_amount_currency = tax_totals_summary['base_amount_currency'] + tax_totals_summary['tax_amount_currency']
    #         total_amount = tax_totals_summary['base_amount'] + tax_totals_summary['tax_amount']
    #         expected_total_amount_currency = float_round(
    #             total_amount_currency,
    #             precision_rounding=cash_rounding_pd,
    #             rounding_method=cash_rounding_method,
    #         )
    #         cash_rounding_base_amount_currency = expected_total_amount_currency - total_amount_currency
    #         rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
    #         cash_rounding_base_amount = company.currency_id.round(cash_rounding_base_amount_currency / rate) if rate else 0.0
    #         if not currency.is_zero(cash_rounding_base_amount_currency):
    #             if strategy == 'add_invoice_line':
    #                 tax_totals_summary['cash_rounding_base_amount_currency'] = cash_rounding_base_amount_currency
    #                 tax_totals_summary['cash_rounding_base_amount'] = cash_rounding_base_amount
    #                 tax_totals_summary['base_amount_currency'] += cash_rounding_base_amount_currency
    #                 tax_totals_summary['base_amount'] += cash_rounding_base_amount
    #                 subtotals[untaxed_amount_subtotal_label]['base_amount_currency'] += cash_rounding_base_amount_currency
    #                 subtotals[untaxed_amount_subtotal_label]['base_amount'] += cash_rounding_base_amount
    #             elif strategy == 'biggest_tax':
    #                 all_subtotal_tax_group = [
    #                     (subtotal, tax_group)
    #                     for subtotal in tax_totals_summary['subtotals']
    #                     for tax_group in subtotal['tax_groups']
    #                 ]

    #                 if all_subtotal_tax_group:
    #                     max_subtotal, max_tax_group = max(
    #                         all_subtotal_tax_group,
    #                         key=lambda item: item[1]['tax_amount_currency'],
    #                     )
    #                     max_tax_group['tax_amount_currency'] += cash_rounding_base_amount_currency
    #                     max_tax_group['tax_amount'] += cash_rounding_base_amount
    #                     max_subtotal['tax_amount_currency'] += cash_rounding_base_amount_currency
    #                     max_subtotal['tax_amount'] += cash_rounding_base_amount
    #                     tax_totals_summary['tax_amount_currency'] += cash_rounding_base_amount_currency
    #                     tax_totals_summary['tax_amount'] += cash_rounding_base_amount
    #                 else:
    #                     # Failed to apply the cash rounding since there is no tax.
    #                     cash_rounding_base_amount_currency = 0.0
    #                     cash_rounding_base_amount = 0.0

    #     # Subtract the cash rounding from the untaxed amounts.
    #     cash_rounding_base_amount_currency = tax_totals_summary.get('cash_rounding_base_amount_currency', 0.0)
    #     cash_rounding_base_amount = tax_totals_summary.get('cash_rounding_base_amount', 0.0)
    #     tax_totals_summary['base_amount_currency'] -= cash_rounding_base_amount_currency
    #     tax_totals_summary['base_amount'] -= cash_rounding_base_amount
    #     for subtotal in tax_totals_summary['subtotals']:
    #         subtotal['base_amount_currency'] -= cash_rounding_base_amount_currency
    #         subtotal['base_amount'] -= cash_rounding_base_amount
    #     encountered_base_amounts.add(float_repr(tax_totals_summary['base_amount_currency'], currency.decimal_places))
    #     tax_totals_summary['same_tax_base'] = len(encountered_base_amounts) == 1

    #     # Total amount.
    #     tax_totals_summary['total_amount_currency'] = \
    #         tax_totals_summary['base_amount_currency'] + tax_totals_summary['tax_amount_currency'] + cash_rounding_base_amount_currency
    #     tax_totals_summary['total_amount'] = \
    #         tax_totals_summary['base_amount'] + tax_totals_summary['tax_amount'] + cash_rounding_base_amount
        

    #     # ------------------------------------------------------------------------------------------
    #     # -------------------------  CUSTOM WORK FOR SHOW/HIDE TAX FIELDS --------------------------
    #     # ------------------------------------------------------------------------------------------

    #     # Get customer so that we can check the country
    #     partner_id = next((line.get('partner_id') for line in base_lines if line.get('partner_id')), False)
    #     if partner_id:
    #         partner = self.env['res.partner'].browse(partner_id.id)

    #     # 1. check if there is any product in orderline with service exist
    #     is_taxable_item_exist_in_orderline = False
    #     for base_line in base_lines:
    #         product = base_line.get('product_id')
    #         if product:
    #             if product.product_tmpl_id.type == 'service' or product.product_tmpl_id.type == 'combo':
    #                 is_taxable_item_exist_in_orderline = True


    #     # 2. if there is any product type service then no need to hide tax fields for any country
    #     if is_taxable_item_exist_in_orderline == False:
    #         # hide tax details if both companies are dubai based
    #         is_ayaan_impex = (company.company_registry == '1804237.01')
    #         is_bora_electronics_fzco = (company.company_registry == '3892') 

    #         # 2.1 if any copmany is tax free then hide tax details
    #         if is_ayaan_impex or is_bora_electronics_fzco:
    #             tax_totals_summary['subtotals'] = []

    #         if partner.country_id.code:
    #             if company.country_id.code == 'IN' and partner.country_id.code != 'IN':
    #                 tax_totals_summary['subtotals'] = []

    #     return tax_totals_summary



# hide tax field from vendor bill and invoice from sale order
class HideTaxFieldFromVendorBill(models.Model):
    _inherit = "account.move"

    hide_tax_column = fields.Boolean(
        compute='_compute_hide_tax_column_if_both_dubai'
    )

    @api.depends('partner_id.country_id.code','invoice_line_ids.product_id.product_tmpl_id')
    def _compute_hide_tax_column_if_both_dubai(self):
        for move in self:
            move.hide_tax_column = False


            # 1. check if there is any product in orderline with service exist
            is_taxable_item_exist_in_orderline = False
            for line in move.invoice_line_ids:
                if line.product_id:
                    if line.product_id.product_tmpl_id.type == 'service' or line.product_id.product_tmpl_id.type == 'combo':
                        is_taxable_item_exist_in_orderline = True
                        break
            if is_taxable_item_exist_in_orderline == True:
                continue


            # 2. if all product type are goods, then search for tax free companies
            is_ayaan_impex = False
            is_bora_electronics_fzco = False

            company_registry = move.company_id.company_registry

            if company_registry:
                is_ayaan_impex = (company_registry == '1804237.01')
                is_bora_electronics_fzco = (company_registry == '3892')

            if is_ayaan_impex or is_bora_electronics_fzco:
                move.hide_tax_column = True
                continue

            # 3. Check if current copmany is India and customer is not from india
            selling_company_country_code = move.company_id.country_id.code
            customer_country_code = move.partner_id.country_id.code
            if selling_company_country_code == 'IN' and customer_country_code != 'IN':
                move.hide_tax_column = True
                continue


    def action_invoice_sent(self):
        print('--------------   ', self.read()[0])
