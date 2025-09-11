from odoo import fields, models, api
import random

class PIUnlockTeam(models.Model):
    _name = 'pi.unlock.approvers'
    _description = 'PI Unlock Approvers'
    _rec_name = 'user_id'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    default_user = fields.Boolean(string="Default")
    group = fields.Selection([
        ('group1', 'Group 1'),
        ('group2', 'Group 2'),
    ], string="Groups", required=True) 
    color = fields.Integer(string="Color Index", readonly=True) 

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approver member must be unique.')
    ]

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
        # Step 1: Collect all affected sale orders
        affected_sos = self.env['sale.order']  # empty recordset

        for approver in self:
            # Find all SOs where this approver is linked
            sos = self.env['sale.order'].search([
                ('approval_users_ids.user_id', '=', approver.user_id.id)
            ])
            affected_sos |= sos  # accumulate affected SOs

            # Delete linked PO approval users with empty state
            for so in sos:
                records_to_delete = so.approval_users_ids.filtered(
                    lambda r: r.user_id == approver.user_id and not r.state
                )
                records_to_delete.unlink()

        # Step 2: Delete the approvers themselves
        result = super().unlink()

        # Step 3: Re-sequence all remaining approvers globally
        all_approvers = self.env['pi.unlock.approvers'].search([], order='sequence')
        for idx, record in enumerate(all_approvers, start=1):
            record.sequence = idx

        # Step 4: Re-sequence SO approval users per sale order
        for so in affected_sos:
            po_users = so.approval_users_ids.sorted(key='sequence')
            for idx, user in enumerate(po_users, start=1):
                user.sequence = idx

        return result