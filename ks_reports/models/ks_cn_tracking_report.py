# -*- coding: utf-8 -*-

import io
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class KsCnTrackingReport(models.Model):
    _name = 'ks.cn.tracking.report'
    _description = 'CN Tracking'
    _order = 'cn_date desc, id desc'
    _rec_name = 'cn_no'

    date_generated = fields.Datetime(
        string='Generated On',
        default=fields.Datetime.now,
        readonly=True,
    )
    credit_note_id = fields.Many2one(
        comodel_name='account.move',
        string='Credit Note',
        ondelete='cascade',
        domain=[('move_type', '=', 'out_refund')],
        index=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Party Name',
        ondelete='set null',
        index=True,
    )

    # --- Proforma Invoice ---
    pi_no = fields.Char(string='Proforma Invoice No')
    pi_date = fields.Date(string='Proforma Invoice Date')
    pi_amount = fields.Float(string='PI Amount', digits=(16, 2))

    # --- Commercial Invoice ---
    commercial_invoice_no = fields.Char(string='Commercial Invoice No')
    commercial_invoice_date = fields.Date(string='Commercial Invoice Date')
    commercial_invoice_amount = fields.Float(string='Commercial Invoice Amount', digits=(16, 2))

    # --- Credit Note ---
    cn_date = fields.Date(string='CN Date')
    cn_no = fields.Char(string='CN No')
    cn_amount = fields.Float(string='CN Amount', digits=(16, 2))

    # --- Adjustment ---
    adjusted_pi_no = fields.Char(string='CN Adjusted Against PI No.')
    adjustment_amount = fields.Float(string='Adjustment Amount', digits=(16, 2))
    balance_cn = fields.Float(string='Balance CN', digits=(16, 2))

    # -------------------------------------------------------------------------
    # Auto-sync helpers
    # -------------------------------------------------------------------------

    @api.model
    def _sync_from_credit_note(self, cn):
        """
        Create or update ks.cn.tracking.report records for the given Credit Note.
        One record per tracking row (one per PI-CN combination).
        Only runs for posted Credit Notes.
        """
        if not cn or cn.move_type != 'out_refund' or cn.state != 'posted':
            return

        rows = self.env['ks.part.wise.all.data.report']._build_cn_tracking_rows(
            credit_note_ids=[cn.id]
        )

        # Delete all existing rows for this CN, then recreate
        self.search([('credit_note_id', '=', cn.id)]).unlink()

        now = fields.Datetime.now()
        for row in rows:
            self.create(dict(
                row,
                credit_note_id=cn.id,
                partner_id=cn.partner_id.id if cn.partner_id else False,
                date_generated=now,
            ))

    # -------------------------------------------------------------------------
    # XLSX export
    # -------------------------------------------------------------------------

    def action_export_xlsx(self):
        """Export selected records to XLSX. If none selected, exports all records."""
        records = self if self else self.search([])
        if xlsxwriter is None:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#FFFF00', 'border': 1,
            'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
        })
        data_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        num_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': '#,##0.00'})
        date_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'num_format': 'dd-mmm-yy'})

        headers = [
            'PROFORMA INVOICE NO', 'PROFORMA INVOICE DATE', 'PI AMOUNT',
            'COMMERCIAL INVOICE NO', 'COMMERCIAL INVOICE DATE', 'COMMERCIAL INVOICE AMOUNT',
            'CN DATE', 'CN NO', 'CN AMOUNT',
            'CN Adjusted Against PI No.', 'Adjustment Amount', 'Balance CN',
        ]
        col_widths = [25, 20, 18, 25, 20, 25, 18, 20, 18, 25, 20, 18]

        sheet = workbook.add_worksheet('CN Tracking')
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_fmt)
        for col, width in enumerate(col_widths):
            sheet.set_column(col, col, width)
        sheet.freeze_panes(1, 0)

        for row_idx, rec in enumerate(records, start=1):
            sheet.write(row_idx, 0, rec.pi_no or '', data_fmt)
            sheet.write(row_idx, 1, rec.pi_date or '', date_fmt if rec.pi_date else data_fmt)
            sheet.write(row_idx, 2, rec.pi_amount or 0.0, num_fmt)
            sheet.write(row_idx, 3, rec.commercial_invoice_no or '', data_fmt)
            sheet.write(row_idx, 4, rec.commercial_invoice_date or '', date_fmt if rec.commercial_invoice_date else data_fmt)
            sheet.write(row_idx, 5, rec.commercial_invoice_amount or 0.0 if rec.commercial_invoice_no else '', num_fmt if rec.commercial_invoice_no else data_fmt)
            sheet.write(row_idx, 6, rec.cn_date or '', date_fmt if rec.cn_date else data_fmt)
            sheet.write(row_idx, 7, rec.cn_no or '', data_fmt)
            sheet.write(row_idx, 8, rec.cn_amount or 0.0 if rec.cn_no else '', num_fmt if rec.cn_no else data_fmt)
            sheet.write(row_idx, 9, rec.adjusted_pi_no or '', data_fmt)
            sheet.write(row_idx, 10, rec.adjustment_amount or 0.0 if rec.cn_no else '', num_fmt if rec.cn_no else data_fmt)
            sheet.write(row_idx, 11, rec.balance_cn or 0.0 if rec.cn_no else '', num_fmt if rec.cn_no else data_fmt)

        workbook.close()
        output.seek(0)
        content = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'CN_Tracking_Export.xlsx',
            'type': 'binary',
            'datas': content,
            'res_model': self._name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
