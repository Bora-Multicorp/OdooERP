from odoo import fields, models, api
import random


class SOCancellationApproverTeam(models.Model):
    _name = 'sale.order.cancellation.approvers'
    _description = 'Cancelation Approvers'
    _rec_name = 'user_id'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    default_approver = fields.Selection([
        ('approver1', 'Approver 1'),
        ('approver2', 'Approver 2'),
    ], string="Default")
    color = fields.Integer(string="Color Index", readonly=True)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approver member must be unique.')
    ]
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_user_ids')

    @api.depends('user_id')
    def _compute_existing_user_ids(self):
        # Get all existing users' IDs
        existing_user_ids_list = self.env['sale.order.cancellation.approvers'].search([]).user_id.ids

        # Convert the list to a set for efficient removal
        existing_user_ids_set = set(existing_user_ids_list)

        for record in self:
            # If the current record has a user_id, remove it from the set
            # The discard() method will not raise an error if the item is not found
            if record.user_id:
                existing_user_ids_set.discard(record.user_id.id)

            # Assign the remaining IDs back to the field
            record.existing_user_ids = [(6, 0, list(existing_user_ids_set))]

    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        group_id = defaults.get('group')
        if group_id:
            max_sequence = self.search([('group', '=', group_id)], order="sequence desc", limit=1).sequence
            defaults['sequence'] = (max_sequence or 0) + 1
        else:
            # If no group is present (e.g., from a form view), find the highest global sequence.
            max_sequence = self.search([], order="sequence desc", limit=1).sequence
            defaults['sequence'] = (max_sequence or 0) + 1

        return defaults

    @api.constrains('default_user', 'group')
    def _check_unique_default_user_per_group(self):
        for record in self:
            if record.default_user:
                existing_default_users = self.search([
                    ('id', '!=', record.id),
                    ('group', '=', record.group),
                    ('default_user', '=', True)
                ])
                if existing_default_users:
                    # Reset the previous default user to False
                    existing_default_users.write({'default_user': False})

    @api.onchange('default_user', 'group')
    def _onchange_default_user(self):
        if self.default_user:
            existing_default_users = self.search([
                ('id', '!=', self._origin.id if self._origin else False),
                ('group', '=', self.group),
                ('default_user', '=', True)
            ])
            if existing_default_users:
                pass

    @api.model
    def create(self, vals):
        if not vals.get('color'):
            # Get all used colors
            used_colors = set(self.search([]).mapped('color'))
            all_colors = set(range(1, 12))  # Odoo has 11 tag colors (1..11)

            # Find available colors
            available_colors = list(all_colors - used_colors)

            if not available_colors:
                # If all colors are used, reset and pick randomly
                available_colors = list(all_colors)

            vals['color'] = random.choice(available_colors)

        return super().create(vals)

    def unlink(self):
        affected_pos = self.env['sale.order']  # empty recordset

        for approver in self:
            # Find all POs where this approver is linked
            pos = self.env['sale.order'].search([
                ('so_approval_users_ids_for_cancellation.user_id', '=', approver.user_id.id)
            ])
            affected_pos |= pos  # accumulate affected POs

            # Delete linked PO approval users with empty state
            for so in pos:
                records_to_delete = so.so_approval_users_ids_for_cancellation.filtered(
                    lambda r: r.user_id == approver.user_id and not r.state
                )
                records_to_delete.unlink()

        # Step 2: Delete the approvers themselves
        result = super().unlink()

        # Step 3: Re-sequence all remaining approvers globally
        all_approvers = self.env['sale.order.cancellation.approvers'].search([], order='sequence')
        for idx, record in enumerate(all_approvers, start=1):
            record.sequence = idx

        for so in affected_pos:
            so_users =so.so_approval_users_ids_for_cancellation.sorted(key='sequence')
            for idx, user in enumerate(so_users, start=1):
                user.sequence = idx

        return result