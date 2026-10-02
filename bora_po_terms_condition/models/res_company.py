# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools import is_html_empty


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_terms = fields.Html(
        string='Default Purchase Terms and Conditions',
        translate=True,
    )
    purchase_terms_type = fields.Selection(
        [
            ('plain', 'Add a Note'),
            ('html', 'Add a link to a Web Page'),
        ],
        string='Purchase Terms & Conditions format',
        default='plain',
    )
    purchase_terms_html = fields.Html(
        string='Default Purchase Terms and Conditions as a Web page',
        translate=True,
        sanitize_attributes=False,
        compute='_compute_purchase_terms_html',
        store=True,
        readonly=False,
    )

    @api.depends('purchase_terms_type')
    def _compute_purchase_terms_html(self):
        for company in self.filtered(
            lambda company: is_html_empty(company.purchase_terms_html) and company.purchase_terms_type == 'html'
        ):
            html = self.env['ir.qweb']._render(
                'bora_po_terms_condition.purchase_default_terms_and_conditions',
                {
                    'company_name': company.name,
                    'company_country': company.country_id.name if company.country_id else '',
                },
                raise_if_not_found=False,
            )
            if html:
                company.purchase_terms_html = html
