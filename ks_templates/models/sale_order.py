# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools import formatLang


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Additional sale order information fields
    ks_other_reference = fields.Char(string='Other Reference(s)')
    ks_despatched_through = fields.Char(string='Despatch through')
    ks_city_port_of_discharge = fields.Char(string='Destination')
    ks_delivery_note = fields.Char(string='Delivery Note')
    ks_remarks = fields.Text(string='Remarks')
    ks_buyer_order_no = fields.Char(string="Buyer's Order No.")
    ks_despatch_document_no = fields.Char(string='Dispatch Doc No.')
    ks_delivery_note_date = fields.Date(string='Delivery Note Date')
    ks_exchange_rate = fields.Float(string='Exchange Rate (to INR)', digits=(16, 4), default=0.0)
    ks_authorized_signature = fields.Binary(string='Authorized Signature', attachment=True, copy=False)

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
        """Convert amount to words for any currency using res.currency.amount_to_text."""
        self.ensure_one()
        if not currency or amount is None:
            return ''
        try:
            return currency.amount_to_text(amount) or ''
        except Exception:
            return ''

    def get_amount_in_words_inr(self, amount):
        """Convert amount to words in INR currency"""
        self.ensure_one()
        try:
            from num2words import num2words
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            lang = self.env['res.lang']._lang_get(self.env.user.lang or 'en_US')
            lang_code = lang.iso_code if lang and hasattr(lang, 'iso_code') else 'en'
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
        except (ImportError, Exception):
            integral, _sep, fractional = f"{amount:.2f}".partition('.')
            integer_value = int(integral)
            fractional_value = int(fractional or 0)
            if fractional_value == 0:
                return f"INR {integer_value} Only"
            else:
                return f"INR {integer_value} and {fractional_value} Paise Only"

    def get_company_pan(self):
        """Get company PAN number (Indian localization field)"""
        self.ensure_one()
        try:
            return self.company_id.l10n_in_pan or ''
        except Exception:
            return ''

    def get_company_iec(self):
        """Get company IEC number"""
        self.ensure_one()
        try:
            return self.company_id.iec_no or ''
        except Exception:
            return ''

    def get_inr_conversion_info(self):
        """Returns INR currency and rate. Uses sale order's rate field if set, else system rate."""
        self.ensure_one()
        inr = self.env['res.currency'].search([('name', '=', 'INR')], limit=1)
        if not inr:
            return {'currency': self.currency_id, 'rate': 1.0}
        if self.currency_id == inr:
            return {'currency': inr, 'rate': 1.0}
        existing_rate = getattr(self, 'rate', 0.0) or 0.0
        if existing_rate > 0:
            return {'currency': inr, 'rate': existing_rate}
        try:
            rate = self.env['res.currency']._get_conversion_rate(
                self.currency_id, inr, self.company_id, fields.Date.today()
            )
        except Exception:
            rate = 1.0
        return {'currency': inr, 'rate': rate}

    def get_inr_conversion_info(self):
        """Returns INR currency and rate. Uses sale order's rate field if set, else system rate."""
        self.ensure_one()
        inr = self.env['res.currency'].search([('name', '=', 'INR')], limit=1)
        if not inr:
            return {'currency': self.currency_id, 'rate': 1.0}
        if self.currency_id == inr:
            return {'currency': inr, 'rate': 1.0}
        existing_rate = getattr(self, 'rate', 0.0) or 0.0
        if existing_rate > 0:
            return {'currency': inr, 'rate': existing_rate}
        try:
            rate = self.env['res.currency']._get_conversion_rate(
                self.currency_id, inr, self.company_id, fields.Date.today()
            )
        except Exception:
            rate = 1.0
        return {'currency': inr, 'rate': rate}

    def get_line_hsn_code(self, line):
        """Get HSN/SAC code from product template"""
        try:
            if line.product_id and line.product_id.product_tmpl_id:
                if hasattr(line.product_id.product_tmpl_id, 'l10n_in_hsn_code') and line.product_id.product_tmpl_id.l10n_in_hsn_code:
                    return line.product_id.product_tmpl_id.l10n_in_hsn_code
        except Exception:
            pass
        try:
            if hasattr(line, 'l10n_in_hsn_code') and line.l10n_in_hsn_code:
                return line.l10n_in_hsn_code
        except Exception:
            pass
        return ''

    def _get_tax_type(self, tax):
        """Return 'cgst', 'sgst', 'igst', or '' for a single tax."""
        try:
            tax_type = (tax.l10n_in_tax_type or '').lower()
        except Exception:
            tax_type = ''
        if not tax_type:
            n = (tax.name or '').lower()
            if 'cgst' in n:
                tax_type = 'cgst'
            elif 'sgst' in n or 'utgst' in n:
                tax_type = 'sgst'
            elif 'igst' in n:
                tax_type = 'igst'
        return tax_type

    def _resolve_tax_rates(self, taxes):
        """Return list of (tax_type, rate) tuples, respecting group tax parent type."""
        result = []
        for tax in taxes:
            if tax.amount_type == 'group' and tax.children_tax_ids:
                parent_type = self._get_tax_type(tax)
                if parent_type in ('cgst', 'sgst', 'igst'):
                    # Parent type known: sum all children rates under parent type
                    total_rate = sum(c.amount for c in tax.children_tax_ids)
                    result.append((parent_type, total_rate))
                else:
                    # Parent type unknown: process each child individually
                    for child in tax.children_tax_ids:
                        child_type = self._get_tax_type(child)
                        if child_type:
                            result.append((child_type, child.amount))
            else:
                tax_type = self._get_tax_type(tax)
                if tax_type:
                    result.append((tax_type, tax.amount))
        return result

    def get_sale_gst_tax_info(self):
        """Returns GST tax breakdown for domestic India sales.
        Returns list of dicts with: taxable_amount, cgst_rate, cgst_amount, sgst_rate, sgst_amount, igst_rate, igst_amount
        Also returns totals: total_taxable, total_cgst, total_sgst, total_igst, subtotal
        """
        self.ensure_one()
        tax_groups = {}  # key: (cgst_rate, sgst_rate, igst_rate)

        for line in self.order_line.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
            cgst_rate = 0.0
            sgst_rate = 0.0
            igst_rate = 0.0
            for tax_type, rate in self._resolve_tax_rates(line.tax_id):
                if tax_type == 'cgst':
                    cgst_rate += rate
                elif tax_type == 'sgst':
                    sgst_rate += rate
                elif tax_type == 'igst':
                    igst_rate += rate

            key = (cgst_rate, sgst_rate, igst_rate)
            if key not in tax_groups:
                tax_groups[key] = {'taxable_amount': 0.0, 'cgst_rate': cgst_rate,
                                   'cgst_amount': 0.0, 'sgst_rate': sgst_rate,
                                   'sgst_amount': 0.0, 'igst_rate': igst_rate, 'igst_amount': 0.0}
            subtotal = line.price_subtotal
            tax_groups[key]['taxable_amount'] += subtotal
            tax_groups[key]['cgst_amount'] += subtotal * cgst_rate / 100.0
            tax_groups[key]['sgst_amount'] += subtotal * sgst_rate / 100.0
            tax_groups[key]['igst_amount'] += subtotal * igst_rate / 100.0

        groups = list(tax_groups.values())
        total_taxable = sum(g['taxable_amount'] for g in groups)
        total_cgst = sum(g['cgst_amount'] for g in groups)
        total_sgst = sum(g['sgst_amount'] for g in groups)
        total_igst = sum(g['igst_amount'] for g in groups)
        return {
            'groups': groups,
            'total_taxable': total_taxable,
            'total_cgst': total_cgst,
            'total_sgst': total_sgst,
            'total_igst': total_igst,
        }

    def get_line_tax_rates(self, line):
        """Return (cgst_rate, sgst_rate, igst_rate) for a sale order line."""
        cgst_rate = sgst_rate = igst_rate = 0.0
        for tax_type, rate in self._resolve_tax_rates(line.tax_id):
            if tax_type == 'cgst':
                cgst_rate += rate
            elif tax_type == 'sgst':
                sgst_rate += rate
            elif tax_type == 'igst':
                igst_rate += rate
        return cgst_rate, sgst_rate, igst_rate

    def format_number(self, value, digits=2):
        """Format number with specified decimal places"""
        self.ensure_one()
        return formatLang(self.env, value, digits=digits)

    def format_currency_amount(self, amount, currency=None):
        """Format amount with currency symbol using Odoo's built-in formatting"""
        self.ensure_one()
        if currency is None:
            currency = self.currency_id
        if currency:
            return currency.format(amount)
        return formatLang(self.env, amount, digits=2)

    def format_currency_with_symbol(self, amount, currency=None):
        """Format amount with currency symbol using currency.format() for proper encoding"""
        self.ensure_one()
        if currency is None:
            currency = self.currency_id
        if currency:
            # Use currency.format() which handles encoding properly
            try:
                return currency.format(amount)
            except Exception:
                # Fallback: format manually
                formatted_amount = formatLang(self.env, amount, digits=currency.decimal_places)
                symbol = (currency.symbol or '').encode('utf-8').decode('utf-8') if currency.symbol else ''
                if symbol:
                    if currency.position == 'after':
                        return f"{formatted_amount} {symbol}"
                    else:
                        return f"{symbol} {formatted_amount}"
                return formatted_amount
        # Fallback without currency
        return formatLang(self.env, amount, digits=2)

    def get_printable_order_lines(self):
        """Return order lines for printing, excluding all advance/downpayment lines."""
        self.ensure_one()
        # Collect downpayment product IDs from multiple sources
        downpayment_product_ids = set()
        try:
            # Odoo 18: stored on res.company
            dp_product = self.company_id.sale_down_payment_product_id
            if dp_product:
                downpayment_product_ids.add(dp_product.id)
        except Exception:
            pass
        try:
            # Fallback: ir.config_parameter
            dp_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
            if dp_id:
                downpayment_product_ids.add(int(dp_id))
        except Exception:
            pass

        def is_printable(line):
            if line.display_type in ('line_section', 'line_note'):
                return False
            if line.is_downpayment:
                return False
            if line.product_id and line.product_id.id in downpayment_product_ids:
                return False
            if line.product_id and (line.product_id.name or '').strip().upper() == 'ADVANCE PAYMENT':
                return False
            return True

        return self.order_line.filtered(is_printable)

    def get_company_bank_info(self):
        """Get bank info only from ks_bank_id. Returns empty if not set."""
        self.ensure_one()
        empty = {'ad_code': '', 'swift_code': '', 'branch': '', 'bank_name': '', 'acc_number': '', 'ifsc_code': '', 'city': ''}
        try:
            if getattr(self, 'ks_bank_id', None) and self.ks_bank_id:
                bank = self.ks_bank_id
                return {
                    'bank_name': bank.name or '',
                    'acc_number': getattr(bank, 'bic', None) or '',
                    'swift_code': getattr(bank, 'swift_code', None) or getattr(bank, 'bic', None) or '',
                    'ad_code': getattr(bank, 'bank_ad_code', None) or '',
                    'ifsc_code': getattr(bank, 'ifsc_code', None) or '',
                    'branch': getattr(bank, 'branch', None) or getattr(bank, 'branch_sol_id', None) or '',
                    'city': getattr(bank, 'city', None) or '',
                }
        except Exception:
            pass
        return empty

    def get_company_iban(self):
        """Get company IBAN safely"""
        self.ensure_one()
        try:
            company_bank = self.company_id.partner_id.bank_ids[:1] if self.company_id.partner_id.bank_ids else False
            if company_bank:
                # Try sanitized_acc_number first (for IBAN)
                if hasattr(company_bank, 'sanitized_acc_number') and company_bank.sanitized_acc_number:
                    return company_bank.sanitized_acc_number
                # Fallback to acc_number
                if hasattr(company_bank, 'acc_number') and company_bank.acc_number:
                    return company_bank.acc_number
        except Exception:
            pass
        return ''

