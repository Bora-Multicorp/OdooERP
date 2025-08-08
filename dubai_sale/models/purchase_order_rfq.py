from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        po = super().create(vals)
        if self.env.context.get('from_orderpoint'):
            po._notify_procurement_team_on_RFQ_creation()
        return po
    
    def write(self, vals):
        
        """
        Overrides the write method to notify the procurement team
        when a purchase order is updated from a re-order rule.
        """
        res = super().write(vals)
        # Check if the purchase order was updated via a re-order rule
        # by checking for the 'from_orderpoint' key in the context.
        if self.env.context.get('from_orderpoint'):
            self._notify_procurement_team_on_RFQ_updation()
        return res



    def _notify_procurement_team_on_RFQ_updation(self):

        procurement_team = self.env['purchase.procurement.team'].search([])
        for user in procurement_team:
            self._schedule_activity(
                user.res_user,
                title="Updated RFQ from Reordering Rule",
                note=f"Please review the updated RFQ: <a href='/web#id={self.id}&model=purchase.order&view_type=form'>{self.name}</a>",
            )
            self._send_notification(
                user.res_user,
                title=f"Updated RFQ from Reordering Rule",
                message=f"A updated RFQ has been created from a reordering rule: {self.name}",
                type='info',
            )

    def _notify_procurement_team_on_RFQ_creation(self):

        procurement_team = self.env['purchase.procurement.team'].search([])
        for user in procurement_team:
            self._schedule_activity(
                user.res_user,
                title="New RFQ from Reordering Rule",
                note=f"Please review the RFQ: <a href='/web#id={self.id}&model=purchase.order&view_type=form'>{self.name}</a>",
            )
            self._send_notification(
                user.res_user,
                title=f"New RFQ from Reordering Rule",
                message=f"A new RFQ has been created from a reordering rule: {self.name}",
                type='info',
            )

    def _schedule_activity(record, user, title, note):
        record.activity_schedule(
            act_type_xmlid='mail.mail_activity_data_todo',
            summary=title,
            note=note,
            user_id=user.id,
            date_deadline=fields.Date.context_today(record),
        )

    def _send_notification(record, user, title, message, type='success'):
        record.env['bus.bus']._sendone(
            user.partner_id,
            'simple_notification',
            {
                'type': type,
                'title': title,
                'message': message,
                'sticky': True,
            },
        )
