# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Additional invoice information fields
    ks_delivery_note = fields.Char(string='Delivery Note')
    ks_supplier_reference = fields.Char(string="Supplier's Reference")
    ks_reference_no_date = fields.Char(string='Reference No. & Date')
    ks_despatch_document_no = fields.Char(string='Despatch Document No.')
    ks_delivery_note_date = fields.Date(string='Delivery Note Date')
    ks_despatched_through = fields.Char(string='Despatched Through')
    ks_vessel_flight_no = fields.Char(string='Vessel / Flight No.')
    ks_place_of_receipt_by_shipper = fields.Char(string='Place of Receipt by Shipper')
    ks_city_port_of_loading = fields.Char(string='City / Port of Loading')
    ks_city_port_of_discharge = fields.Char(string='City / Port of Discharge')
    # Bank details for invoice (copied from sale order ks_bank_id when invoice is created from SO)
    ks_bank_id = fields.Many2one(
        'res.bank',
        string='Bank Information',
        copy=False,
        help='Bank details for this Invoice. Filled from Sale Order when invoice is created from SO.',
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
                        if "UAE Dirham" not in result:
                            result = result.replace("Dirham", "UAE Dirham", 1)
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

    def _is_igst_tax(self, tax):
        """Check if tax is IGST type safely"""
        try:
            if hasattr(tax, 'l10n_in_tax_type') and tax.l10n_in_tax_type == 'igst':
                return True
        except:
            pass
        return False

    def get_igst_tax_info(self):
        """Get IGST tax information grouped by HSN code (or any tax if IGST not found)"""
        self.ensure_one()
        tax_info = {}

        # Build a map: invoice_line -> tax_amount from actual journal tax lines (posted invoices)
        # tax journal lines have display_type == 'tax' and are linked via tax_line_id
        # We match them back to invoice lines via tax_repartition_line_id -> invoice_line_ids
        line_tax_amounts = {}  # {invoice_line_id: total_tax_amount}

        tax_journal_lines = self.line_ids.filtered(
            lambda l: l.display_type == 'tax' and l.tax_line_id
        )
        for tl in tax_journal_lines:
            # amount_currency holds value in invoice currency; balance is in company currency
            tax_amt = abs(tl.amount_currency) if tl.amount_currency else abs(tl.balance)
            # Link back to the invoice line via move_id lines with same tax
            # Best proxy: distribute proportionally or just accumulate per tax
            # Store keyed by tax_line_id so we can match to invoice lines below
            tax_key = tl.tax_line_id.id
            if tax_key not in line_tax_amounts:
                line_tax_amounts[tax_key] = 0.0
            line_tax_amounts[tax_key] += tax_amt

        # Get all invoice lines with products
        for line in self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ('line_section', 'line_note') and l.product_id
        ):
            hsn_code = self.get_line_hsn_code(line)

            # Prefer IGST taxes, fall back to any tax
            line_taxes = line.tax_ids.filtered(lambda t: self._is_igst_tax(t))
            if not line_taxes and line.tax_ids:
                line_taxes = line.tax_ids

            if line_taxes:
                tax_rate = line_taxes[0].amount
                taxable_amount = line.price_subtotal

                # Compute tax amount: use line.price_total - line.price_subtotal
                # which Odoo computes correctly for both draft and posted invoices
                line_tax_amount = line.price_total - line.price_subtotal

                key = f"{hsn_code}_{tax_rate}"
                if key not in tax_info:
                    tax_info[key] = {
                        'hsn_code': hsn_code,
                        'taxable_amount': 0.0,
                        'tax_rate': tax_rate,
                        'tax_amount': 0.0,
                    }
                tax_info[key]['taxable_amount'] += taxable_amount
                tax_info[key]['tax_amount'] += line_tax_amount
            else:
                if hsn_code:
                    key = f"{hsn_code}_0"
                    if key not in tax_info:
                        tax_info[key] = {
                            'hsn_code': hsn_code,
                            'taxable_amount': 0.0,
                            'tax_rate': 0.0,
                            'tax_amount': 0.0,
                        }
                    tax_info[key]['taxable_amount'] += line.price_subtotal

        # If price_total - price_subtotal gave 0 (can happen on some edge cases),
        # fall back to actual tax journal lines distributed by taxable ratio
        total_tax_from_lines = sum(d['tax_amount'] for d in tax_info.values())
        if total_tax_from_lines == 0.0 and tax_journal_lines:
            total_taxable = sum(d['taxable_amount'] for d in tax_info.values()) or 1.0
            total_journal_tax = sum(
                abs(tl.amount_currency) if tl.amount_currency else abs(tl.balance)
                for tl in tax_journal_lines
            )
            # Get rate from first tax journal line
            first_tax = tax_journal_lines[0].tax_line_id
            for key, data in tax_info.items():
                ratio = data['taxable_amount'] / total_taxable
                data['tax_amount'] = total_journal_tax * ratio
                if data['tax_rate'] == 0.0:
                    data['tax_rate'] = first_tax.amount

        # Group by HSN code (combine if same HSN, different rates)
        final_tax_info = {}
        for key, data in tax_info.items():
            hsn = data['hsn_code']
            if hsn not in final_tax_info:
                final_tax_info[hsn] = {
                    'taxable_amount': 0.0,
                    'tax_rate': data['tax_rate'],
                    'tax_amount': 0.0,
                }
            final_tax_info[hsn]['taxable_amount'] += data['taxable_amount']
            final_tax_info[hsn]['tax_amount'] += data['tax_amount']
            if data['tax_rate'] > final_tax_info[hsn]['tax_rate']:
                final_tax_info[hsn]['tax_rate'] = data['tax_rate']

        return final_tax_info

    def get_igst_tax_details(self):
        """Get IGST tax rate and amount from invoice tax lines (or any tax if IGST not found)"""
        self.ensure_one()
        igst_rate = 18.0  # Default rate
        igst_amount = 0.0
        
        # Get tax lines (use balance for credit/debit, or amount_currency for currency)
        tax_lines = self.line_ids.filtered(lambda l: l.display_type == 'tax' and l.tax_line_id)
        
        # First, try to find IGST tax lines
        igst_tax_lines = []
        other_tax_lines = []
        
        for tax_line in tax_lines:
            tax = tax_line.tax_line_id
            if self._is_igst_tax(tax):
                igst_tax_lines.append(tax_line)
            else:
                other_tax_lines.append(tax_line)
        
        # Use IGST if available, otherwise use any tax
        tax_lines_to_use = igst_tax_lines if igst_tax_lines else other_tax_lines
        
        for tax_line in tax_lines_to_use:
            tax = tax_line.tax_line_id
            # Use the tax rate from the tax definition
            igst_rate = tax.amount
            # Calculate tax amount: prefer amount_currency (in invoice currency) over balance
            if tax_line.amount_currency:
                # Use amount_currency which is in the invoice currency
                igst_amount += abs(tax_line.amount_currency)
            else:
                # Fallback to balance if amount_currency not available
                igst_amount += abs(tax_line.balance)
        
        # If no tax lines found, try to calculate from invoice lines
        if igst_amount == 0.0 and self.amount_tax > 0:
            # Get tax from invoice lines
            for line in self.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note') and l.tax_ids):
                # Prefer IGST, but use any tax if IGST not found
                line_taxes = line.tax_ids.filtered(lambda t: self._is_igst_tax(t))
                if not line_taxes:
                    line_taxes = line.tax_ids
                
                if line_taxes:
                    igst_rate = line_taxes[0].amount
                    break
            
            # Use total tax amount as fallback
            igst_amount = self.amount_tax
        
        return {
            'rate': igst_rate,
            'amount': igst_amount,
        }

    def get_sale_order_info(self):
        """Get sales order information from invoice"""
        self.ensure_one()
        sale_orders = self.line_ids.mapped('sale_line_ids.order_id')
        if sale_orders:
            return sale_orders[0]
        # Fallback: try to get from invoice_origin
        if self.invoice_origin:
            sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
            if sale_order:
                return sale_order
        return False

    def get_line_hsn_code(self, line):
        """Get HSN/SAC code from product template"""
        try:
            # Get HSN/SAC code from product template (primary source)
            if line.product_id and line.product_id.product_tmpl_id:
                if hasattr(line.product_id.product_tmpl_id, 'l10n_in_hsn_code') and line.product_id.product_tmpl_id.l10n_in_hsn_code:
                    return line.product_id.product_tmpl_id.l10n_in_hsn_code
        except:
            pass
        
        # Fallback: Try to get from invoice line (if overridden)
        try:
            if hasattr(line, 'l10n_in_hsn_code') and line.l10n_in_hsn_code:
                return line.l10n_in_hsn_code
        except:
            pass
        
        return ''

    def get_company_bank_info(self):
        """Get company bank information: prefer sale order ks_bank_id, else company partner bank."""
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
            # Prefer invoice's own ks_bank_id (set from sale order when invoice is created)
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
            # Else prefer bank from linked sale order (ks_bank_id)
            sale_order = self.get_sale_order_info()
            if sale_order and getattr(sale_order, 'ks_bank_id', None):
                bank = sale_order.ks_bank_id
                bank_info['bank_name'] = bank.name or ''
                bank_info['acc_number'] = getattr(bank, 'bic', None) or ''  # Account Number in ks_sale_order
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

    def get_payment_bank_info(self):
        """Get bank information from payment if payment has been received in a bank account"""
        self.ensure_one()
        bank_info = {
            'ad_code': '',
            'bank_name': '',
            'acc_number': '',
            'ifsc_code': '',
            'branch': '',
            'swift_code': '',
            'city': '',
            'has_payment': False,
        }
        
        try:
            # Only check for customer invoices (out_invoice) where payment is received
            if self.move_type != 'out_invoice':
                return bank_info
            
            # Get all payments linked to this invoice
            # Try multiple methods to find payments
            all_payments = self.env['account.payment']
            
            # Method 1: Use reconciled_payment_ids (computed field)
            if self.reconciled_payment_ids:
                all_payments |= self.reconciled_payment_ids
            
            # Method 2: Use matched_payment_ids
            if self.matched_payment_ids:
                all_payments |= self.matched_payment_ids
            
            # Method 3: Search through move lines for reconciled payments
            if not all_payments:
                receivable_lines = self.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable' and l.reconciled
                )
                if receivable_lines:
                    # Get reconciled move lines
                    reconciled_debit_lines = receivable_lines.mapped('matched_debit_ids.debit_move_id')
                    reconciled_credit_lines = receivable_lines.mapped('matched_credit_ids.credit_move_id')
                    all_reconciled_lines = reconciled_debit_lines | reconciled_credit_lines
                    
                    # Get payment moves from reconciled lines
                    payment_moves = all_reconciled_lines.mapped('move_id').filtered(
                        lambda m: m.payment_id
                    )
                    if payment_moves:
                        all_payments = payment_moves.mapped('payment_id')
            
            if not all_payments:
                return bank_info
            
            # Filter for payments that have a bank journal
            # First try: payments with posted moves and bank journal type
            bank_payments = all_payments.filtered(
                lambda p: p.journal_id and 
                p.journal_id.type == 'bank' and
                p.move_id and 
                p.move_id.state == 'posted'
            )
            
            # If no bank payments found, try any payment with bank account
            if not bank_payments:
                bank_payments = all_payments.filtered(
                    lambda p: p.journal_id and 
                    p.journal_id.bank_account_id and
                    p.move_id and 
                    p.move_id.state == 'posted'
                )
            
            # Last resort: get any payment with a journal that has bank_account_id
            if not bank_payments:
                bank_payments = all_payments.filtered(
                    lambda p: p.journal_id and 
                    (p.journal_id.type == 'bank' or p.journal_id.bank_account_id)
                )
            
            if not bank_payments:
                return bank_info
            
            # Get the first bank payment
            payment = bank_payments[0]
            
            bank_info['has_payment'] = True
            
            # Get bank account from journal
            bank_account = payment.journal_id.bank_account_id
            
            # If no bank_account_id, try to get from journal's linked bank accounts
            if not bank_account and payment.journal_id:
                # Try to find bank account from company's bank accounts that match this journal
                company_banks = self.company_id.partner_id.bank_ids
                if company_banks:
                    # Try to match by journal
                    matching_bank = company_banks.filtered(
                        lambda b: b.journal_id == payment.journal_id
                    )
                    if matching_bank:
                        bank_account = matching_bank[0]
                    else:
                        # Use first bank account as fallback
                        bank_account = company_banks[0]
            
            # Get bank information
            if bank_account:
                # Get bank name from bank_id
                if bank_account.bank_id:
                    bank_info['bank_name'] = bank_account.bank_id.name or ''
                
                # Get account number
                bank_info['acc_number'] = bank_account.acc_number or ''
                
                # Get SWIFT Code from bank_id.bic
                if bank_account.bank_id and bank_account.bank_id.bic:
                    bank_info['swift_code'] = bank_account.bank_id.bic
                
                # Get City from bank_id
                if bank_account.bank_id and bank_account.bank_id.city:
                    bank_info['city'] = bank_account.bank_id.city
                
                # Get custom fields (AD Code, IFSC, Branch) from bank_account
                try:
                    if hasattr(bank_account, 'ad_code') and bank_account.ad_code:
                        bank_info['ad_code'] = bank_account.ad_code
                except:
                    pass
                
                try:
                    if hasattr(bank_account, 'ifsc_code') and bank_account.ifsc_code:
                        bank_info['ifsc_code'] = bank_account.ifsc_code
                except:
                    pass
                
                try:
                    if hasattr(bank_account, 'branch') and bank_account.branch:
                        bank_info['branch'] = bank_account.branch
                except:
                    pass
            
            # Fallback: Get info from journal if bank_account not found or missing data
            if payment.journal_id:
                # Use journal name if bank name not found
                if not bank_info['bank_name']:
                    bank_info['bank_name'] = payment.journal_id.name or ''
                
                # Get SWIFT Code from journal code field
                if not bank_info['swift_code'] and payment.journal_id.code:
                    bank_info['swift_code'] = payment.journal_id.code
                
                # Get custom fields from journal
                try:
                    if not bank_info['ad_code'] and hasattr(payment.journal_id, 'ad_code') and payment.journal_id.ad_code:
                        bank_info['ad_code'] = payment.journal_id.ad_code
                except:
                    pass
                
                try:
                    if not bank_info['ifsc_code'] and hasattr(payment.journal_id, 'ifsc_code') and payment.journal_id.ifsc_code:
                        bank_info['ifsc_code'] = payment.journal_id.ifsc_code
                except:
                    pass
                
                try:
                    if not bank_info['branch'] and hasattr(payment.journal_id, 'branch') and payment.journal_id.branch:
                        bank_info['branch'] = payment.journal_id.branch
                except:
                    pass
                
        except Exception:
            pass
        
        return bank_info

