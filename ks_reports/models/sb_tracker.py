# -*- coding: utf-8 -*-

import io
import base64
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class SbTracker(models.Model):
    _name = 'sb.tracker'
    _description = 'SB Tracker'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Sr No',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Party Name',
        ondelete='set null',
    )
    document_type = fields.Char(
        string='Document Type',
        default='Sales Invoice',
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice No',
        domain=[('move_type', '=', 'out_invoice')],
        ondelete='set null',
    )
    invoice_date = fields.Date(string='Invoice Date')
    shipping_no = fields.Char(string='SB No')
    shipping_date = fields.Date(string='SB Date')
    forex_amount = fields.Float(string='Value', digits=(16, 2))
    exchange_rate = fields.Float(string='Ex Rate', digits=(16, 6))
    inr_amount = fields.Float(string='Amount INR', digits=(16, 2))
    brc_date = fields.Date(string='BRC Date')
    brc_no = fields.Char(string='BRC No')
    brc_amount = fields.Float(string='BRC Amount', digits=(16, 2))
    bank_id = fields.Many2one(
        'res.bank',
        string='Bank',
        ondelete='set null',
    )
    ad_code = fields.Char(string='AD Code')
    bank_updation_status = fields.Text(string='Bank Updation Status')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('sb.tracker')
                    or _('New')
                )
        return super().create(vals_list)

    def _update_from_invoice(self, invoice):
        """Update tracker fields from account.move (invoice)."""
        self.ensure_one()
        vals = {
            'partner_id': invoice.partner_id.id,
            'invoice_date': invoice.invoice_date,
            'forex_amount': invoice.amount_total or 0.0,
        }
        bank_id = getattr(invoice, 'ks_bank_id', None)
        if bank_id:
            vals['bank_id'] = bank_id.id
            ad_code = getattr(bank_id, 'bank_ad_code', None)
            if ad_code:
                vals['ad_code'] = ad_code
        self.write(vals)

    def _update_from_sb_brc_master(self, master):
        """Update tracker fields from sb.brc.master."""
        self.ensure_one()
        self.write({
            'shipping_no': master.sb_no or '',
            'shipping_date': master.sb_date,
            'exchange_rate': master.sb_ex_rate or master.ex_rate or 0.0,
            'inr_amount': master.amount_inr or 0.0,
            'brc_date': master.brc_date,
            'brc_no': master.brc_no or '',
            'brc_amount': master.brc_amount_usd or 0.0,
        })

    def action_export_xlsx(self):
        """Export selected records to XLSX. Used as top action from list view."""
        if not self:
            raise UserError(_('Please select at least one record to export.'))
        if xlsxwriter is None:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))
        content = self._generate_xlsx_report()
        filename = 'SB_Tracker_Export.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': content,
            'res_model': 'sb.tracker',
            'res_id': 0,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }

    def _generate_xlsx_report(self):
        """Generate XLSX file content (base64) for current recordset."""
        # Use datetime.date.min as a sentinel so that records with no
        # invoice_date sort first without mixing date and str types, which
        # would raise: TypeError: '<' not supported between instances of
        # 'datetime.date' and 'str'.
        records = self.sorted(key=lambda r: (r.invoice_date or datetime.date.min, r.id))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('SB Tracker')

        header_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D3D3D3',
            'text_wrap': True,
        })
        data_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        number_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })

        headers = [
            'Sr No', 'Party Name', 'Document Type', 'Invoice No', 'Invoice Date',
            'SB No', 'SB Date', 'Value', 'Ex Rate', 'Amount INR',
            'BRC Date', 'BRC No', 'BRC Amount', 'Bank', 'AD Code',
            'Bank Updation Status',
        ]
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_fmt)

        for row_idx, rec in enumerate(records):
            row_vals = [
                rec.name or '',
                rec.partner_id.name if rec.partner_id else '',
                rec.document_type or '',
                rec.invoice_id.name if rec.invoice_id else '',
                rec.invoice_date.strftime('%Y-%m-%d') if rec.invoice_date else '',
                rec.shipping_no or '',
                rec.shipping_date.strftime('%Y-%m-%d') if rec.shipping_date else '',
                rec.forex_amount,
                rec.exchange_rate,
                rec.inr_amount,
                rec.brc_date.strftime('%Y-%m-%d') if rec.brc_date else '',
                rec.brc_no or '',
                rec.brc_amount,
                rec.bank_id.name if rec.bank_id else '',
                rec.ad_code or '',
                (rec.bank_updation_status or '')[:32767],
            ]
            for col, val in enumerate(row_vals):
                fmt = number_fmt if col in (7, 8, 9, 12) and isinstance(val, (int, float)) else data_fmt
                sheet.write(row_idx + 1, col, val, fmt)

        widths = [10, 22, 14, 14, 12, 14, 12, 12, 10, 12, 12, 12, 12, 18, 14, 22]
        for col, w in enumerate(widths):
            sheet.set_column(col, col, w)

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.getvalue())
