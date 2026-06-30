# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AccountAccount(models.Model):
    _name = 'account.account'
    _inherit = ['account.account', 'mail.thread', 'mail.activity.mixin']

    # ── Hierarchy fields ──────────────────────────────────────────────────────

    layered_parent_id = fields.Many2one(
        comodel_name='account.account',
        string='Parent Account',
        domain="[('account_type', '=', account_type), ('company_id', '=', company_id), ('id', '!=', id)]",
        tracking=True,
        help='Assign a parent account of the same type to establish a hierarchy. '
             'This account becomes a child (leaf) node under the selected parent.',
        index=True,
    )

    layered_child_ids = fields.One2many(
        comodel_name='account.account',
        inverse_name='layered_parent_id',
        string='Child Accounts',
        help='Direct child accounts that roll up into this parent.',
    )

    layered_account_ids = fields.Many2many(
        comodel_name='account.account',
        string='Layered Accounts',
        compute='_compute_layered_account_ids',
        help='All descendant accounts (all levels) under this account.',
    )

    layered_depth = fields.Integer(
        string='Hierarchy Depth',
        compute='_compute_layered_depth',
        store=True,
        help='Depth level of this account in the hierarchy. Root accounts = 1.',
    )

    is_parent_account = fields.Boolean(
        string='Is Parent Account',
        compute='_compute_is_parent_account',
        store=True,
        help='True when this account has at least one child account assigned.',
    )

    layered_is_leaf = fields.Boolean(
        string='Is Leaf Account',
        compute='_compute_is_parent_account',
        store=True,
        help='True when this account has no child accounts (transactions allowed).',
    )

    # ── Computed fields ───────────────────────────────────────────────────────

    @api.depends('layered_child_ids', 'layered_child_ids.layered_child_ids')
    def _compute_is_parent_account(self):
        for account in self:
            has_children = bool(account.layered_child_ids)
            account.is_parent_account = has_children
            account.layered_is_leaf = not has_children

    @api.depends('layered_parent_id', 'layered_parent_id.layered_depth')
    def _compute_layered_depth(self):
        for account in self:
            depth = 1
            parent = account.layered_parent_id
            visited = set()
            while parent and parent.id not in visited:
                depth += 1
                visited.add(parent.id)
                parent = parent.layered_parent_id
            account.layered_depth = depth

    def _compute_layered_account_ids(self):
        """Recursively collect all descendant account IDs."""
        for account in self:
            descendants = self._get_all_descendants(account)
            account.layered_account_ids = [(6, 0, descendants.ids)]

    def _get_all_descendants(self, account):
        """Return a recordset of all descendant accounts (all levels)."""
        result = self.env['account.account']
        for child in account.layered_child_ids:
            result |= child
            result |= self._get_all_descendants(child)
        return result

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('layered_parent_id', 'account_type')
    def _check_parent_account_type(self):
        """UC-A07: Enforce account type consistency between parent and child."""
        for account in self:
            if account.layered_parent_id:
                if account.layered_parent_id.account_type != account.account_type:
                    raise ValidationError(_(
                        "Account type mismatch: account '%(child)s' (type: %(child_type)s) "
                        "cannot be assigned under parent '%(parent)s' (type: %(parent_type)s). "
                        "Parent and child accounts must share the same account type.",
                        child=account.name,
                        child_type=account.account_type,
                        parent=account.layered_parent_id.name,
                        parent_type=account.layered_parent_id.account_type,
                    ))

    @api.constrains('layered_parent_id')
    def _check_depth_limit(self):
        """A-05: Enforce the company-configured maximum depth level."""
        for account in self:
            if account.layered_parent_id:
                max_depth = int(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'layered_coa.max_depth', default='0'
                    )
                )
                if max_depth and account.layered_depth > max_depth:
                    raise ValidationError(_(
                        "Depth limit exceeded: assigning '%(account)s' as a child of '%(parent)s' "
                        "would create a hierarchy depth of %(depth)s levels. "
                        "Your company is configured to allow a maximum of %(max)s levels. "
                        "Please adjust the Limit Layered COA setting or restructure your hierarchy.",
                        account=account.name,
                        parent=account.layered_parent_id.name,
                        depth=account.layered_depth,
                        max=max_depth,
                    ))

    @api.constrains('layered_parent_id')
    def _check_no_circular_hierarchy(self):
        """Prevent circular parent-child relationships."""
        for account in self:
            if account.layered_parent_id:
                ancestor = account.layered_parent_id
                visited = set()
                while ancestor:
                    if ancestor.id == account.id:
                        raise ValidationError(_(
                            "Circular hierarchy detected: '%(account)s' cannot be its own "
                            "ancestor. Please review the parent account assignment.",
                            account=account.name,
                        ))
                    if ancestor.id in visited:
                        break
                    visited.add(ancestor.id)
                    ancestor = ancestor.layered_parent_id

    @api.constrains('layered_parent_id')
    def _check_company_consistency(self):
        """Enforce parent and child belong to the same company."""
        for account in self:
            if account.layered_parent_id:
                if account.layered_parent_id.company_id != account.company_id:
                    raise ValidationError(_(
                        "Company mismatch: account '%(child)s' belongs to company '%(child_company)s' "
                        "but the selected parent '%(parent)s' belongs to '%(parent_company)s'. "
                        "Parent and child accounts must belong to the same company.",
                        child=account.name,
                        child_company=account.company_id.name,
                        parent=account.layered_parent_id.name,
                        parent_company=account.layered_parent_id.company_id.name,
                    ))

    # ── Deprecation logic ─────────────────────────────────────────────────────

    @api.onchange('layered_parent_id')
    def _onchange_layered_parent_id(self):
        """
        Warn users if they are converting a leaf account to a parent/child
        and the account has existing move lines.
        """
        if self.layered_parent_id and self._origin.id:
            move_lines = self.env['account.move.line'].search_count([
                ('account_id', '=', self._origin.id),
            ])
            if move_lines:
                return {
                    'warning': {
                        'title': _('Account Has Existing Transactions'),
                        'message': _(
                            "Account '%s' has %s existing journal entry line(s). "
                            "Assigning it as a child account is allowed, but you should ensure "
                            "all transactions are reclassified before converting this account "
                            "into a parent account in the future.\n\n"
                            "Refer to UC-A06 in the BRD for the reclassification procedure."
                        ) % (self.name, move_lines),
                    }
                }

    def write(self, vals):
        """
        A-03: When child accounts are assigned, auto-deprecate the parent account
        to prevent direct transaction postings at the parent level.
        Also enforce UC-A09: category changes only on leaf accounts.
        """
        # UC-A09: Block account_type change on parent accounts
        if 'account_type' in vals:
            for account in self:
                if account.is_parent_account:
                    raise UserError(_(
                        "Cannot change the account type of '%s': this account is a parent account "
                        "and has child accounts assigned to it. Only leaf (child) accounts "
                        "may have their account type changed.",
                        account.name,
                    ))

        result = super().write(vals)

        # A-03: Auto-deprecate parent accounts that now have children
        if 'layered_parent_id' in vals and vals.get('layered_parent_id'):
            parent_id = vals['layered_parent_id']
            parent = self.env['account.account'].browse(parent_id)
            if parent.exists() and not parent.deprecated:
                parent.with_context(layered_coa_deprecate=True).write({'deprecated': True})
                parent.message_post(
                    body=_(
                        "<b>Account Auto-Deprecated by Layered COA</b><br/>"
                        "This account has been automatically marked as <i>deprecated</i> "
                        "because one or more child accounts have been assigned to it. "
                        "Direct transaction postings to parent accounts are not permitted. "
                        "All journal entries must be posted to leaf (child) accounts only."
                    ),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

        return result

    # ── Override: block postings to parent accounts ───────────────────────────

    @api.constrains('deprecated')
    def _check_deprecated_not_forced_active_on_parent(self):
        """
        UC-A04: Prevent un-deprecating a parent account that still has children.
        """
        for account in self:
            if not account.deprecated and account.is_parent_account:
                if not self.env.context.get('layered_coa_deprecate'):
                    raise ValidationError(_(
                        "Cannot activate account '%s': this account is a parent account "
                        "with child accounts assigned. Parent accounts must remain deprecated "
                        "to prevent accidental journal entry postings. "
                        "Remove all child account assignments first.",
                        account.name,
                    ))

    # ── UC-A05: Convert child to parent ───────────────────────────────────────

    def action_convert_to_parent(self):
        """
        UC-A05: Convert a leaf account to a parent account.
        Requires zero balance and no existing journal entry lines.
        """
        self.ensure_one()
        if self.is_parent_account:
            raise UserError(_("Account '%s' is already a parent account.", self.name))

        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', self.id),
        ], limit=1)
        if move_lines:
            raise UserError(_(
                "Cannot convert '%s' to a parent account: it has existing journal entry lines. "
                "Please reclassify all transactions to another account first (see UC-A06).",
                self.name,
            ))

        # Remove parent assignment to make this a root-level parent
        self.write({'layered_parent_id': False})
        self.message_post(
            body=_(
                "<b>Account Converted to Parent</b><br/>"
                "This account has been designated as a parent account. "
                "Child accounts can now be assigned to it. "
                "Direct transaction postings to this account are restricted."
            ),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        return True

    # ── UC-A06: Reclassify transactions ───────────────────────────────────────

    def action_open_reclassify_wizard(self):
        """
        UC-A06: Open a wizard to reclassify existing journal entries
        from this account to another account before hierarchy conversion.
        """
        self.ensure_one()
        return {
            'name': _('Reclassify Transactions — %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'layered.coa.reclassify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_account_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }

    # ── Hierarchy path helper ─────────────────────────────────────────────────

    def _get_hierarchy_path(self):
        """Return the full hierarchy path as a string, e.g. 'Assets / Current / Cash'."""
        self.ensure_one()
        parts = [self.name]
        parent = self.layered_parent_id
        visited = set()
        while parent and parent.id not in visited:
            parts.insert(0, parent.name)
            visited.add(parent.id)
            parent = parent.layered_parent_id
        return ' / '.join(parts)

    # ── Override name_get for hierarchy display ───────────────────────────────

    def name_get(self):
        """
        Append hierarchy path indicator for parent accounts in dropdowns.
        """
        result = []
        for account in self:
            name = account.name
            if account.code:
                name = '%s %s' % (account.code, name)
            if account.is_parent_account:
                name = '[Group] %s' % name
            result.append((account.id, name))
        return result
