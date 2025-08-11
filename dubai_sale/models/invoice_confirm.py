from odoo import fields, models


class ShowPaymentButtonToAccountsGroup(models.Model):
    _inherit='account.move'

    def action_post(self):
        super(ShowPaymentButtonToAccountsGroup, self).action_post()

        if self.env.context.get('active_model') != 'sale.advance.payment.inv':
            # can show a notification here
            return

        sales_account_group = self.env.ref('dubai_sale.account_group_for_sales')

        if sales_account_group:
            users_in_group = sales_account_group.users

            for user in users_in_group:

                self.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary = f'Invoice {self.name} is now ready for payment.',
                    note="You have been assigned to unlock this PI.",
                    user_id=user.id,
                    date_deadline=fields.Date.context_today(self),
                )

                self.env['bus.bus']._sendone(
                    user.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'Invoice {self.name} generated for payment.',
                        'message':  f'Activity assigned to you.',
                        'sticky': True,
                    },
                )



    