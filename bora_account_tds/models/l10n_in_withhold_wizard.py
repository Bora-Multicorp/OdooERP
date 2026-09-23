# -*- coding: utf-8 -*-
from odoo import api, fields, models


class L10nInWithholdWizard(models.TransientModel):
    _inherit = 'l10n_in.withhold.wizard'

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids', [])
        if active_model in ('account.move', 'account.payment') and active_ids:
            active_record = self.env[active_model].browse(active_ids[0])
            if active_record.company_id:
                result['company_id'] = active_record.company_id.id
        return result

    def action_create_and_post_withhold(self):
        self.ensure_one()
        # If branch/sub-company has no withholding account set, inherit from parent company
        if not self.company_id.l10n_in_withholding_account_id:
            parent = self.company_id.parent_id
            while parent:
                if parent.l10n_in_withholding_account_id:
                    self.company_id.sudo().l10n_in_withholding_account_id = parent.l10n_in_withholding_account_id
                    break
                parent = parent.parent_id
        return super().action_create_and_post_withhold()


class L10nInWithholdWizardLine(models.TransientModel):
    _inherit = 'l10n_in.withhold.wizard.line'

    company_id = fields.Many2one(
        related='withhold_id.company_id',
        string="Company",
        store=True,
    )
