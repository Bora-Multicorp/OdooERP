# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request


def sitemap_purchase_terms(env, rule, qs):
    if qs and qs.lower() not in '/purchase-terms':
        return
    use_purchase_terms = env['ir.config_parameter'].sudo().get_param('purchase.use_purchase_terms')
    if use_purchase_terms and env.company.purchase_terms_type == 'html':
        yield {'loc': '/purchase-terms'}


class PurchaseTermsController(http.Controller):

    @http.route(['/purchase-terms', '/purchase_terms'], type='http', auth='public', website=True, sitemap=sitemap_purchase_terms)
    def purchase_terms_conditions(self, **kwargs):
        use_purchase_terms = request.env['ir.config_parameter'].sudo().get_param('purchase.use_purchase_terms')
        company = request.env.company
        if not (use_purchase_terms and company.purchase_terms_type == 'html'):
            return request.render('http_routing.http_error', {
                'status_code': _('Oops'),
                'status_message': _("""The requested page is invalid, or doesn't exist anymore.""")})
        values = {
            'use_purchase_terms': use_purchase_terms,
            'company': company,
        }
        return request.render("bora_po_terms_condition.purchase_terms_conditions_page", values)
