# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools import formatLang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ks_authorised_signatory = fields.Binary(string='Authorised Signatory', attachment=True, copy=False)
    ks_bank_id = fields.Many2one('res.bank', string='Bank Information')
    ks_remarks = fields.Text(string='Remarks')
    ks_round_off = fields.Float(
        string='Round Off',
        digits=(16, 2),
        compute='_compute_ks_round_off',
        inverse='_inverse_ks_round_off',
        store=True,
        help='Auto-calculated to round the total to the nearest integer. Can be manually overridden.',
    )
    ks_destination = fields.Char(string='Destination')
    ks_despatched_through = fields.Char(string='Despatched Through')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)

    def get_exchange_rate_info(self):
        """Returns exchange rate info for PDF display.
        large_rate = 1 foreign currency unit = X company currency units (e.g. 1 USD = 100 INR → 100)
        small_rate = 1 company currency unit = X foreign currency units (e.g. 1 INR = 0.01 USD → 0.01)

        Priority: manual rate (is_exchange=True) → system rate.
        """
        self.ensure_one()
        order = self.sudo()
        inv_currency = order.currency_id.sudo()
        comp_currency = order.company_id.sudo().currency_id.sudo()
        if not inv_currency or not comp_currency or inv_currency == comp_currency:
            return {'has_exchange': False, 'large_rate': 1.0, 'small_rate': 1.0}
        try:
            # Use manually entered rate when is_exchange is enabled
            if order.is_exchange and order.rate and order.rate > 0:
                large_rate = order.rate
                small_rate = 1.0 / large_rate
            else:
                # Fallback to system rate
                large_rate = self.env['res.currency'].sudo()._get_conversion_rate(
                    inv_currency, comp_currency, order.company_id.sudo(), fields.Date.today()
                )
                small_rate = 1.0 / large_rate if large_rate else 1.0
            return {'has_exchange': True, 'large_rate': large_rate, 'small_rate': small_rate}
        except Exception:
            return {'has_exchange': False, 'large_rate': 1.0, 'small_rate': 1.0}

    def get_company_pan(self):
        """Get company PAN number (Indian localization field)"""
        self.ensure_one()
        try:
            return self.sudo().company_id.sudo().l10n_in_pan or ''
        except Exception:
            return ''

    def get_company_iec(self):
        """Get company IEC number"""
        self.ensure_one()
        try:
            return self.sudo().company_id.sudo().iec_no or ''
        except Exception:
            return ''

    @api.depends('order_line.price_subtotal', 'order_line.price_tax')
    def _compute_ks_round_off(self):
        for order in self:
            lines = order.order_line.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
            raw_untaxed = sum(lines.mapped('price_subtotal'))
            raw_tax = sum(lines.mapped('price_tax'))
            raw_total = raw_untaxed + raw_tax
            order.ks_round_off = raw_total - round(raw_total)

    def _inverse_ks_round_off(self):
        # Allow manual override — stored value is kept as-is; amount_total recomputes via _amount_all
        pass

    @api.depends('order_line.price_subtotal', 'company_id', 'currency_id', 'ks_round_off')
    def _amount_all(self):
        super()._amount_all()
        for order in self:
            order.amount_total = order.amount_untaxed + order.amount_tax - order.ks_round_off

    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'ks_round_off')
    @api.depends_context('lang')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            if order.tax_totals and order.ks_round_off:
                order.tax_totals['total_amount_currency'] -= order.ks_round_off
                currency = order.currency_id or order.company_id.currency_id
                order.tax_totals['formatted_amount_total'] = formatLang(
                    self.env, order.tax_totals['total_amount_currency'], currency_obj=currency
                )

    def get_amount_in_words_aed(self, amount):
        """Convert amount to words in AED currency in the format: UAE Dirham [amount in words] and [fils] fils Only"""
        self.ensure_one()
        try:
            from num2words import num2words
            
            # Split integer and decimal parts
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            
            # Get language
            lang = self.env['res.lang']._lang_get(self.env.user.lang or 'en_US')
            lang_code = lang.iso_code if lang and hasattr(lang, 'iso_code') else 'en'
            
            # Convert to words
            if fractional_value == 0:
                words = num2words(integer_value, lang=lang_code).title()
                # Remove commas and replace "And" with "and" to match the format
                words = words.replace(",", "").replace(" And ", " and ").replace(" And", " and")
                return f"UAE Dirham {words} Only"
            else:
                words_integer = num2words(integer_value, lang=lang_code).title()
                words_fractional = num2words(fractional_value, lang=lang_code).title()
                # Remove commas and replace "And" with "and" to match the format
                words_integer = words_integer.replace(",", "").replace(" And ", " and ").replace(" And", " and")
                words_fractional = words_fractional.replace(",", "").replace(" And ", " and ").replace(" And", " and")
                # Format: UAE Dirham [amount] and [fils] fils Only (fils in lowercase, "and" lowercase)
                return f"UAE Dirham {words_integer} and {words_fractional} fils Only"
        except ImportError:
            # num2words not installed - try using currency's amount_to_text
            try:
                aed_currency = self.env['res.currency'].search([('name', '=', 'AED')], limit=1)
                if not aed_currency:
                    aed_currency = self.env['res.currency'].search([('symbol', '=', 'AED')], limit=1)
                
                if aed_currency:
                    result = aed_currency.amount_to_text(amount)
                    if result and result.strip():
                        # Format the result to match desired format
                        # Replace "Dirham" with "UAE Dirham" if not already present
                        if "UAE Dirham" not in result:
                            result = result.replace("Dirham", "UAE Dirham", 1)
                        # Make "fils" lowercase
                        result = result.replace("Fils", "fils")
                        return result
            except Exception:
                pass
            
            # Final fallback - return formatted number
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            if fractional_value == 0:
                return f"UAE Dirham {integer_value} Only"
            else:
                return f"UAE Dirham {integer_value} and {fractional_value} fils Only"
        except Exception:
            # Any other error - return formatted number
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            if fractional_value == 0:
                return f"UAE Dirham {integer_value} Only"
            else:
                return f"UAE Dirham {integer_value} and {fractional_value} fils Only"

    def get_amount_in_words_currency(self, amount, currency):
        """Convert amount to words for any currency using res.currency.amount_to_text.

        INR must use the Indian numbering system (lakh/crore) rather than the
        international system (million), so it is routed to get_amount_in_words_inr.
        """
        self.ensure_one()
        if not currency or amount is None:
            return ''
        if currency.name == 'INR':
            return self.get_amount_in_words_inr(amount)
        try:
            return currency.amount_to_text(amount) or ''
        except Exception:
            return ''

    def get_amount_in_words_inr(self, amount):
        """Convert amount to words in INR currency using the Indian numbering
        system (lakh/crore), independent of the user's UI language."""
        self.ensure_one()
        try:
            from num2words import num2words

            # Split integer and decimal parts
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)

            # Indian currency always uses Indian numbering (lakh/crore), regardless of UI language
            lang_code = 'en_IN'

            # Convert to words
            if fractional_value == 0:
                words = num2words(integer_value, lang=lang_code).title()
                words = words.replace(",", "").replace(" And ", " and ").replace(" And", " and")
                return f"INR {words} Only"
            else:
                words_integer = num2words(integer_value, lang=lang_code).title()
                words_fractional = num2words(fractional_value, lang=lang_code).title()
                words_integer = words_integer.replace(",", "").replace(" And ", " and ").replace(" And", " and")
                words_fractional = words_fractional.replace(",", "").replace(" And ", " and ").replace(" And", " and")
                return f"INR {words_integer} and {words_fractional} Paise Only"
        except ImportError:
            # Fallback
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            if fractional_value == 0:
                return f"INR {integer_value} Only"
            else:
                return f"INR {integer_value} and {fractional_value} Paise Only"
        except Exception:
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            if fractional_value == 0:
                return f"INR {integer_value} Only"
            else:
                return f"INR {integer_value} and {fractional_value} Paise Only"

    def format_number(self, value, digits=2):
        """Format number with specified decimal places"""
        self.ensure_one()
        return formatLang(self.env, value, digits=digits)

    def format_currency_amount(self, amount, currency=None):
        """Format amount with currency symbol"""
        self.ensure_one()
        if currency is None:
            currency = self.currency_id
        return currency.format(amount) if currency else formatLang(self.env, amount, digits=2)

    def get_discount_amount(self):
        """Calculate total discount amount before GST/IGST"""
        self.ensure_one()
        total_discount = 0.0
        for line in self.sudo().order_line.sudo().filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
            if line.discount:
                # Calculate discount amount: (price_unit * quantity * discount / 100)
                discount_amount = (line.price_unit * line.product_qty * line.discount) / 100.0
                total_discount += discount_amount
        return abs(total_discount)

    def get_cgst_sgst_info(self):
        """Get CGST and SGST information - split total tax equally (50% each)"""
        self.ensure_one()
        order = self.sudo()
        # Get total tax amount
        total_tax = order.amount_tax
        
        # Split equally (50% each)
        cgst_amount = total_tax / 2.0
        sgst_amount = total_tax / 2.0
        
        # Get tax rate from CGST/SGST taxes if available
        cgst_rate = 0.0
        sgst_rate = 0.0
        
        # Find CGST and SGST taxes from order lines
        for line in order.order_line.sudo().filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.taxes_id):
            for tax in line.taxes_id.sudo():
                if hasattr(tax, 'l10n_in_tax_type'):
                    if tax.l10n_in_tax_type == 'cgst':
                        cgst_rate = tax.amount
                    elif tax.l10n_in_tax_type == 'sgst':
                        sgst_rate = tax.amount
        
        # If rates not found, calculate from total tax and untaxed amount
        if cgst_rate == 0.0 and sgst_rate == 0.0 and order.amount_untaxed > 0:
            # Estimate rate from total tax
            estimated_rate = (total_tax / order.amount_untaxed) * 100.0
            cgst_rate = estimated_rate / 2.0
            sgst_rate = estimated_rate / 2.0
        
        return {
            'cgst_rate': cgst_rate,
            'cgst_amount': cgst_amount,
            'sgst_rate': sgst_rate,
            'sgst_amount': sgst_amount,
        }

    def get_tds_info(self):
        """Get TDS (Tax Deducted at Source) information"""
        self.ensure_one()
        order = self.sudo()
        tds_name = ''
        tds_amount = 0.0
        
        # Search for TDS taxes in order lines
        # TDS taxes typically have specific tags or names
        for line in order.order_line.sudo().filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.taxes_id):
            for tax in line.taxes_id.sudo():
                # Check if tax is a withholding/TDS tax
                # Look for TDS in tax name or check for withholding tags
                tax_name_lower = (tax.name or '').lower()
                if 'tds' in tax_name_lower or 'withhold' in tax_name_lower or '194' in tax_name_lower:
                    # Get TDS name (remove section number if present, use full name)
                    tds_name = tax.name or 'TDS on Purchase of Goods'
                    # Calculate TDS amount from this line
                    # TDS is typically calculated on the line amount
                    line_tds_amount = (line.price_subtotal * tax.amount) / 100.0
                    tds_amount += line_tds_amount
        
        # If TDS not found in taxes, check for withholding moves (if invoice is created)
        if tds_amount == 0.0:
            # Check if there are any invoice moves with TDS
            for invoice in order.invoice_ids.sudo().filtered(lambda inv: inv.state != 'cancel'):
                if hasattr(invoice, 'l10n_in_total_withholding_amount') and invoice.l10n_in_total_withholding_amount:
                    tds_amount = invoice.l10n_in_total_withholding_amount
                    # Try to get TDS name from withholding lines
                    if hasattr(invoice, 'l10n_in_withholding_line_ids') and invoice.l10n_in_withholding_line_ids:
                        tds_tax = invoice.l10n_in_withholding_line_ids.sudo().mapped('tax_ids').sudo().filtered(
                            lambda t: 'tds' in (t.name or '').lower() or 'withhold' in (t.name or '').lower() or '194' in (t.name or '').lower()
                        )
                        if tds_tax:
                            tds_name = tds_tax[0].name or 'TDS on Purchase of Goods'
                    else:
                        tds_name = 'TDS on Purchase of Goods'
                    break
        
        # If still no TDS found, return default
        if not tds_name:
            tds_name = 'TDS on Purchase of Goods'
        
        return {
            'tds_name': tds_name,
            'tds_amount': abs(tds_amount),
        }

    def get_purchase_gst_summary(self):
        """Returns list of {'name': ..., 'amount': X}.
        CGST+SGST at same rate are combined: 'Input SGST/UTGST @2.5% + Input CGST @2.5%'
        """
        self.ensure_one()
        order = self.sudo()

        def get_tax_type(tax):
            if hasattr(tax, 'l10n_in_tax_type') and tax.l10n_in_tax_type:
                return tax.l10n_in_tax_type
            name = (tax.name or '').lower()
            if 'igst' in name:
                return 'igst'
            elif 'cgst' in name:
                return 'cgst'
            elif 'sgst' in name or 'utgst' in name:
                return 'sgst'
            return None

        def fmt_rate(r):
            return f"{r:.1f}".rstrip('0').rstrip('.') if r % 1 else f"{r:.0f}"

        raw = {}  # key: (type, rate) -> amount

        def add(tax_type, rate, amount):
            key = (tax_type, rate)
            raw[key] = raw.get(key, 0.0) + amount

        for line in order.order_line.sudo().filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
            for tax in line.taxes_id.sudo():
                if tax.amount_type == 'group':
                    parent_type = get_tax_type(tax)
                    if parent_type:
                        total_rate = sum(c.amount for c in tax.children_tax_ids.sudo())
                        add(parent_type, total_rate, line.price_subtotal * total_rate / 100.0)
                    else:
                        for child in tax.children_tax_ids.sudo():
                            child_type = get_tax_type(child)
                            if child_type:
                                add(child_type, child.amount, line.price_subtotal * child.amount / 100.0)
                else:
                    tax_type = get_tax_type(tax)
                    if tax_type:
                        add(tax_type, tax.amount, line.price_subtotal * tax.amount / 100.0)

        result = []
        for (t, rate), amt in sorted(raw.items(), key=lambda x: (x[0][0], x[0][1])):
            if t == 'sgst':
                result.append({'name': f"Input SGST/UTGST @{fmt_rate(rate)}%", 'amount': amt})
            elif t == 'cgst':
                result.append({'name': f"Input CGST @{fmt_rate(rate)}%", 'amount': amt})
            elif t == 'igst':
                result.append({'name': f"Input IGST @{fmt_rate(rate)}%", 'amount': amt})
        return result

    def get_purchase_line_tax_info(self, line):
        """Returns list of tax display strings for a purchase order line.
        e.g. ['Input IGST @28%'] or ['Input CGST @14%', 'Input SGST @14%']
        """
        self.ensure_one()
        result = []
        line = line.sudo()

        def get_tax_type(tax):
            if hasattr(tax, 'l10n_in_tax_type') and tax.l10n_in_tax_type:
                return tax.l10n_in_tax_type
            name = (tax.name or '').lower()
            if 'igst' in name:
                return 'igst'
            elif 'cgst' in name:
                return 'cgst'
            elif 'sgst' in name or 'utgst' in name:
                return 'sgst'
            return None

        type_labels = {'igst': 'IGST', 'cgst': 'CGST', 'sgst': 'SGST/UTGST'}

        for tax in line.taxes_id.sudo():
            if tax.amount_type == 'group':
                parent_type = get_tax_type(tax)
                if parent_type:
                    total_rate = sum(c.amount for c in tax.children_tax_ids.sudo())
                    label = type_labels.get(parent_type, parent_type.upper())
                    result.append(f"Input {label} @{total_rate:.0f}%")
                else:
                    for child in tax.children_tax_ids.sudo():
                        child_type = get_tax_type(child)
                        if child_type:
                            label = type_labels.get(child_type, child_type.upper())
                            result.append(f"Input {label} @{child.amount:.0f}%")
            else:
                tax_type = get_tax_type(tax)
                if tax_type:
                    label = type_labels.get(tax_type, tax_type.upper())
                    result.append(f"Input {label} @{tax.amount:.0f}%")

        return result

    def get_printable_order_lines(self):
        """Return purchase order lines for printing, excluding advance/downpayment lines."""
        self.ensure_one()

        def is_printable(line):
            line = line.sudo()
            if line.display_type in ('line_section', 'line_note'):
                return False
            if line.product_id and line.product_id.sudo().product_tmpl_id.sudo().is_advance_payment_product:
                return False
            return True

        return self.sudo().order_line.sudo().filtered(is_printable)

    def get_line_hsn_code(self, line):
        """Get HSN/SAC code from purchase order line safely"""
        line = line.sudo()
        try:
            # Get HSN/SAC code from product template (primary source)
            if line.product_id and line.product_id.sudo().product_tmpl_id.sudo():
                tmpl = line.product_id.sudo().product_tmpl_id.sudo()
                if hasattr(tmpl, 'l10n_in_hsn_code') and tmpl.l10n_in_hsn_code:
                    return tmpl.l10n_in_hsn_code
        except Exception:
            pass
        
        # Fallback: Try to get from product variant
        try:
            prod = line.product_id.sudo()
            if prod and hasattr(prod, 'l10n_in_hsn_code') and prod.l10n_in_hsn_code:
                return prod.l10n_in_hsn_code
        except Exception:
            pass
        
        return ''


