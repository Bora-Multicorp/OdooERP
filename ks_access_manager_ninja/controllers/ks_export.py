# -*- coding: utf-8 -*-

import io
import logging

from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.misc import xlsxwriter

from odoo.addons.web.controllers.export import ExportXlsxWriter

_logger = logging.getLogger(__name__)


class InheritExportXlsxWriter(ExportXlsxWriter):
    def __init__(self, fields, columns_headers, row_count, env=None):
        self.fields = fields
        self.columns_headers = columns_headers
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.header_style = self.workbook.add_format({'bold': True})
        self.date_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd'})
        self.datetime_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.base_style = self.workbook.add_format({'text_wrap': True})
        self.float_style = self.workbook.add_format({'text_wrap': True, 'num_format': '#,##0.00'})

        if env:
            decimal_places = env['res.currency']._read_group([], aggregates=['decimal_places:max'])[0][0]
        else:
            decimal_places = request.env['res.currency']._read_group([], aggregates=['decimal_places:max'])[0][0]
        self.monetary_style = self.workbook.add_format(
            {'text_wrap': True, 'num_format': f'#,##0.{(decimal_places or 2) * "0"}'})

        header_bold_props = {'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'}
        self.header_bold_style = self.workbook.add_format(header_bold_props)
        self.header_bold_style_float = self.workbook.add_format(dict(**header_bold_props, num_format='#,##0.00'))
        self.header_bold_style_monetary = self.workbook.add_format(
            dict(**header_bold_props, num_format=f'#,##0.{(decimal_places or 2) * "0"}'))

        self.worksheet = self.workbook.add_worksheet()
        self.value = False

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(request.env._(
                'There are too many rows (%(count)s rows, limit: %(limit)s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.',
                count=row_count, limit=self.worksheet.xls_rowmax))
