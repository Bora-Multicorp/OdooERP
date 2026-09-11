# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _check_stamp_and_signature_validations(self, res_ids=None, model=None):
        company = self.env.company
        target_model = model or getattr(self, 'model', None)
        if res_ids and target_model:
            records = self.env[target_model].browse(res_ids)
            if records and 'company_id' in records._fields and records[0].company_id:
                company = records[0].company_id

        stamp_missing = not bool(company.stamp_image)
        signature_missing = not bool(self.env.user.sign_signature)

        if stamp_missing or signature_missing:
            errors = []
            if stamp_missing:
                errors.append(
                    _("1. Company / Branch Stamp Missing:\n"
                      "The selected company or branch '%(company)s' does not have a stamp image uploaded.\n\n"
                      "How to add Company Stamp:\n"
                      "• Go to Settings -> Companies -> Companies.\n"
                      "• Open '%(company)s'.\n"
                      "• Under Company Details (below Color), upload your stamp image in the 'Company Stamp' field.\n"
                      "• Save the company form.",
                      company=company.display_name)
                )

            if signature_missing:
                errors.append(
                    _("2. Logged-in User Digital Signature Missing:\n"
                      "The logged-in user '%(user)s' does not have a digital signature configured in Preferences.\n\n"
                      "How to add Digital Signature:\n"
                      "• Click your User Avatar / Name in the top-right header of Odoo.\n"
                      "• Click 'Preferences'.\n"
                      "• Draw or upload your digital signature in the 'Signature' field.\n"
                      "• Click Save.",
                      user=self.env.user.display_name)
                )

            msg = _("PDF Generation & Download Cancelled!\n\n"
                    "Cannot generate PDF report because of missing required configuration:\n\n"
                    "%(details)s\n\n"
                    "Please configure the missing stamp/signature and try printing again.",
                    details="\n\n".join(errors))
            raise UserError(msg)

    def report_action(self, docids, data=None, config_parameter=None):
        if self.report_type == 'qweb-pdf':
            self._check_stamp_and_signature_validations(res_ids=docids, model=self.model)
        return super().report_action(docids, data=data, config_parameter=config_parameter)

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        report_sudo = self._get_report(report_ref)
        if report_sudo and report_sudo.report_type == 'qweb-pdf':
            report_sudo._check_stamp_and_signature_validations(res_ids=res_ids, model=report_sudo.model)
        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
