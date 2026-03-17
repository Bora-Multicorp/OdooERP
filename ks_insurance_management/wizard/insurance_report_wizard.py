# -*- coding: utf-8 -*-

import io
import base64
from datetime import date

from odoo import fields, models, _
from odoo.exceptions import UserError


# Map report_type to (xml_id, report_name) for fallback lookup
REPORT_ACTIONS = {
    'fire_burglary': (
        'ks_insurance_management.action_report_fire_burglary',
        'ks_insurance_management.report_fire_burglary_template',
    ),
    'marine': (
        'ks_insurance_management.action_report_marine',
        'ks_insurance_management.report_marine_template',
    ),
    'misc': (
        'ks_insurance_management.action_report_misc',
        'ks_insurance_management.report_misc_template',
    ),
}

MARINE_APPLICABILITY_LABELS = {
    'exim': 'EXIM',
    'domestic': 'Domestic',
    'both': 'Both',
    'russia': 'Russia Only',
}


class InsuranceReportWizard(models.TransientModel):
    _name = 'insurance.report.wizard'
    _description = 'Insurance Report Wizard'

    date_from = fields.Date(
        string='Active From',
        help='Filter policies whose coverage period starts on or after this date. '
             'Leave empty to include all policies regardless of start date.',
    )
    date_to = fields.Date(
        string='Active To',
        help='Filter policies whose expiry date is on or before this date. '
             'Leave empty to include all policies regardless of expiry date.',
    )
    company_ids = fields.Many2many(
        'res.company',
        string='Companies',
        default=lambda self: self.env.company,
        help='Select one or more companies to include in the report. '
             'Leave empty to include policies from all companies.',
    )
    report_type = fields.Selection([
        ('fire_burglary', 'Fire & Burglary'),
        ('marine', 'Marine'),
        ('misc', 'Miscellaneous'),
    ], string='Report Type', default='fire_burglary',
        help='Fire & Burglary: shows all active F&B policies with inventory values.\n'
             'Marine: shows all active Marine policies with balance sum insured and declaration count.\n'
             'Miscellaneous: shows all other policies (GMC, GPA, Vehicle, Personal, etc.).',
    )
    include_expired = fields.Boolean(
        string='Include Expired Policies',
        default=False,
        help='When checked, expired policies will also appear in the report alongside active ones. '
             'Useful for historical analysis or audit purposes.',
    )

    def _get_policies(self):
        domain = []
        if not self.include_expired:
            domain.append(('state', '=', 'active'))
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if self.report_type == 'fire_burglary':
            domain.append(('is_fire_burglary', '=', True))
        elif self.report_type == 'marine':
            domain.append(('is_marine', '=', True))
        elif self.report_type == 'misc':
            domain.append(('is_misc', '=', True))
        if self.date_from:
            domain.append(('expiry_date', '>=', self.date_from))
        if self.date_to:
            domain += ['|', ('start_date', '<=', self.date_to), ('start_date', '=', False)]
        return self.env['insurance.policy'].search(domain, order='company_id, insurance_type_id')

    # ─── PDF ────────────────────────────────────────────────────────────────────

    def _get_report_action(self, report_type):
        xml_id, report_name = REPORT_ACTIONS[report_type]
        report = self.env.ref(xml_id, raise_if_not_found=False)
        if not report or report._name != 'ir.actions.report':
            report = self.env['ir.actions.report'].search(
                [('report_name', '=', report_name)], limit=1
            )
        if not report:
            raise UserError(
                _('Report "%s" not found. Please upgrade the Insurance Management module.')
                % report_name
            )
        return report.report_action(self)

    def action_print_fire_burglary(self):
        self.report_type = 'fire_burglary'
        return self._get_report_action('fire_burglary')

    def action_print_marine(self):
        self.report_type = 'marine'
        return self._get_report_action('marine')

    def action_print_misc(self):
        self.report_type = 'misc'
        return self._get_report_action('misc')

    # ─── XLSX ───────────────────────────────────────────────────────────────────

    def _build_xlsx(self, report_type):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_(
                'xlsxwriter is not installed. Run: pip install xlsxwriter'
            ))

        policies = self._get_policies()
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})

        # ── shared formats ────────────────────────────────────────────────────
        title_fmt = wb.add_format({
            'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter',
            'font_color': '#1F3864',
        })
        sub_fmt = wb.add_format({
            'italic': True, 'font_size': 9, 'align': 'center', 'font_color': '#666666',
        })
        hdr_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1F3864', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True,
        })
        cell_fmt = wb.add_format({'border': 1, 'valign': 'vcenter'})
        center_fmt = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        num_fmt = wb.add_format({'border': 1, 'num_format': '#,##0.00', 'valign': 'vcenter'})
        pct_fmt = wb.add_format({'border': 1, 'num_format': '0.00"%"', 'valign': 'vcenter', 'align': 'center'})
        active_fmt = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter',
                                    'font_color': '#1A7431', 'bold': True})
        expired_fmt = wb.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter',
                                     'font_color': '#C00000', 'bold': True})

        today_str = date.today().strftime('%d/%m/%Y')
        companies_str = ', '.join(self.company_ids.mapped('name')) if self.company_ids else 'All Companies'

        def _write_header(ws, title, headers, col_widths, num_cols):
            ws.merge_range(0, 0, 0, num_cols - 1, title, title_fmt)
            ws.set_row(0, 22)
            sub = f'Companies: {companies_str}   |   Generated: {today_str}'
            if self.date_from or self.date_to:
                sub += f'   |   Period: {self.date_from or ""} – {self.date_to or ""}'
            ws.merge_range(1, 0, 1, num_cols - 1, sub, sub_fmt)
            ws.write_row(2, 0, headers, hdr_fmt)
            ws.set_row(2, 20)
            for col, width in enumerate(col_widths):
                ws.set_column(col, col, width)
            return 3  # first data row

        def _state_fmt(ws, row, col, state):
            fmt = active_fmt if state == 'active' else expired_fmt
            ws.write(row, col, state.upper(), fmt)

        # ── Fire & Burglary ───────────────────────────────────────────────────
        if report_type == 'fire_burglary':
            ws = wb.add_worksheet('Fire & Burglary')
            headers = [
                'Sr.', 'Policy No.', 'Type', 'Company', 'Insurer',
                'Sum Insured (₹)', 'Premium (₹)', 'Premium %',
                'Avg Inventory (₹)', 'Expiry Date', 'Status',
            ]
            widths = [5, 18, 22, 22, 22, 18, 16, 11, 18, 13, 10]
            start = _write_header(ws, 'Fire & Burglary Insurance Report', headers, widths, len(headers))
            for i, p in enumerate(policies, 1):
                r = start + i - 1
                ws.write(r, 0, i, center_fmt)
                ws.write(r, 1, p.policy_number or '-', cell_fmt)
                ws.write(r, 2, p.insurance_type_id.name or '-', cell_fmt)
                ws.write(r, 3, p.company_id.name, cell_fmt)
                ws.write(r, 4, p.insurance_company_id.name, cell_fmt)
                ws.write(r, 5, p.sum_insured, num_fmt)
                ws.write(r, 6, p.premium, num_fmt)
                ws.write(r, 7, p.premium_percentage, pct_fmt)
                ws.write(r, 8, p._get_avg_inventory(), num_fmt)
                ws.write(r, 9, str(p.expiry_date) if p.expiry_date else '-', center_fmt)
                _state_fmt(ws, r, 10, p.state)

        # ── Marine ────────────────────────────────────────────────────────────
        elif report_type == 'marine':
            ws = wb.add_worksheet('Marine')
            headers = [
                'Sr.', 'Policy No.', 'Applicability', 'Company', 'Insurer',
                'Sum Insured (₹)', 'Premium (₹)', 'Premium %',
                'Balance Sum Insured (₹)', 'Expiry Date', 'Status',
                'Declarations', 'Remarks',
            ]
            widths = [5, 18, 14, 22, 22, 18, 16, 11, 22, 13, 10, 13, 22]
            start = _write_header(ws, 'Marine Insurance Report', headers, widths, len(headers))
            for i, p in enumerate(policies, 1):
                r = start + i - 1
                applicability = MARINE_APPLICABILITY_LABELS.get(
                    p.insurance_type_id.marine_applicability, '-'
                )
                ws.write(r, 0, i, center_fmt)
                ws.write(r, 1, p.policy_number or '-', cell_fmt)
                ws.write(r, 2, applicability, center_fmt)
                ws.write(r, 3, p.company_id.name, cell_fmt)
                ws.write(r, 4, p.insurance_company_id.name, cell_fmt)
                ws.write(r, 5, p.sum_insured, num_fmt)
                ws.write(r, 6, p.premium, num_fmt)
                ws.write(r, 7, p.premium_percentage, pct_fmt)
                ws.write(r, 8, p.balance_sum_insured, num_fmt)
                ws.write(r, 9, str(p.expiry_date) if p.expiry_date else '-', center_fmt)
                _state_fmt(ws, r, 10, p.state)
                ws.write(r, 11, len(p.declaration_ids), center_fmt)
                ws.write(r, 12, '', cell_fmt)

        # ── Miscellaneous ─────────────────────────────────────────────────────
        elif report_type == 'misc':
            ws = wb.add_worksheet('Miscellaneous')
            headers = [
                'Sr.', 'Policy No.', 'Type', 'Category', 'Company', 'Insurer',
                'Agent', 'Sum Insured (₹)', 'Premium (₹)', 'Premium %',
                'Expiry Date', 'Status',
            ]
            widths = [5, 18, 22, 16, 22, 22, 18, 18, 16, 11, 13, 10]
            start = _write_header(ws, 'Miscellaneous Insurance Report', headers, widths, len(headers))
            for i, p in enumerate(policies, 1):
                r = start + i - 1
                ws.write(r, 0, i, center_fmt)
                ws.write(r, 1, p.policy_number or '-', cell_fmt)
                ws.write(r, 2, p.insurance_type_id.name or '-', cell_fmt)
                ws.write(r, 3, p.insurance_category_id.name or '-', cell_fmt)
                ws.write(r, 4, p.company_id.name, cell_fmt)
                ws.write(r, 5, p.insurance_company_id.name, cell_fmt)
                ws.write(r, 6, p.agent_id.name or '-', cell_fmt)
                ws.write(r, 7, p.sum_insured, num_fmt)
                ws.write(r, 8, p.premium, num_fmt)
                ws.write(r, 9, p.premium_percentage, pct_fmt)
                ws.write(r, 10, str(p.expiry_date) if p.expiry_date else '-', center_fmt)
                _state_fmt(ws, r, 11, p.state)

        wb.close()
        output.seek(0)
        return output.read()

    def _download_xlsx(self, report_type, filename):
        xlsx_data = self._build_xlsx(report_type)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_download_fire_burglary_xlsx(self):
        self.report_type = 'fire_burglary'
        return self._download_xlsx('fire_burglary', 'Fire_Burglary_Insurance_Report.xlsx')

    def action_download_marine_xlsx(self):
        self.report_type = 'marine'
        return self._download_xlsx('marine', 'Marine_Insurance_Report.xlsx')

    def action_download_misc_xlsx(self):
        self.report_type = 'misc'
        return self._download_xlsx('misc', 'Miscellaneous_Insurance_Report.xlsx')
