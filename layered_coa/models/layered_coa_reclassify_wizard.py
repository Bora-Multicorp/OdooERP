# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LayeredCoaReclassifyWizard(models.TransientModel):
    """
    UC-A06: Wizard to reclassify all journal entry lines from one account
    to another before converting the source account into a parent account.
    """
    _name = 'layered.coa.reclassify.wizard'
    _description = 'Layered COA — Reclassify Transactions Wizard'

    source_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Source Account',
        required=True,
        readonly=True,
        help='The account whose transactions will be reclassified.',
    )

    target_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Target Account',
        required=True,
        domain="[('account_type', '=', source_account_type), "
               "('id', '!=', source_account_id), "
               "('deprecated', '=', False), "
               "('is_parent_account', '=', False)]",
        help='The leaf account that will receive all reclassified transactions.',
    )

    source_account_type = fields.Selection(
        related='source_account_id.account_type',
        string='Source Account Type',
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    move_line_count = fields.Integer(
        string='Journal Entry Lines',
        compute='_compute_move_line_count',
        help='Number of journal entry lines that will be reclassified.',
    )

    reclassification_date = fields.Date(
        string='Reclassification Date',
        required=True,
        default=fields.Date.context_today,
        help='Date to use for the reclassification journal entry.',
    )

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Reclassification Journal',
        required=True,
        domain="[('company_id', '=', company_id), ('type', 'in', ['general', 'miscellaneous'])]",
        help='The journal used to post the reclassification entry.',
    )

    notes = fields.Text(
        string='Notes / Reference',
        help='Optional notes to attach to the reclassification journal entry.',
    )

    @api.depends('source_account_id')
    def _compute_move_line_count(self):
        for wizard in self:
            wizard.move_line_count = self.env['account.move.line'].search_count([
                ('account_id', '=', wizard.source_account_id.id),
            ]) if wizard.source_account_id else 0

    @api.constrains('target_account_id')
    def _check_target_not_source(self):
        for wizard in self:
            if wizard.target_account_id == wizard.source_account_id:
                raise ValidationError(_('The target account must be different from the source account.'))

    def action_reclassify(self):
        """
        Create a reclassification journal entry that transfers the net balance
        from the source account to the target account, then post it.
        """
        self.ensure_one()

        if not self.target_account_id:
            raise UserError(_('Please select a target account.'))

        if self.target_account_id.is_parent_account:
            raise UserError(_(
                "Target account '%s' is a parent account and cannot receive transactions. "
                "Please select a leaf (child) account.",
                self.target_account_id.name,
            ))

        # Calculate net balance on source account
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', self.source_account_id.id),
            ('move_id.state', '=', 'posted'),
        ])

        if not move_lines:
            raise UserError(_(
                "No posted journal entry lines found on account '%s'. "
                "Nothing to reclassify.",
                self.source_account_id.name,
            ))

        net_debit = sum(move_lines.mapped('debit'))
        net_credit = sum(move_lines.mapped('credit'))
        net_balance = net_debit - net_credit

        if net_balance == 0:
            raise UserError(_(
                "The net balance of account '%s' is zero. "
                "No reclassification entry is needed.",
                self.source_account_id.name,
            ))

        # Build reclassification journal entry
        ref = self.notes or _(
            'Layered COA Reclassification: %s → %s'
        ) % (self.source_account_id.name, self.target_account_id.name)

        move_vals = {
            'move_type': 'entry',
            'date': self.reclassification_date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'ref': ref,
            'line_ids': [],
        }

        if net_balance > 0:
            # Debit on source = credit source, debit target
            move_vals['line_ids'] = [
                (0, 0, {
                    'account_id': self.source_account_id.id,
                    'credit': abs(net_balance),
                    'debit': 0.0,
                    'name': ref,
                }),
                (0, 0, {
                    'account_id': self.target_account_id.id,
                    'debit': abs(net_balance),
                    'credit': 0.0,
                    'name': ref,
                }),
            ]
        else:
            # Credit on source = debit source, credit target
            move_vals['line_ids'] = [
                (0, 0, {
                    'account_id': self.source_account_id.id,
                    'debit': abs(net_balance),
                    'credit': 0.0,
                    'name': ref,
                }),
                (0, 0, {
                    'account_id': self.target_account_id.id,
                    'credit': abs(net_balance),
                    'debit': 0.0,
                    'name': ref,
                }),
            ]

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        # Log on source account
        self.source_account_id.message_post(
            body=_(
                "<b>Transactions Reclassified (UC-A06)</b><br/>"
                "Net balance of <b>%(balance)s</b> reclassified to account "
                "<b>%(target)s</b> via journal entry "
                "<a href='/odoo/accounting/journal-entries/%(move_id)s'>%(move_name)s</a>.",
                balance=net_balance,
                target=self.target_account_id.name,
                move_id=move.id,
                move_name=move.name,
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        return {
            'name': _('Reclassification Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }
