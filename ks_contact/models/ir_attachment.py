# -*- coding: utf-8 -*-
import logging
from odoo import models, api
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def check(self, mode, values=None):
        """
        Override check() to grant read access to attachments linked to
        res.partner.kyc.approval records (or child bank/director lines)
        if the current user has read access to the parent KYC Approval record.
        """
        if mode != 'read' or self.env.is_superuser():
            return super().check(mode, values=values)

        try:
            super().check(mode, values=values)
        except AccessError as original_error:
            failing_attachments = self.sudo()
            allowed_att_ids = self._get_kyc_accessible_attachment_ids(failing_attachments.ids)

            # If all failing attachments belong to readable KYC records, suppress error
            if set(failing_attachments.ids).issubset(allowed_att_ids):
                return

            # If only some attachments are allowed, raise exception for the disallowed ones
            disallowed_attachments = failing_attachments.filtered(lambda a: a.id not in allowed_att_ids)
            if disallowed_attachments:
                return super(IrAttachment, disallowed_attachments.with_env(self.env)).check(mode, values=values)

            raise original_error

    @api.model
    def _get_kyc_accessible_attachment_ids(self, attachment_ids):
        """
        Returns a set of attachment IDs (from attachment_ids) that belong to
        or are referenced by res.partner.kyc.approval, bank.details, or director.details
        records that the current user has read access to.
        """
        if not attachment_ids:
            return set()

        allowed_ids = set()
        attachments = self.sudo().browse(attachment_ids)

        kyc_res_ids = set()
        bank_res_ids = set()
        director_res_ids = set()

        for att in attachments:
            if att.res_model == 'res.partner.kyc.approval' and att.res_id:
                kyc_res_ids.add(att.res_id)
            elif att.res_model == 'bank.details' and att.res_id:
                bank_res_ids.add(att.res_id)
            elif att.res_model == 'director.details' and att.res_id:
                director_res_ids.add(att.res_id)

        KycModel = self.env['res.partner.kyc.approval']

        if kyc_res_ids:
            readable_kyc_ids = set(KycModel.search([('id', 'in', list(kyc_res_ids))]).ids)
            for att in attachments:
                if att.res_model == 'res.partner.kyc.approval' and att.res_id in readable_kyc_ids:
                    allowed_ids.add(att.id)

        if bank_res_ids:
            BankModel = self.env['bank.details'].sudo()
            banks = BankModel.browse(list(bank_res_ids))
            bank_kyc_ids = [b.kyc_approval_id.id for b in banks if b.kyc_approval_id]
            if bank_kyc_ids:
                readable_kyc_ids = set(KycModel.search([('id', 'in', bank_kyc_ids)]).ids)
                for att in attachments:
                    if att.res_model == 'bank.details':
                        bank = banks.filtered(lambda b: b.id == att.res_id)
                        if bank and bank.kyc_approval_id and bank.kyc_approval_id.id in readable_kyc_ids:
                            allowed_ids.add(att.id)

        if director_res_ids:
            DirectorModel = self.env['director.details'].sudo()
            directors = DirectorModel.browse(list(director_res_ids))
            director_kyc_ids = [d.kyc_approval_id.id for d in directors if d.kyc_approval_id]
            if director_kyc_ids:
                readable_kyc_ids = set(KycModel.search([('id', 'in', director_kyc_ids)]).ids)
                for att in attachments:
                    if att.res_model == 'director.details':
                        director = directors.filtered(lambda d: d.id == att.res_id)
                        if director and director.kyc_approval_id and director.kyc_approval_id.id in readable_kyc_ids:
                            allowed_ids.add(att.id)

        # Group 2: Check M2M relation tables for KYC records
        unresolved_att_ids = set(attachment_ids) - allowed_ids
        if unresolved_att_ids:
            m2m_tables = [
                ('vendor_kyc_gst_cert_rels', 'partner_id', 'attachment_id'),
                ('vendor_kyc_shop_act_documents_rels', 'partner_id', 'attachment_id'),
                ('pan_card_company_documents_rels', 'partner_id', 'attachment_id'),
                ('vendor_kyc_shop_documents_rels', 'partner_id', 'attachment_id'),
                ('vendor_kyc_shop_photos_rels', 'partner_id', 'attachment_id'),
                ('vendor_kyc_shop_videos_rels', 'partner_id', 'attachment_id'),
                ('vendor_kyc_moa_aoa_rels', 'partner_id', 'attachment_id'),
                ('vendor_kyc_electricity_bill_rels', 'partner_id', 'attachment_id'),
                ('incorportaion_certificate_rels', 'partner_id', 'attachment_id'),
                ('kyc_approval_company_reg_rel', 'kyc_id', 'attachment_id'),
                ('kyc_approval_auth_person_id_rel', 'kyc_id', 'attachment_id'),
            ]
            for table, kyc_col, att_col in m2m_tables:
                query = f"""
                    SELECT {att_col}, {kyc_col}
                    FROM {table}
                    WHERE {att_col} IN %s
                """
                self.env.cr.execute(query, [tuple(unresolved_att_ids)])
                rows = self.env.cr.fetchall()
                if rows:
                    found_kyc_ids = set(r[1] for r in rows)
                    readable_kyc_ids = set(KycModel.search([('id', 'in', list(found_kyc_ids))]).ids)
                    for att_id, kyc_id in rows:
                        if kyc_id in readable_kyc_ids:
                            allowed_ids.add(att_id)

            unresolved_att_ids = set(attachment_ids) - allowed_ids

        if unresolved_att_ids:
            query = """
                SELECT rel.attachment_id, bd.kyc_approval_id
                FROM vendor_bank_detail_cheque_rel rel
                JOIN bank_details bd ON bd.id = rel.kyc_approval_id
                WHERE rel.attachment_id IN %s AND bd.kyc_approval_id IS NOT NULL
            """
            self.env.cr.execute(query, [tuple(unresolved_att_ids)])
            rows = self.env.cr.fetchall()
            if rows:
                found_kyc_ids = set(r[1] for r in rows)
                readable_kyc_ids = set(KycModel.search([('id', 'in', list(found_kyc_ids))]).ids)
                for att_id, kyc_id in rows:
                    if kyc_id in readable_kyc_ids:
                        allowed_ids.add(att_id)

            unresolved_att_ids = set(attachment_ids) - allowed_ids

        if unresolved_att_ids:
            dir_tables = [
                ('vendor_bank_aadhaar_card_rel', 'kyc_approval_id'),
                ('vendor_bank_pan_card_rel', 'kyc_approval_id'),
                ('director_details_govt_id_rel', 'director_id'),
            ]
            for table, dir_col in dir_tables:
                query = f"""
                    SELECT rel.attachment_id, dd.kyc_approval_id
                    FROM {table} rel
                    JOIN director_details dd ON dd.id = rel.{dir_col}
                    WHERE rel.attachment_id IN %s AND dd.kyc_approval_id IS NOT NULL
                """
                self.env.cr.execute(query, [tuple(unresolved_att_ids)])
                rows = self.env.cr.fetchall()
                if rows:
                    found_kyc_ids = set(r[1] for r in rows)
                    readable_kyc_ids = set(KycModel.search([('id', 'in', list(found_kyc_ids))]).ids)
                    for att_id, kyc_id in rows:
                        if kyc_id in readable_kyc_ids:
                            allowed_ids.add(att_id)

        return allowed_ids
