from odoo import fields, models, api


class POApproverTeam(models.Model):
    _name = 'purchase.order.approvers'
    _description = 'PO Approvers'
    _rec_name = 'user_id'

    sequence = fields.Integer(string='Sequence', readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each approver member must be unique.')
    ]


    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        max_sequence = self.search([], order="sequence desc", limit=1).sequence
        defaults['sequence'] = max_sequence + 1 if max_sequence else 1
        return defaults