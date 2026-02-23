import datetime
import io
import json
import logging
import operator
import os

import pytz
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo.http import content_disposition, request
from odoo.tools import pycompat
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug.exceptions import InternalServerError

from odoo import http
from odoo.addons.web.controllers.export import ExportXlsxWriter
from ..common_lib.ks_date_filter_selections import ks_get_date, ks_convert_into_local

_logger = logging.getLogger(__name__)


class KsListExport(http.Controller):

    def base(self, data):

        header, list_data = operator.itemgetter(
            'header',
            'chart_data',
        )(data)
        if not list_data or not list_data.get('columns', False):
            raise ValidationError("List data not present")

        columns_headers = [column_vals['field_description'] for column_vals in list_data['columns'].values()]
        import_data = []
        excel_fields = [{
            'type': 'float' if column_vals.get('ttype', False) == 'float' else ''
        } for column_vals in list_data['columns'].values()]

        for record in list_data.get('records', []):
            record_vals = [record_vals['value'] for record_vals in record['data'].values()]
            import_data.append(record_vals)

        lang_code = request.env.user.lang
        lang = request.env['res.lang']._lang_get(lang_code)

        if lang.direction == 'rtl':
            excel_fields, columns_headers, import_data =self.reverse_inner_index(excel_fields, columns_headers, import_data)
        return request.make_response(self.from_data(excel_fields, columns_headers, import_data),
                                     headers=[('Content-Disposition',
                                               content_disposition(self.filename(header))),
                                              ('Content-Type', self.content_type)],
                                     )

    def reverse_inner_index(self, columns, fields, data):
        reversed_columns = columns[::-1]
        reversed_fields = fields[::-1]
        reversed_data = [row[::-1] for row in data]
        return reversed_columns, reversed_fields, reversed_data


class KsListExcelExport(KsListExport, http.Controller):

    # Excel needs raw data to correctly handle numbers and date values
    raw_data = True

    @http.route('/ks_dashboard_ninja/export/list_xls', type='http', auth="user")
    def index(self, data):
        try:
            data = json.loads(data)
            record = request.env['ks_dashboard_ninja.item'].with_context(**data.get('context', {})).browse(
                data.get('res_id', False)
            )
            domain = data.get('domain', {})
            chart_data = record._ksGetListViewData(domain.get('ks_domain_1', []))
            data['chart_data'] = chart_data
            return self.base(data)
        except Exception as exc:
            _logger.exception("Exception during request handling.")
            payload = json.dumps({
                'code': 200,
                'message': "Odoo Server Error",
                'data': http.serialize_exception(exc)
            })
            raise InternalServerError(payload) from exc

    @property
    def content_type(self):
        return 'application/vnd.ms-excel'

    def filename(self, base):
        return base + '.xlsx'

    def from_data(self, fields, columns_headers, rows):
        with ExportXlsxWriter(fields, columns_headers, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value


class KsListCsvExport(KsListExport, http.Controller):

    @http.route('/ks_dashboard_ninja/export/list_csv', type='http', auth="user")
    def index(self, data):
        try:
            data = json.loads(data)
            record = request.env['ks_dashboard_ninja.item'].with_context(**data.get('context', {})).browse(
                data.get('res_id', False)
            )
            domain = data.get('domain', {})
            chart_data = record._ksGetListViewData(domain.get('ks_domain_1', []))
            data['chart_data'] = chart_data
            return self.base(data)
        except Exception as exc:
            _logger.exception("Exception during request handling.")
            payload = json.dumps({
                'code': 200,
                'message': "Odoo Server Error",
                'data': http.serialize_exception(exc)
            })
            raise InternalServerError(payload) from exc

    @property
    def content_type(self):
        return 'text/csv;charset=utf8'

    def filename(self, base):
        return base + '.csv'

    def from_data(self, fields, column_headers,rows):
        fp = io.BytesIO()
        writer = pycompat.csv_writer(fp, quoting=1)

        writer.writerow(column_headers)

        for data in rows:
            row = []
            for d in data:
                # Spreadsheet apps tend to detect formulas on leading =, + and -
                if isinstance(d, str)    and d.startswith(('=', '-', '+')):
                    d = "'" + d

                row.append(pycompat.to_text(d))
            writer.writerow(row)

        return fp.getvalue()
