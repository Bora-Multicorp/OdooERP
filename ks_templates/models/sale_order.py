# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools import formatLang


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Additional sale order information fields
    ks_other_reference = fields.Char(string='Other Reference(s)')
    ks_despatched_through = fields.Char(string='Despatch through')
    ks_city_port_of_discharge = fields.Char(string='Destination')

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

    def get_company_bank_info(self):
        """Get company bank information: prefer sale order ks_bank_id when set, else company partner bank."""
        self.ensure_one()
        bank_info = {
            'ad_code': '',
            'swift_code': '',
            'branch': '',
            'bank_name': '',
            'acc_number': '',
            'ifsc_code': '',
            'city': '',
        }
        try:
            # Prefer sale order's selected bank (ks_bank_id) when set
            if getattr(self, 'ks_bank_id', None) and self.ks_bank_id:
                bank = self.ks_bank_id
                bank_info['bank_name'] = bank.name or ''
                bank_info['acc_number'] = getattr(bank, 'bic', None) or ''
                bank_info['swift_code'] = getattr(bank, 'swift_code', None) or getattr(bank, 'bic', None) or ''
                bank_info['ad_code'] = getattr(bank, 'bank_ad_code', None) or ''
                bank_info['ifsc_code'] = getattr(bank, 'ifsc_code', None) or ''
                bank_info['branch'] = getattr(bank, 'branch', None) or getattr(bank, 'branch_sol_id', None) or ''
                bank_info['city'] = getattr(bank, 'city', None) or ''
                return bank_info
        except Exception:
            pass

        try:
            company_bank = self.company_id.partner_id.bank_ids[:1] if self.company_id.partner_id.bank_ids else False
            if company_bank:
                # Get AD Code (custom field, may not exist)
                try:
                    if hasattr(company_bank, 'ad_code') and company_bank.ad_code:
                        bank_info['ad_code'] = company_bank.ad_code
                except:
                    pass
                
                # Get Branch (custom field, may not exist)
                try:
                    if hasattr(company_bank, 'branch') and company_bank.branch:
                        bank_info['branch'] = company_bank.branch
                except:
                    pass
                
                # Get standard fields
                if company_bank.bank_id:
                    bank_info['bank_name'] = company_bank.bank_id.name or ''
                    bank_info['swift_code'] = company_bank.bank_id.bic or ''
                    bank_info['city'] = company_bank.bank_id.city or ''
                    
                    # Get IFSC Code (custom field, may not exist)
                    try:
                        if hasattr(company_bank.bank_id, 'ifsc_code') and company_bank.bank_id.ifsc_code:
                            bank_info['ifsc_code'] = company_bank.bank_id.ifsc_code
                    except:
                        pass
                
                bank_info['acc_number'] = company_bank.acc_number or ''
        except Exception:
            pass
        
        return bank_info

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

