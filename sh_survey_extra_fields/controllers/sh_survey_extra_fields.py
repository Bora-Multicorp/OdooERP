# Part of Softhealer Technologies.

from odoo import http
from odoo.http import request

class SurveyController(http.Controller):

    @http.route(['/survey/get_many2many_field_data'], type='json', auth="public", methods=['POST'])
    def get_many2many_field_data(self, **kw):
        records = []
        rec_name = False
        if kw.get("model_id", False):
            modelRecord = request.env["ir.model"].sudo().search([
                ('id', '=', kw.get("model_id"))
            ], limit=1)
            if modelRecord:
                modelRecord = modelRecord.sudo()
                rec_name = modelRecord._rec_name
                rec_name = 'display_name'
                records = request.env[modelRecord.model].sudo(
                ).search_read([], fields=[rec_name, 'id'])

                # give any rec_name value to name key in record in order to use in js.
                if records:
                    records = [dict(item, name=item.get(rec_name))
                               for item in records]
        return dict(
            records=records,
            rec_name=rec_name,
        )

    @http.route(['/survey/get_many2one_field_data'], type='json', auth="public", methods=['POST'])
    def get_many2one_field_data(self, **kw):
        records = []
        rec_name = False
        if kw.get("model_id", False):
            modelRecord = request.env["ir.model"].sudo().search([
                ('id', '=', kw.get("model_id"))
            ], limit=1)
            if modelRecord:
                modelRecord = modelRecord.sudo()
                rec_name = modelRecord._rec_name
                records = request.env[modelRecord.model].sudo(
                ).search_read([], fields=[rec_name, 'id'])

                # give any rec_name value to name key in record in order to use in js.
                if records:
                    records = [dict(item, name=item.get(rec_name))
                               for item in records]

        return dict(
            records=records,
            rec_name=rec_name,
        )

    @http.route(['/survey/get_countries'], type='json', auth="public", methods=['POST'], csrf=False)
    def get_countries(self, **kw):
        return dict(
            countries=request.env["res.country"].sudo(
            ).search_read([], fields=['name', 'id']),
            country_states=request.env["res.country"].state_ids,
        )

    @http.route(['/survey/get_ountry_info/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], csrf=False)
    def get_ountry_info(self, country, **kw):
        return dict(
            states=[(st.id, st.name, st.code) for st in country.state_ids],
            phone_code=country.phone_code,
            zip_required=country.zip_required,
            state_required=country.state_required,
        )

    
    @http.route('/survey/download/<model("survey.user_input.line"):answer_line>/<string:answer_token>', type='http', auth='public', website=True)
    def survey_download_file(self, answer_line, answer_token):
        base_url = request.httprequest.url_root
        if answer_line.sudo().answer_type == "ans_sh_file":
            download_url = f"{base_url}/web/content/{answer_line._name}/{answer_line.id}/value_ans_sh_file/{answer_line.value_ans_sh_file_fname}?download=true&access_token={answer_token}"
            return request.redirect(download_url)
        return request.redirect(base_url)
