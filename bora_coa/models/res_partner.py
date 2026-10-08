# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, models
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _register_hook(self):
        super()._register_hook()
        try:
            self.env['account.account'].sudo()._setup_bora_coa_all()
        except Exception as e:
            self.env.cr.rollback()
            _logger.warning("Bora COA setup in _register_hook: %s", e)

    @api.model
    def _get_coa_accounts_map(self):
        """
        Fast lookup dictionary for accounts 900001-900004.
        """
        Account = self.env['account.account'].sudo()
        accounts = Account.search([('code', 'in', ['900001', '900002', '900003', '900004'])])
        res = {acc.code: acc for acc in accounts}
        if len(res) < 4:
            self._cr.execute("""
                SELECT id, code_store
                FROM account_account
                WHERE code_store::text LIKE '%900001%'
                   OR code_store::text LIKE '%900002%'
                   OR code_store::text LIKE '%900003%'
                   OR code_store::text LIKE '%900004%';
            """)
            for acc_id, code_store in self._cr.fetchall():
                acc = Account.browse(acc_id)
                for c in ['900001', '900002', '900003', '900004']:
                    if c not in res and code_store and f'"{c}"' in json.dumps(code_store):
                        res[c] = acc
        return res

    def _field_to_sql(self, alias: str, fname: str, query=None, flush: bool = True) -> SQL:
        """
        Dynamically resolve Account Receivable and Account Payable in SQL:
        1. When Company country matches Contact country:
           Account Receivable = 900001 Domestic Debtor
           Account Payable = 900002 Domestic Creditor
        2. When Company country does not match Contact country:
           Account Receivable = 900003 Export Debtor
           Account Payable = 900004 Export Creditor
        """
        if fname in ('property_account_receivable_id', 'property_account_payable_id'):
            acc_map = self._get_coa_accounts_map()
            is_rec = (fname == 'property_account_receivable_id')
            dom_acc = acc_map.get('900001' if is_rec else '900002')
            exp_acc = acc_map.get('900003' if is_rec else '900004')

            if dom_acc and exp_acc:
                company = self.env.company
                comp_country_id = company.country_id.id if company.country_id else None
                company_id_str = str(company.id)
                alias_ident = SQL.identifier(alias)
                fname_ident = SQL.identifier(fname)

                raw_col = SQL('%s.%s->>%s', alias_ident, fname_ident, company_id_str)
                country_col = SQL('%s.country_id', alias_ident)

                if comp_country_id:
                    computed_acc_id = SQL(
                        'CASE WHEN %s IS NOT NULL AND %s != %s THEN %s ELSE %s END',
                        country_col, country_col, comp_country_id, exp_acc.id, dom_acc.id
                    )
                else:
                    computed_acc_id = SQL('%s', dom_acc.id)

                resolved_id = SQL(
                    '''CASE 
                        WHEN (%s) IS NOT NULL AND (%s)::int NOT IN (%s, %s)
                        THEN (%s)::int
                        ELSE (%s)
                    END''',
                    raw_col, raw_col, dom_acc.id, exp_acc.id, raw_col, computed_acc_id
                )

                return SQL(
                    '''(SELECT %(cotable_alias)s.id
                        FROM account_account AS %(cotable_alias)s
                        WHERE %(cotable_alias)s.id = (%(field)s))''',
                    cotable_alias=SQL.identifier(f"{alias}_{fname}"),
                    field=resolved_id,
                )

        return super()._field_to_sql(alias, fname, query=query, flush=flush)

    @api.onchange('country_id', 'company_id')
    def _onchange_country_id_coa_accounts(self):
        """
        Dynamically update Account Receivable and Account Payable on Contact Form:
        1. When Company country matches Contact country:
           Account Receivable = 900001 Domestic Debtor
           Account Payable = 900002 Domestic Creditor
        2. When Company country does not match Contact country:
           Account Receivable = 900003 Export Debtor
           Account Payable = 900004 Export Creditor
        """
        company = self.company_id or self.env.company
        company_country = company.country_id
        contact_country = self.country_id

        is_export = bool(contact_country and company_country and contact_country.id != company_country.id)
        acc_map = self._get_coa_accounts_map()
        rec_acc = acc_map.get('900003' if is_export else '900001')
        pay_acc = acc_map.get('900004' if is_export else '900002')

        if rec_acc:
            self.property_account_receivable_id = rec_acc
        if pay_acc:
            self.property_account_payable_id = pay_acc

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        acc_map = self._get_coa_accounts_map()
        company = self.env.company
        company_country = company.country_id
        contact_country_id = defaults.get('country_id')
        contact_country = self.env['res.country'].browse(contact_country_id) if contact_country_id else False

        is_export = bool(contact_country and company_country and contact_country.id != company_country.id)
        if 'property_account_receivable_id' in fields_list:
            acc = acc_map.get('900003' if is_export else '900001')
            if acc:
                defaults['property_account_receivable_id'] = acc.id
        if 'property_account_payable_id' in fields_list:
            acc = acc_map.get('900004' if is_export else '900002')
            if acc:
                defaults['property_account_payable_id'] = acc.id
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        acc_map = self._get_coa_accounts_map()
        rec_dom = acc_map.get('900001')
        rec_exp = acc_map.get('900003')
        pay_dom = acc_map.get('900002')
        pay_exp = acc_map.get('900004')

        for vals in vals_list:
            company_id = vals.get('company_id')
            company = self.env['res.company'].browse(company_id) if company_id else self.env.company
            company_country = company.country_id
            contact_country_id = vals.get('country_id')
            contact_country = self.env['res.country'].browse(contact_country_id) if contact_country_id else False

            is_export = bool(contact_country and company_country and contact_country.id != company_country.id)
            expected_rec = rec_exp if is_export else rec_dom
            expected_pay = pay_exp if is_export else pay_dom

            curr_rec = vals.get('property_account_receivable_id')
            if expected_rec and (not curr_rec or curr_rec in (rec_dom.id if rec_dom else False, rec_exp.id if rec_exp else False)):
                vals['property_account_receivable_id'] = expected_rec.id

            curr_pay = vals.get('property_account_payable_id')
            if expected_pay and (not curr_pay or curr_pay in (pay_dom.id if pay_dom else False, pay_exp.id if pay_exp else False)):
                vals['property_account_payable_id'] = expected_pay.id

        return super().create(vals_list)

    def write(self, vals):
        if 'country_id' in vals or 'company_id' in vals:
            acc_map = self._get_coa_accounts_map()
            rec_dom = acc_map.get('900001')
            rec_exp = acc_map.get('900003')
            pay_dom = acc_map.get('900002')
            pay_exp = acc_map.get('900004')

            for partner in self:
                company = self.env['res.company'].browse(vals['company_id']) if 'company_id' in vals and vals['company_id'] else (partner.company_id or self.env.company)
                company_country = company.country_id
                contact_country = self.env['res.country'].browse(vals['country_id']) if 'country_id' in vals and vals['country_id'] else partner.country_id

                is_export = bool(contact_country and company_country and contact_country.id != company_country.id)
                expected_rec = rec_exp if is_export else rec_dom
                expected_pay = pay_exp if is_export else pay_dom

                if expected_rec:
                    vals['property_account_receivable_id'] = expected_rec.id
                if expected_pay:
                    vals['property_account_payable_id'] = expected_pay.id

        return super().write(vals)
