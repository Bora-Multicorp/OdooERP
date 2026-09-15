from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ks_is_indian_company = fields.Boolean(
        string="Is Indian Company",
        compute="_compute_ks_is_indian_company",
    )

    @api.depends("company_id", "company_id.country_id", "company_id.country_code")
    def _compute_ks_is_indian_company(self):
        for move in self:
            comp = move.company_id or self.env.company
            move.ks_is_indian_company = bool(
                comp and (comp.country_code == "IN" or (comp.country_id and comp.country_id.code == "IN"))
            )
