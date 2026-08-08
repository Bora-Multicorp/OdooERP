# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BoraInvoiceApprovalRequestWizard(models.TransientModel):
    _name = 'bora.invoice.approval.request.wizard'
    _description = 'Bora Invoice Approval Request Wizard'

    bora_inv_move_id = fields.Many2one('account.move', string='Invoice', required=True)

    # ── Sale-type — computed directly from partner's country code ─────────────
    # Using country_id.code == 'IN' inline everywhere: no env.ref(), no stored
    # field dependency, no chained computed field. Always live and correct.
    bora_inv_is_local = fields.Boolean(
        compute='_compute_inv_sale_type', string='Is Local Sale')
    bora_inv_sale_type_info = fields.Char(
        compute='_compute_inv_sale_type', string='Sale Type')
    # Debug field — shows raw partner country code for troubleshooting
    bora_inv_debug_country_code = fields.Char(
        compute='_compute_inv_sale_type', string='[DEBUG] Country Code')
    bora_inv_debug_partner_country = fields.Char(
        compute='_compute_inv_sale_type', string='[DEBUG] Country Name')
    bora_inv_debug_is_local = fields.Char(
        compute='_compute_inv_sale_type', string='[DEBUG] Is Local (IN check)')

    # Approver pools loaded from config based on sale type
    bora_inv_approver1_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_pools', store=False,
        relation='bora_inv_req_wiz_pool1_rel')
    bora_inv_approver2_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_pools', store=False,
        relation='bora_inv_req_wiz_pool2_rel')
    bora_inv_approver1_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_pools', store=False,
        relation='bora_inv_req_wiz_filtered1_rel')
    bora_inv_approver2_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_pools', store=False,
        relation='bora_inv_req_wiz_filtered2_rel')

    bora_inv_approver1_user = fields.Many2one(
        'res.users', string='Approver 1', required=True,
        domain="[('id', 'in', bora_inv_approver1_filtered_ids)]")
    bora_inv_approver2_user = fields.Many2one(
        'res.users', string='Approver 2',
        domain="[('id', 'in', bora_inv_approver2_filtered_ids)]")
    bora_inv_reason = fields.Text(string='Reason', placeholder='Optional reason...')
    bora_inv_show_approver2 = fields.Boolean(compute='_compute_show_approver2')
    bora_inv_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)
    bora_inv_is_update_mode = fields.Boolean(default=False)
    bora_inv_pm1_already_approved = fields.Boolean(default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        is_update = self.env.context.get('bora_inv_is_update', False)
        move_id = self.env.context.get('default_bora_inv_move_id') or res.get('bora_inv_move_id')
        if is_update and move_id:
            move = self.env['account.move'].browse(move_id)
            if move.bora_inv_pm1_approved and move.bora_inv_pm1_id:
                res['bora_inv_pm1_already_approved'] = True
                res['bora_inv_approver1_user'] = move.bora_inv_pm1_id.id
        return res

    # ─────────────────────────────────────────────────────────────────────────
    # All computed methods use partner_id.country_id.code == 'IN' directly.
    # Depends includes partner_id and country_id so Odoo invalidates correctly.
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('bora_inv_move_id.partner_id.country_id')
    def _compute_inv_sale_type(self):
        for wiz in self:
            partner = wiz.bora_inv_move_id.partner_id
            country = partner.country_id
            country_code = country.code or ''
            country_name = country.name or '(no country set)'
            is_local = country_code == 'IN'

            wiz.bora_inv_is_local = is_local
            wiz.bora_inv_sale_type_info = (
                _('Local Sale (India)') if is_local else _('Export / Foreign Sale')
            )
            # Debug values — visible in the wizard form
            wiz.bora_inv_debug_country_code = country_code or '(empty)'
            wiz.bora_inv_debug_partner_country = country_name
            wiz.bora_inv_debug_is_local = 'TRUE — LOCAL SALE (India)' if is_local else 'FALSE — EXPORT SALE (non-India)'

    @api.depends('bora_inv_move_id.partner_id.country_id')
    def _compute_approver_pools(self):
        for wiz in self:
            move = wiz.bora_inv_move_id
            if not move or not move._has_inv_approval_config():
                wiz.bora_inv_approver1_user_ids = False
                wiz.bora_inv_approver2_user_ids = False
                continue

            # Direct country code check — the single source of truth
            is_local = move.partner_id.country_id.code == 'IN'
            config = move._get_inv_approval_config()
            _mode, pm1_ids, pm2_ids = config.get_approvers_for_sale_type(is_local)
            wiz.bora_inv_approver1_user_ids = pm1_ids
            wiz.bora_inv_approver2_user_ids = pm2_ids

    @api.depends('bora_inv_approver1_user_ids', 'bora_inv_approver2_user_ids',
                 'bora_inv_approver1_user', 'bora_inv_approver2_user')
    def _compute_filtered_pools(self):
        for wiz in self:
            wiz.bora_inv_approver1_filtered_ids = (
                wiz.bora_inv_approver1_user_ids - wiz.bora_inv_approver2_user
                if wiz.bora_inv_approver2_user else wiz.bora_inv_approver1_user_ids
            )
            wiz.bora_inv_approver2_filtered_ids = (
                wiz.bora_inv_approver2_user_ids - wiz.bora_inv_approver1_user
                if wiz.bora_inv_approver1_user else wiz.bora_inv_approver2_user_ids
            )

    @api.depends('bora_inv_move_id.partner_id.country_id')
    def _compute_show_approver2(self):
        for wiz in self:
            move = wiz.bora_inv_move_id
            if move and move._has_inv_approval_config():
                is_local = move.partner_id.country_id.code == 'IN'
                config = move._get_inv_approval_config()
                wiz.bora_inv_show_approver2 = config.is_dual_approval(is_local)
            else:
                wiz.bora_inv_show_approver2 = False

    @api.depends('bora_inv_move_id.partner_id.country_id', 'bora_inv_is_update_mode')
    def _compute_approval_info(self):
        for wiz in self:
            move = wiz.bora_inv_move_id
            if not move or not move._has_inv_approval_config():
                wiz.bora_inv_approval_info = '<p>No invoice approval configuration found.</p>'
                continue

            is_local = move.partner_id.country_id.code == 'IN'
            config = move._get_inv_approval_config()
            html = ''

            if wiz.bora_inv_is_update_mode and move.bora_inv_pm1_approved and move.bora_inv_pm1_id:
                html += (
                    '<div class="alert alert-success">'
                    '<strong>&#10003; Approver 1 (%s) has already approved.</strong> '
                    'Keeping the same Approver 1 will preserve their approval.</div>'
                ) % move.bora_inv_pm1_id.name

            sale_type_label = _('Local Sale (India)') if is_local else _('Export / Foreign Sale')
            html += '<div class="alert alert-%s">' % ('success' if is_local else 'warning')
            html += '<h5><strong>Invoice Approval Request — %s</strong></h5>' % sale_type_label
            html += '<p>You are about to submit this invoice for approval before confirmation.</p>'
            if config.is_dual_approval(is_local):
                html += ('<p><strong>Note:</strong> Both Approver 1 and Approver 2 approval is required. '
                         'Approver 2 cannot approve until Approver 1 has approved.</p>')
            else:
                html += '<p><strong>Note:</strong> Only Approver 1 is required for this sale type.</p>'
            html += '</div>'
            wiz.bora_inv_approval_info = html

    @api.onchange('bora_inv_approver1_user')
    def _onchange_approver1(self):
        if self.bora_inv_approver1_user and self.bora_inv_approver2_user == self.bora_inv_approver1_user:
            self.bora_inv_approver2_user = False

    @api.onchange('bora_inv_approver2_user')
    def _onchange_approver2(self):
        if self.bora_inv_approver2_user and self.bora_inv_approver1_user == self.bora_inv_approver2_user:
            self.bora_inv_approver1_user = False

    def action_confirm_request(self):
        self.ensure_one()
        if not self.bora_inv_approver1_user:
            raise UserError(_('Please select Approver 1.'))
        if self.bora_inv_show_approver2 and not self.bora_inv_approver2_user:
            raise UserError(_('Please select Approver 2 (required for dual approval mode).'))

        is_update = self.env.context.get('bora_inv_is_update', False)
        move = self.bora_inv_move_id

        if is_update and move.bora_inv_pm1_approved and move.bora_inv_pm1_id:
            if move.bora_inv_pm1_id != self.bora_inv_approver1_user:
                raise UserError(_(
                    "Approver 1 (%s) has already approved and cannot be changed."
                ) % move.bora_inv_pm1_id.name)

        preserve_pm1 = (
            is_update
            and move.bora_inv_pm1_id
            and move.bora_inv_pm1_id == self.bora_inv_approver1_user
            and move.bora_inv_pm1_approved
        )

        if is_update:
            move._bora_cancel_inv_activities()
            write_vals = {
                'bora_inv_pm1_id': False,
                'bora_inv_pm2_id': False,
                'bora_inv_pm2_approved': False,
            }
            if not preserve_pm1:
                write_vals['bora_inv_pm1_approved'] = False
            move.write(write_vals)
            msg = (
                _('Approval request updated. PM1 (%s) approval preserved; Approver 2 updated.')
                % move.bora_inv_pm1_id.name
                if preserve_pm1
                else _('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name
            )
            move.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')
            pre_state = move.bora_inv_pre_approval_state or 'draft'
            move.write({'state': pre_state})

        # Always store the sale type from the live country check before submission
        move.write({'bora_inv_is_local_sale': move.partner_id.country_id.code == 'IN'})

        move.bora_inv_do_request_approval(
            pm1_user=self.bora_inv_approver1_user,
            pm2_user=self.bora_inv_approver2_user or None,
            reason=self.bora_inv_reason,
        )

        if preserve_pm1:
            move.write({'bora_inv_pm1_approved': True})
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move.id),
                ('user_id', '=', move.bora_inv_pm1_id.id),
                ('summary', 'ilike', 'Invoice Approval'),
            ]).unlink()
            if move.bora_inv_pm2_id:
                move._create_inv_approval_activity(move.bora_inv_pm2_id, 'Confirm')

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        move = self.bora_inv_move_id
        if move and move.state == 'invoice_approval_pending' and not move.bora_inv_pm1_id:
            pre_state = move.bora_inv_pre_approval_state or 'draft'
            move.write({'state': pre_state, 'bora_inv_pre_approval_state': False})
        return {'type': 'ir.actions.act_window_close'}
