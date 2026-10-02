# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import is_html_empty
from odoo.tools.mail import html_keep_url


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_terms_type = fields.Selection(
        related='company_id.purchase_terms_type',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'notes' in fields_list and not res.get('notes'):
            use_purchase_terms = self.env['ir.config_parameter'].sudo().get_param('purchase.use_purchase_terms')
            if use_purchase_terms:
                company = self.env.company
                if company.purchase_terms_type == 'html' and company.purchase_terms_html:
                    baseurl = html_keep_url(company.get_base_url() + '/purchase-terms')
                    res['notes'] = _('Terms & Conditions: %s', baseurl)
                elif not is_html_empty(company.purchase_terms):
                    res['notes'] = company.purchase_terms
        return res

    @api.onchange('partner_id')
    def _onchange_partner_id_terms(self):
        use_purchase_terms = self.env['ir.config_parameter'].sudo().get_param('purchase.use_purchase_terms')
        if not use_purchase_terms:
            return
        company = self.company_id or self.env.company
        if company.purchase_terms_type == 'html' and company.purchase_terms_html:
            baseurl = html_keep_url(company.get_base_url() + '/purchase-terms')
            self.notes = _('Terms & Conditions: %s', baseurl)
        elif not is_html_empty(company.purchase_terms):
            if self.partner_id.lang:
                company = company.with_context(lang=self.partner_id.lang)
            self.notes = company.purchase_terms

    @api.model_create_multi
    def create(self, vals_list):
        use_purchase_terms = self.env['ir.config_parameter'].sudo().get_param('purchase.use_purchase_terms')
        if use_purchase_terms:
            for vals in vals_list:
                if not vals.get('notes'):
                    company = (
                        self.env['res.company'].browse(vals.get('company_id'))
                        if vals.get('company_id')
                        else self.env.company
                    )
                    if company.purchase_terms_type == 'html' and company.purchase_terms_html:
                        baseurl = html_keep_url(company.get_base_url() + '/purchase-terms')
                        vals['notes'] = _('Terms & Conditions: %s', baseurl)
                    elif not is_html_empty(company.purchase_terms):
                        partner = (
                            self.env['res.partner'].browse(vals.get('partner_id'))
                            if vals.get('partner_id')
                            else False
                        )
                        if partner and partner.lang:
                            company = company.with_context(lang=partner.lang)
                        vals['notes'] = company.purchase_terms
        return super().create(vals_list)
