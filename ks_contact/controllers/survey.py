# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey


class SurveyKsContact(Survey):

    def _prepare_survey_data(self, survey_sudo, answer_sudo, **post):
        """
        Before rendering: purge all skipped=True lines for que_sh_file questions
        that have real file data. This is a safety net that runs on every page load
        so stale skipped lines from previous sessions never cause the error banner.
        """
        stale = answer_sudo.sudo().user_input_line_ids.filtered(
            lambda l: l.skipped
            and l.question_id.question_type == 'que_sh_file'
            and any(
                not sib.skipped and sib.value_ans_sh_file
                for sib in answer_sudo.sudo().user_input_line_ids
                if sib.question_id == l.question_id
            )
        )
        if stale:
            stale.sudo().unlink()
        return super()._prepare_survey_data(survey_sudo, answer_sudo, **post)

    def _check_validity(self, survey_token, answer_token, ensure_token=True, check_partner=True):
        """
        When a vendor opens the pre-filled Re-KYC link (answer_token is explicitly
        provided), skip the partner ownership check so the link works regardless of
        whether the visitor is a public user, portal user, or internal user.
        """
        if answer_token:
            check_partner = False
        return super()._check_validity(
            survey_token, answer_token,
            ensure_token=ensure_token,
            check_partner=check_partner,
        )

    @http.route('/survey/remove_file_answer/<int:line_id>', type='json', auth='public', website=True, methods=['POST'])
    def remove_file_answer(self, line_id, access_token=None, **kwargs):
        """Remove a pre-filled file answer line via JSON (no page reload, no server-side validation)."""
        line = request.env['survey.user_input.line'].sudo().search([
            ('id', '=', line_id),
            ('answer_type', '=', 'ans_sh_file'),
        ], limit=1)
        if not line:
            return {'error': 'not_found'}
        answer = line.user_input_id
        if not access_token or answer.access_token != access_token:
            return {'error': 'invalid_token'}
        line.sudo().unlink()
        return {'status': 'ok'}
