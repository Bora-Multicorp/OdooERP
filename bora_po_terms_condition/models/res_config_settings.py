# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_purchase_terms = fields.Boolean(
        string='Default Terms & Conditions',
        config_parameter='purchase.use_purchase_terms',
    )
    purchase_terms = fields.Html(
        related='company_id.purchase_terms',
        string="Terms & Conditions",
        readonly=False,
    )
    purchase_terms_html = fields.Html(
        related='company_id.purchase_terms_html',
        string="Terms & Conditions as a Web page",
        readonly=False,
    )
    purchase_terms_type = fields.Selection(
        related='company_id.purchase_terms_type',
        readonly=False,
    )
    purchase_preview_ready = fields.Boolean(
        string="Display preview button",
        compute='_compute_purchase_terms_preview',
    )

    @api.depends('purchase_terms_type')
    def _compute_purchase_terms_preview(self):
        for setting in self:
            setting.purchase_preview_ready = (
                self.env.company.purchase_terms_type == 'html' and setting.purchase_terms_type == 'html'
            )

    def action_update_purchase_terms(self):
        self.ensure_one()
        if hasattr(self, 'website_id') and self.env.user.has_group('website.group_website_designer'):
            return self.env["website"].get_client_action('/purchase-terms', True)
        return {
            'name': _('Update Terms & Conditions'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'res.company',
            'view_id': self.env.ref("bora_po_terms_condition.res_company_view_form_purchase_terms", False).id,
            'target': 'new',
            'res_id': self.company_id.id,
        }
