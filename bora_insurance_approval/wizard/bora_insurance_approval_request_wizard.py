# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BoraInsuranceApprovalRequestWizard(models.TransientModel):
    _name = 'bora.insurance.approval.request.wizard'
    _description = 'Bora Insurance Approval Request Wizard'

    bora_policy_ids = fields.Many2many('insurance.policy', string='Insurance Policies', required=True)

    bora_approver1_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_user_ids', store=False,
        relation='bora_ins_req_wiz_approver1_rel')
    bora_approver2_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_user_ids', store=False,
        relation='bora_ins_req_wiz_approver2_rel')
    bora_approver1_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_approver_ids', store=False,
        relation='bora_ins_req_wiz_filtered1_rel')
    bora_approver2_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_approver_ids', store=False,
        relation='bora_ins_req_wiz_filtered2_rel')

    bora_approver1_user = fields.Many2one(
        'res.users', string='Approver 1', required=True,
        domain="[('id', 'in', bora_approver1_filtered_ids)]")
    bora_approver2_user = fields.Many2one(
        'res.users', string='Approver 2',
        domain="[('id', 'in', bora_approver2_filtered_ids)]")
    bora_show_approver2 = fields.Boolean(compute='_compute_show_approver2')
    bora_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)
    bora_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)
    bora_pm1_already_approved = fields.Boolean(string='PM1 Already Approved', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        is_update = self.env.context.get('bora_is_update', False)
        policy_ids = self.env.context.get('default_bora_policy_ids') or res.get('bora_policy_ids')
        if is_update and policy_ids:
            p_ids = []
            if isinstance(policy_ids, models.BaseModel):
                p_ids = policy_ids.ids
            elif isinstance(policy_ids, (int, str)) and str(policy_ids).isdigit():
                p_ids = [int(policy_ids)]
            elif isinstance(policy_ids, (list, tuple)):
                for item in policy_ids:
                    if isinstance(item, models.BaseModel):
                        p_ids.extend(item.ids)
                    elif isinstance(item, (int, str)) and str(item).isdigit():
                        p_ids.append(int(item))
                    elif isinstance(item, (list, tuple)):
                        if len(item) == 3:
                            cmd, val1, val2 = item[0], item[1], item[2]
                            if cmd == 6 and isinstance(val2, (list, tuple)):
                                p_ids.extend([int(x) for x in val2 if isinstance(x, (int, str)) and str(x).isdigit()])
                            elif cmd == 4 and isinstance(val1, (int, str)) and str(val1).isdigit():
                                p_ids.append(int(val1))
                        else:
                            p_ids.extend([int(x) for x in item if isinstance(x, (int, str)) and str(x).isdigit()])

            policies = self.env['insurance.policy'].browse(p_ids)
            if policies:
                if len(policies) == 1:
                    p = policies[0]
                    if p.bora_insurance_pm1_approved and p.bora_insurance_pm1_id:
                        res['bora_pm1_already_approved'] = True
                        res['bora_approver1_user'] = p.bora_insurance_pm1_id.id
                res['bora_is_update_mode'] = True
        return res

    @api.depends('bora_policy_ids')
    def _compute_show_approver2(self):
        for wiz in self:
            first_policy = wiz.bora_policy_ids[:1]
            if first_policy and first_policy._has_insurance_approval_config():
                wiz.bora_show_approver2 = (
                    first_policy._get_insurance_approval_config().is_dual_approval()
                )
            else:
                wiz.bora_show_approver2 = False

    @api.depends('bora_policy_ids')
    def _compute_approver_user_ids(self):
        for wiz in self:
            first_policy = wiz.bora_policy_ids[:1]
            if first_policy and first_policy._has_insurance_approval_config():
                config = first_policy._get_insurance_approval_config()
                wiz.bora_approver1_user_ids = config.bora_insurance_pm1_ids
                wiz.bora_approver2_user_ids = config.bora_insurance_pm2_ids
            else:
                wiz.bora_approver1_user_ids = False
                wiz.bora_approver2_user_ids = False

    @api.depends('bora_approver1_user_ids', 'bora_approver2_user_ids',
                 'bora_approver1_user', 'bora_approver2_user')
    def _compute_filtered_approver_ids(self):
        for wiz in self:
            wiz.bora_approver1_filtered_ids = (
                wiz.bora_approver1_user_ids - wiz.bora_approver2_user
                if wiz.bora_approver2_user else wiz.bora_approver1_user_ids
            )
            wiz.bora_approver2_filtered_ids = (
                wiz.bora_approver2_user_ids - wiz.bora_approver1_user
                if wiz.bora_approver1_user else wiz.bora_approver2_user_ids
            )

    @api.depends('bora_policy_ids', 'bora_approver1_user', 'bora_approver2_user', 'bora_is_update_mode')
    def _compute_approval_info(self):
        for wiz in self:
            first_policy = wiz.bora_policy_ids[:1]
            if not first_policy or not first_policy._has_insurance_approval_config():
                wiz.bora_approval_info = '<p>No insurance approval configuration found.</p>'
                continue
            config = first_policy._get_insurance_approval_config()
            html = ''

            if wiz.bora_is_update_mode and first_policy.bora_insurance_pm1_approved and first_policy.bora_insurance_pm1_id:
                html += (
                    '<div class="alert alert-success" role="alert">'
                    '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                    ' Keeping the same Approver 1 will preserve their approval.'
                    '</div>'
                ) % first_policy.bora_insurance_pm1_id.name

            html += '<div class="alert alert-info">'
            html += '<h5><strong>Insurance Approval Request</strong></h5>'
            html += '<p>You are about to submit insurance approval request.</p>'
            if config.is_dual_approval():
                html += ('<p><strong>Note:</strong> Both Approver 1 and Approver 2 approval is required. '
                         'Approver 2 cannot approve until Approver 1 has approved.</p>')
            else:
                html += '<p><strong>Note:</strong> Approver 1 approval is required.</p>'
            html += '</div>'
            wiz.bora_approval_info = html

    @api.onchange('bora_approver1_user')
    def _onchange_approver1(self):
        if self.bora_approver1_user and self.bora_approver2_user == self.bora_approver1_user:
            self.bora_approver2_user = False

    @api.onchange('bora_approver2_user')
    def _onchange_approver2(self):
        if self.bora_approver2_user and self.bora_approver1_user == self.bora_approver2_user:
            self.bora_approver1_user = False

    def action_confirm_request(self):
        self.ensure_one()
        if not self.bora_approver1_user:
            raise UserError(_('Please select Approver 1.'))
        if self.bora_show_approver2 and not self.bora_approver2_user:
            raise UserError(_('Please select Approver 2 (required for dual approval mode).'))

        is_update = self.env.context.get('bora_is_update', False)

        for policy in self.bora_policy_ids:
            if is_update and policy.bora_insurance_pm1_approved and policy.bora_insurance_pm1_id:
                if policy.bora_insurance_pm1_id != self.bora_approver1_user:
                    raise UserError(_(
                        "Approver 1 (%s) has already approved this request and cannot be changed."
                    ) % policy.bora_insurance_pm1_id.name)

            preserve_pm1 = (
                is_update
                and policy.bora_insurance_pm1_id
                and policy.bora_insurance_pm1_id == self.bora_approver1_user
                and policy.bora_insurance_pm1_approved
            )

            if is_update:
                policy._bora_cancel_insurance_activities()
                write_vals = {
                    'bora_insurance_pm1_id': False,
                    'bora_insurance_pm2_id': False,
                    'bora_insurance_pm2_approved': False,
                }
                if not preserve_pm1:
                    write_vals['bora_insurance_pm1_approved'] = False
                policy.write(write_vals)

            policy.bora_do_request_insurance_approval(
                pm1_user=self.bora_approver1_user,
                pm2_user=self.bora_approver2_user if self.bora_approver2_user else None,
            )

            if preserve_pm1:
                policy.write({'bora_insurance_pm1_approved': True})
                policy._bora_unlink_user_activity(policy.bora_insurance_pm1_id)
                if policy.bora_insurance_pm2_id:
                    policy._create_insurance_approval_activity(policy.bora_insurance_pm2_id, 'Confirm')

        return {'type': 'ir.actions.act_window_close'}
