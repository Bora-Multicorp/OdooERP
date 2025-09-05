from odoo import models, fields, api

class ProcurementTeam(models.Model):
    _name = 'purchase.procurement.team'
    _description = 'Procurement Team'

    sequence = fields.Integer(string='Sequence', readonly=True)
    res_user = fields.Many2one('res.users', string='User', required=True)
    user_id = fields.Char(store=False)

    _sql_constraints = [
        ('unique_user_id', 'unique(user_id)', 'Each team member must be unique.')
    ]
 

    # generate sequence
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        max_sequence = self.search([], order="sequence desc", limit=1).sequence
        defaults['sequence'] = max_sequence + 1 if max_sequence else 1
        return defaults
