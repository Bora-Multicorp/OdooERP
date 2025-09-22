# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VendorApprovalConfig(models.Model):
    _name = "vendor.approval.config"
    _description = "Vendor Approval Settings"
    _rec_name = 'user_id'


    sequence = fields.Integer(string='Sequence', required=False)
    user_id = fields.Many2one('res.users', string='Approval User', required=False)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approval user must be unique.'),
        ('unique_sequence', 'unique(sequence)', 'Each sequence must be unique.'),
    ]

    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        max_sequence = self.search([], order="sequence desc", limit=1).sequence
        defaults['sequence'] = max_sequence + 1 if max_sequence else 1
        return defaults

    def _validate_unique_user(self, user_id, exclude_ids=None):
        domain = [('user_id', '=', user_id)]
        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))
        if self.search_count(domain):
            raise ValidationError(_("This user is already added to the approval list."))

    def _validate_unique_sequence(self, sequence, exclude_ids=None):
        domain = [('sequence', '=', sequence)]
        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))
        if self.search_count(domain):
            raise ValidationError(_("This sequence number is already used. Please choose a different one."))

    @api.model
    def create(self, vals):
        # Auto-generate sequence if not given
        if not vals.get('sequence'):
            seq_str = self.env['ir.sequence'].next_by_code('vendor.approval.config')
            try:
                vals['sequence'] = int(seq_str)
            except (ValueError, TypeError):
                raise ValidationError(_("Failed to generate a valid sequence number."))

        # Validate sequence and user_id
        if vals['sequence'] <= 0:
            raise ValidationError(_("Sequence must be a positive number."))

        self._validate_unique_user(vals.get('user_id'))
        self._validate_unique_sequence(vals.get('sequence'))

        res = super().create(vals)
        res._update_draft_kyc_approvals()
        return res

    def write(self, vals):
        for rec in self:
            if 'sequence' in vals:
                if vals['sequence'] <= 0:
                    raise ValidationError(_("Sequence must be a positive number."))
                rec._validate_unique_sequence(vals['sequence'], exclude_ids=rec.ids)

            if 'user_id' in vals:
                rec._validate_unique_user(vals['user_id'], exclude_ids=rec.ids)

        res = super().write(vals)
        self._update_draft_kyc_approvals()
        return res

    def unlink(self):
        res = super().unlink()
        self._update_draft_kyc_approvals()
        return res

    def _update_draft_kyc_approvals(self):
        # kyc_approvals = self.env['res.partner.kyc.approval'].search([('state', '=', 'draft')])
        # config_users = self.search([]).sorted(key=lambda r: r.sequence)

        # for kyc in kyc_approvals:
        #     approval_lines = [(5, 0, 0)]  # Clear existing first
        #     for config in config_users:
        #         approval_lines.append((0, 0, {
        #             'sequence': config.sequence,
        #             'user_id': config.user_id.id,
        #         }))
        #     kyc.write({'approval_users_ids': approval_lines})


        """Fast SQL approach. Bypasses ORM. Use with caution."""
        cr = self.env.cr
        # Get config users ordered by sequence
        confs = self.env['vendor.approval.config'].sudo().search([], order='sequence')
        if not confs:
            return

        # Prepare values
        conf_vals = [(c.sequence, c.user_id.id) for c in confs]

        # get KYC ids (only ids, no record instantiation)
        cr.execute("SELECT id FROM res_partner_kyc_approval WHERE state = %s", ('draft',))
        rows = cr.fetchall()
        kyc_ids = [r[0] for r in rows]
        if not kyc_ids:
            return

        # Delete existing approval.users rows for these kyc ids
        # Table name for approval.users is assumed 'approval_users' (model -> table)
        cr.execute("""
            DELETE FROM approval_users
            WHERE kyc_approval_id = ANY(%s)
        """, (kyc_ids,))

        # Bulk insert in chunks (to avoid huge single INSERT)
        insert_tuples = []
        for kyc_id in kyc_ids:
            for seq, uid in conf_vals:
                insert_tuples.append((kyc_id, seq, uid))

        # executemany is efficient
        cr.executemany(
            "INSERT INTO approval_users (kyc_approval_id, sequence, user_id) VALUES (%s, %s, %s)",
            insert_tuples
        )

        # Optionally, update sequences or caches if needed afterwards:
        # self.env['res.partner.kyc.approval'].invalidate_cache()

















