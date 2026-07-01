# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey

_logger = logging.getLogger(__name__)


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

    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):
        """
        Before running the standard validation loop, replace empty answers for
        mandatory que_sh_file questions that already have pre-filled file lines
        with a truthy sentinel ('__ks_existing__').  This prevents the server-side
        mandatory check from failing when a vendor hasn't re-uploaded an existing file.

        save_line_que_sh_file (in survey_user_input.py) already knows to preserve
        existing lines when the answer carries no new base64 data.
        """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is True:
            answer_sudo = access_data['answer_sudo']
            survey_sudo = access_data['survey_sudo']
            try:
                questions, _ = survey_sudo._get_survey_questions(
                    answer=answer_sudo,
                    page_id=post.get('page_id'),
                    question_id=post.get('question_id'),
                )
                for question in questions:
                    if question.question_type != 'que_sh_file' or not question.constr_mandatory:
                        continue
                    raw = post.get(str(question.id))
                    if raw:  # new file was uploaded — don't interfere
                        continue
                    existing = request.env['survey.user_input.line'].sudo().search([
                        ('user_input_id', '=', answer_sudo.id),
                        ('question_id', '=', question.id),
                        ('answer_type', '=', 'ans_sh_file'),
                        ('value_ans_sh_file', '!=', False),
                    ], limit=1)
                    if existing:
                        post[str(question.id)] = '__ks_existing__'
            except Exception:
                _logger.exception('KS survey_submit prefill-bypass failed; continuing normally')

        return super().survey_submit(survey_token, answer_token, **post)

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
