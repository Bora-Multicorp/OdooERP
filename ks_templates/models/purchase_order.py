# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools import formatLang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

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
        for line in self.order_line.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
            if line.discount:
                # Calculate discount amount: (price_unit * quantity * discount / 100)
                discount_amount = (line.price_unit * line.product_qty * line.discount) / 100.0
                total_discount += discount_amount
        return abs(total_discount)

    def get_cgst_sgst_info(self):
        """Get CGST and SGST information - split total tax equally (50% each)"""
        self.ensure_one()
        # Get total tax amount
        total_tax = self.amount_tax
        
        # Split equally (50% each)
        cgst_amount = total_tax / 2.0
        sgst_amount = total_tax / 2.0
        
        # Get tax rate from CGST/SGST taxes if available
        cgst_rate = 0.0
        sgst_rate = 0.0
        
        # Find CGST and SGST taxes from order lines
        for line in self.order_line.filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.taxes_id):
            for tax in line.taxes_id:
                if hasattr(tax, 'l10n_in_tax_type'):
                    if tax.l10n_in_tax_type == 'cgst':
                        cgst_rate = tax.amount
                    elif tax.l10n_in_tax_type == 'sgst':
                        sgst_rate = tax.amount
        
        # If rates not found, calculate from total tax and untaxed amount
        if cgst_rate == 0.0 and sgst_rate == 0.0 and self.amount_untaxed > 0:
            # Estimate rate from total tax
            estimated_rate = (total_tax / self.amount_untaxed) * 100.0
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
        tds_name = ''
        tds_amount = 0.0
        
        # Search for TDS taxes in order lines
        # TDS taxes typically have specific tags or names
        for line in self.order_line.filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.taxes_id):
            for tax in line.taxes_id:
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
            for invoice in self.invoice_ids.filtered(lambda inv: inv.state != 'cancel'):
                if hasattr(invoice, 'l10n_in_total_withholding_amount') and invoice.l10n_in_total_withholding_amount:
                    tds_amount = invoice.l10n_in_total_withholding_amount
                    # Try to get TDS name from withholding lines
                    if hasattr(invoice, 'l10n_in_withholding_line_ids') and invoice.l10n_in_withholding_line_ids:
                        tds_tax = invoice.l10n_in_withholding_line_ids.mapped('tax_ids').filtered(
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

    def get_line_hsn_code(self, line):
        """Get HSN/SAC code from purchase order line safely"""
        try:
            # Get HSN/SAC code from product template (primary source)
            if line.product_id and line.product_id.product_tmpl_id:
                if hasattr(line.product_id.product_tmpl_id, 'l10n_in_hsn_code') and line.product_id.product_tmpl_id.l10n_in_hsn_code:
                    return line.product_id.product_tmpl_id.l10n_in_hsn_code
        except:
            pass
        
        # Fallback: Try to get from product variant
        try:
            if line.product_id and hasattr(line.product_id, 'l10n_in_hsn_code') and line.product_id.l10n_in_hsn_code:
                return line.product_id.l10n_in_hsn_code
        except:
            pass
        
        return ''

