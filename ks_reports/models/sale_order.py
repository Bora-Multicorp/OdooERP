# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_print_sheet_2_report(self):
        """
        Action button method to generate and download Sheet 2 report
        This method is called from the Sale Order form view action button
        """
        self.ensure_one()
        
        # Check if order is confirmed
        if self.state not in ['sale', 'done']:
            raise UserError('This report is only available for confirmed Sale Orders.')
        
        # Generate report for this specific sale order
        report_model = self.env['ks.part.wise.all.data.report']
        file_content = report_model.generate_sheet_2_xlsx_report(sale_order_ids=[self.id])
        
        # Create attachment to store the file
        attachment = self.env['ir.attachment'].create({
            'name': f'Sheet_2_Report_{self.name}.xlsx',
            'type': 'binary',
            'datas': file_content,
            'res_model': 'sale.order',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment.id) + '?download=true',
            'target': 'self',
        }

