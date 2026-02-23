# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime

import odoo.modules.registry
import werkzeug
from dateutil.relativedelta import relativedelta
from odoo.http import request
from odoo.tools.translate import _

import odoo
from odoo import http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.session import Session
from odoo.addons.web.controllers.utils import ensure_db

_logger = logging.getLogger(__name__)

SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error', 'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name', 'partner_id',
                          'password', 'confirm_password', 'city', 'country_id', 'lang', 'signup_email'}
LOGIN_SUCCESSFUL_PARAMS = set()


class KsSessionWebsite(Session):

    @http.route('/web/session/logout', type='http', auth="none", website=True, multilang=False, sitemap=False)
    def logout(self, redirect='/web'):
        activity = request.env['recent.activity'].sudo().search(
            [('ks_session_id', '=', request.session.sid)])
        if activity:
            activity.ks_action_logout()
        return super().logout(redirect=redirect)


class Home(Home):
    @http.route('/web/login')
    def web_login(self, *args, **kw):
        redirect = None
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect(redirect)

        # simulate hybrid auth=user/auth=public, despite using auth=none to be able
        # to redirect users when no db is selected - cfr ensure_db()
        if request.env.uid is None:
            if request.session.uid is None:
                # no user -> auth=public with specific website public user
                request.env["ir.http"]._auth_method_public()
            else:
                # auth=user
                request.update_env(user=request.session.uid)

        values = {k: v for k, v in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            try:
                user = request.env['res.users'].sudo().search([('login', '=', request.params['login'])])
                login = True
                # Check that is password is expired then show password expire message while login.
                if user and not user.has_group('base.group_system') and user.ks_is_passwd_expired:
                    values['error'] = _("Password Expired")
                    login = False
                # If no any profile for the user then user don't have an access of database.
                elif user and not user.groups_id and not user.has_group('base.group_system'):
                    login = False
                    values['error'] = _(
                        "This database is not allowed, Please contact your Admin to activate this database")
                if login:
                    credential = {'login': request.params['login'], 'password': request.params['password'],
                                  'type': 'password'}
                    uid = request.session.authenticate(request.db, credential)
                    request.params['login_success'] = True
                    return request.redirect(self._login_redirect(uid['uid'], redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employees can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"

        # Check that Auth module is installed or not.
        # If installed then it will update the providers on the login page.
        module = request.env['ir.module.module'].sudo().search(
            [('name', '=', 'auth_oauth'), ('state', '=', 'installed')],
            limit=1)
        login_successful = '/web/login_successful'
        if module:
            response.qcontext.update(self.get_auth_signup_config())
            if request.session.uid:
                if request.httprequest.method == 'GET' and request.params.get('redirect'):
                    # Redirect if already logged in and redirect param is present
                    return request.redirect(request.params.get('redirect'))
                # Add message for non-internal user account without redirect if account was just created
                if response.location == login_successful and kw.get('confirm_password'):
                    return request.redirect_query(login_successful, query={'account_created': True})
            if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
                # Redirect if already logged in and redirect param is present
                return request.redirect(request.params.get('redirect'))
            providers = self.list_providers()
            if response.is_qweb:
                error = request.params.get('oauth_error')
                if error == '1':
                    error = _("Sign up is not allowed on this database.")
                elif error == '2':
                    error = _("Access Denied")
                elif error == '3':
                    error = _(
                        "You do not have access to this database or your invitation has expired. Please ask for an invitation and be sure to follow the link in your invitation email.")
                else:
                    error = None

                response.qcontext['providers'] = providers
                if error:
                    response.qcontext['error'] = error

            return response
        else:
            response.qcontext.update(self.get_auth_signup_config())
            if request.session.uid:
                if request.httprequest.method == 'GET' and request.params.get('redirect'):
                    # Redirect if already logged in and redirect param is present
                    return request.redirect(request.params.get('redirect'))
                # Add message for non-internal user account without redirect if account was just created
                if response.location == login_successful and kw.get('confirm_password'):
                    return request.redirect_query(login_successful, query={'account_created': True})
            return response

    def list_providers(self):
        try:
            providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            params = dict(
                response_type='token',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=json.dumps(state),
            )
            provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params))
        return providers


class KsAuthSignupHomeInherit(AuthSignupHome):

    @http.route('/web/reset_password/direct', type='http', auth='public', website=True, sitemap=False, csrf=False, )
    def ks_auth_reset_password(self):
        qcontext = self.get_auth_signup_qcontext()
        response = request.render('ks_access_manager_ninja.reset_password_direct', qcontext)
        return response

    @http.route('/web/reset_password/submit', type='http', methods=['POST'], auth="public", website=True, csrf=False)
    def ks_change_password(self, **kw):
        values = {}
        reset_password_template = 'ks_access_manager_ninja.reset_password_direct'
        if kw['confirm_new_password'] == kw['old_password']:
            values['error'] = _("New password must be different from current password.")
            return request.render(reset_password_template, values)

        if kw['confirm_new_password'] == kw['new_password']:
            try:
                uid = request.session.authenticate(request.session.db, {'login': kw['user_name'],
                                                                        'password': kw['old_password'],
                                                                        'type': 'password'})
                user = request.env['res.users'].sudo().search([('id', '=', uid['uid'])])
                vals = {'ks_password_update': datetime.now(), 'password': kw['confirm_new_password'],
                        'ks_is_passwd_expired': False}
                expiry_month = request.env['ir.config_parameter'].sudo().get_param(
                    'ks_access_manager_ninja.password_expire_in_days')
                if expiry_month:
                    expire_date = user.ks_password_update + relativedelta(
                        days=int(
                            expiry_month))
                    vals['ks_password_expire_date'] = expire_date
                user.sudo().write(vals)
                return request.redirect('/web/login')

            except Exception as e:
                _logger.error(e)
                values['error'] = _("Login or Password Is Incorrect")
                return request.render(reset_password_template, values)
        else:
            values['error'] = _("Password Not Match")
            return request.render(reset_password_template, values)
