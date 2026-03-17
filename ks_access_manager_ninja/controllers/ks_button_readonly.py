
from odoo.api import call_kw
from odoo.http import request
from odoo.service.model import get_public_method

from odoo import http
from odoo.addons.web.controllers.dataset import DataSet

class KsCustomButtonController(DataSet):

    @http.route(['/web/dataset/call_button', '/web/dataset/call_button/<path:path>'], type='json', auth="user",
                readonly=DataSet._call_kw_readonly)
    def call_button(self, model, method, args, kwargs, path=None):
        current_user = request.env.user
        company_ids = current_user.company_ids.ids
        readonly_access = request.env['user.management'].sudo().search([
            ('active', '=', True),
            ('ks_user_ids', 'in', current_user.id),
            ('ks_readonly', '=', True),
            ('ks_company_ids', 'in', company_ids)
        ], limit=1)

        if readonly_access:
            return False
        else:
            return super(KsCustomButtonController, self).call_button(model, method, args, kwargs, path)