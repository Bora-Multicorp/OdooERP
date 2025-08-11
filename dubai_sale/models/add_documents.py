

from odoo import models, fields, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'


    attachment_count = fields.Integer(
        string="Attachments",
        compute="_compute_attachment_count"
    )

    def _compute_attachment_count(self):
        Attachment = self.env['ir.attachment']
        for order in self:
            order.attachment_count = Attachment.search_count([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id)
            ])

# working on sending attachments in email to customer



    def action_view_attachments(self):
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'context': {
                'default_res_model': 'sale.order',  # Explicitly set the model
                'default_res_id': self.id,
                'default_company_id': self.company_id.id,
            },
            'domain': [
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', self.id)
            ],
            'target': 'current',

            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    Attach files to sale order
                </p><p>
                    Use this feature to attach any files you would like to share with your customers<br/>
                    (e.g: airways bill, transport bill, export bill...).
                </p>
            """),
        }
    


