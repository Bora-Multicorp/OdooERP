# -*- coding: utf-8 -*-

from odoo.http import request

from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import ensure_db


class KsWeb(Home):
    def _web_client_readonly(self):
        return False

    @http.route('/clear/cache', type='json', auth="user")
    def clear_cache(self, **kwargs):
        request.env.registry.clear_cache()

    @http.route([
        '/web',
        '/odoo',
        '/odoo/<path:subpath>',
        '/scoped_app/<path:subpath>'
    ], type='http', auth="none", readonly=_web_client_readonly)
    def web_client(self, s_action=None, **kw):
        ensure_db()
        user = request.env.user.browse(request.session.uid)

        # Handle expired passwords
        if user.ks_is_passwd_expired:
            request.session.logout()
            return

        # Fetch company ID from cookies if available
        company_id = request.httprequest.cookies.get('cids', '')

        # Handle debug mode restrictions
        if kw.get('debug') != "0":
            profile_mgmt_pool = request.env['user.management'].sudo()
            domain = [('ks_disable_debug_mode', '=', True), ('ks_user_ids', 'in', user.id)]

            # Process company IDs if provided
            if company_id:
                company_ids = [int(cid) for cid in company_id.replace('-', ',').split(',')]
                domain.append(('ks_company_ids', 'in', company_ids))

            # Check profile management rules
            if profile_mgmt_pool.search_count(domain):
                redirect_url = '/odoo'
                if kw.get('subpath'):
                    redirect_url = f"{redirect_url}/{kw['subpath']}"
                return request.redirect(f"{redirect_url}?debug=0")

        return super(KsWeb, self).web_client(s_action=s_action, **kw)

