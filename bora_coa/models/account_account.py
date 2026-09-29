# -*- coding: utf-8 -*-
import json
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def _setup_bora_coa_all(self):
        """
        Executed during module installation and upgrade:
        1. Update existing 2 accounts:
           - 600292 -> 900001 Domestic Debtor (asset_receivable, reconcile=True)
           - 600291 -> 900002 Domestic Creditor (liability_payable, reconcile=True)
        2. Create 2 new accounts:
           - 900003 Export Debtor (asset_receivable, reconcile=True)
           - 900004 Export Creditor (liability_payable, reconcile=True)
        3. Update mapping section (code_store for all companies & ir.default)
        """
        _logger.info("Bora COA: Setting up Chart of Accounts...")
        cr = self._cr
        companies = self.env['res.company'].sudo().search([])
        company_ids = companies.ids if companies else []

        # Find all root company IDs
        root_company_ids = set()
        for c in companies:
            curr = c
            while curr.parent_id:
                curr = curr.parent_id
            root_company_ids.add(curr.id)

        # -------------------------------------------------------------------------
        # 1. Update Existing Account: 600292 -> 900001 Domestic Debtor
        # -------------------------------------------------------------------------
        cr.execute("""
            UPDATE account_account
            SET code_store = replace(code_store::text, '600292', '900001')::jsonb
            WHERE code_store::text LIKE '%600292%';
        """)
        acc_900001 = self._find_single_account(['900001', '600292'])
        if acc_900001:
            acc_900001.sudo().write({
                'name': 'Domestic Debtor',
                'account_type': 'asset_receivable',
                'reconcile': True,
            })
            _logger.info("Bora COA: Account 900001 (Domestic Debtor) ready.")
        else:
            acc_900001 = self.sudo().create({
                'name': 'Domestic Debtor',
                'code': '900001',
                'account_type': 'asset_receivable',
                'reconcile': True,
            })

        # -------------------------------------------------------------------------
        # 2. Update Existing Account: 600291 -> 900002 Domestic Creditor
        # -------------------------------------------------------------------------
        cr.execute("""
            UPDATE account_account
            SET code_store = replace(code_store::text, '600291', '900002')::jsonb
            WHERE code_store::text LIKE '%600291%';
        """)
        acc_900002 = self._find_single_account(['900002', '600291'])
        if acc_900002:
            acc_900002.sudo().write({
                'name': 'Domestic Creditor',
                'account_type': 'liability_payable',
                'reconcile': True,
            })
            _logger.info("Bora COA: Account 900002 (Domestic Creditor) ready.")
        else:
            acc_900002 = self.sudo().create({
                'name': 'Domestic Creditor',
                'code': '900002',
                'account_type': 'liability_payable',
                'reconcile': True,
            })

        # -------------------------------------------------------------------------
        # 3. Create Account: 900003 Export Debtor
        # -------------------------------------------------------------------------
        acc_900003 = self._find_single_account(['900003'])
        if not acc_900003:
            acc_900003 = self.sudo().create({
                'name': 'Export Debtor',
                'code': '900003',
                'account_type': 'asset_receivable',
                'reconcile': True,
            })
            _logger.info("Bora COA: Account 900003 (Export Debtor) created.")
        else:
            acc_900003.sudo().write({
                'name': 'Export Debtor',
                'account_type': 'asset_receivable',
                'reconcile': True,
            })

        # -------------------------------------------------------------------------
        # 4. Create Account: 900004 Export Creditor
        # -------------------------------------------------------------------------
        acc_900004 = self._find_single_account(['900004'])
        if not acc_900004:
            acc_900004 = self.sudo().create({
                'name': 'Export Creditor',
                'code': '900004',
                'account_type': 'liability_payable',
                'reconcile': True,
            })
            _logger.info("Bora COA: Account 900004 (Export Creditor) created.")
        else:
            acc_900004.sudo().write({
                'name': 'Export Creditor',
                'account_type': 'liability_payable',
                'reconcile': True,
            })

        # -------------------------------------------------------------------------
        # 5. Ensure all 4 accounts have code_store for all root companies and company links
        # -------------------------------------------------------------------------
        if root_company_ids:
            c900001 = json.dumps({str(cid): '900001' for cid in root_company_ids})
            c900002 = json.dumps({str(cid): '900002' for cid in root_company_ids})
            c900003 = json.dumps({str(cid): '900003' for cid in root_company_ids})
            c900004 = json.dumps({str(cid): '900004' for cid in root_company_ids})
            cr.execute("UPDATE account_account SET code_store = %s::jsonb WHERE id = %s", (c900001, acc_900001.id))
            cr.execute("UPDATE account_account SET code_store = %s::jsonb WHERE id = %s", (c900002, acc_900002.id))
            cr.execute("UPDATE account_account SET code_store = %s::jsonb WHERE id = %s", (c900003, acc_900003.id))
            cr.execute("UPDATE account_account SET code_store = %s::jsonb WHERE id = %s", (c900004, acc_900004.id))

        if company_ids:
            for acc in [acc_900001, acc_900002, acc_900003, acc_900004]:
                for cid in company_ids:
                    cr.execute("""
                        INSERT INTO account_account_res_company_rel (account_account_id, res_company_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                    """, (acc.id, cid))

        # -------------------------------------------------------------------------
        # 6. Update Mapping Section (ir.default)
        # -------------------------------------------------------------------------
        rec_json = json.dumps(acc_900001.id)
        pay_json = json.dumps(acc_900002.id)

        cr.execute("""
            UPDATE ir_default
            SET json_value = %s
            WHERE field_id = (SELECT id FROM ir_model_fields WHERE model = 'res.partner' AND name = 'property_account_receivable_id');
        """, (rec_json,))

        cr.execute("""
            UPDATE ir_default
            SET json_value = %s
            WHERE field_id = (SELECT id FROM ir_model_fields WHERE model = 'res.partner' AND name = 'property_account_payable_id');
        """, (pay_json,))

        cr.execute("""
            INSERT INTO ir_default (field_id, company_id, json_value)
            SELECT id, NULL, %s
            FROM ir_model_fields
            WHERE model = 'res.partner' AND name = 'property_account_receivable_id'
              AND NOT EXISTS (
                  SELECT 1 FROM ir_default
                  WHERE field_id = ir_model_fields.id AND company_id IS NULL AND user_id IS NULL
              );
        """, (rec_json,))

        cr.execute("""
            INSERT INTO ir_default (field_id, company_id, json_value)
            SELECT id, NULL, %s
            FROM ir_model_fields
            WHERE model = 'res.partner' AND name = 'property_account_payable_id'
              AND NOT EXISTS (
                  SELECT 1 FROM ir_default
                  WHERE field_id = ir_model_fields.id AND company_id IS NULL AND user_id IS NULL
              );
        """, (pay_json,))

        self.env.registry.clear_cache()
        _logger.info("Bora COA: Setup completed successfully.")

    @api.model
    def _find_single_account(self, codes):
        for code in codes:
            acc = self.sudo().search([('code', '=', code)], limit=1)
            if acc:
                return acc
            self._cr.execute("SELECT id FROM account_account WHERE code_store::text LIKE %s LIMIT 1", (f'%"{code}"%',))
            row = self._cr.fetchone()
            if row:
                return self.sudo().browse(row[0])
        return None
