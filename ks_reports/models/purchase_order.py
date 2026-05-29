# -*- coding: utf-8 -*-

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def create(self, vals_list):
        orders = super().create(vals_list)
        if orders:
            self.env['ks.purchase.report.detail'].action_sync_po_data(purchase_orders=orders)
        return orders

    def write(self, vals):
        res = super().write(vals)
        if res and self:
            self.env['ks.purchase.report.detail'].action_sync_po_data(purchase_orders=self)
        return res

    def action_sync_to_report(self):
        """Sync this PO (or selected POs) to ks.purchase.report.detail."""
        self.env['ks.purchase.report.detail'].action_sync_po_data(purchase_orders=self)
        return True

    # Extra PO fields (Other Info tab)
    ks_remarks = fields.Char(string='Remarks')
    ks_invoice = fields.Char(string='Invoice')
    ks_e_invoices = fields.Char(string='E - Invoices')
    ks_e_way_bill = fields.Char(string='E-way Bill')
    ks_imei_serial_no = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='IMEI/ Serial No',
        required=True,
        default='no',
    )
    ks_docket = fields.Char(string='DOCKET')
    ks_ewaybill_no = fields.Char(string='EWAYBILL NO')
    ks_docket_no = fields.Char(string='DOCKET No')
    ks_vehicle_no = fields.Char(string='Vehicle No.')
    ks_transporter = fields.Char(string='TRANSPORTER')
