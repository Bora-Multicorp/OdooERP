from odoo import models, api, fields, _, sql_db
from odoo.exceptions import ValidationError
from psycopg2 import ProgrammingError
from dateutil import relativedelta
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.ks_dashboard_ninja.common_lib.ks_date_filter_selections import ks_get_date, ks_convert_into_utc, \
    ks_convert_into_local
from datetime import datetime
from dateutil.parser import parse
import json
import psycopg2
import mysql.connector
import requests



class KsDashboardNinjaItemAdvance(models.Model):
    _inherit = 'ks_dashboard_ninja.item'

    ks_custom_query = fields.Text(string="Custom Query",
                                  help=' Fetch, combine, and compare data by generating SQL query on your own.')
    ks_data_calculation_type = fields.Selection([('custom', 'Default Query'),
                                                 ('query', 'Custom Query')], string="Data Calculation Type",
                                                default="custom")
    ks_query_result = fields.Char(compute='ks_run_query', string="Result")
    ks_xlabels = fields.Char(string="X-Labels")
    ks_ylabels = fields.Char(string="Y-Labels")
    ks_model_id = fields.Many2one('ir.model', string='Model', required=False,
                                  domain="[('access_ids','!=',False),('transient','=',False),"
                                         "('model','not ilike','base_import%'),'|',('model','not ilike','ir.%'),('model','=ilike','_%ir.%'),"
                                         "('model','not ilike','web_editor.%'),('model','not ilike','web_tour.%'),"
                                         "('model','!=','mail.thread'),('model','not ilike','ks_dash%'), ('model','not ilike','ks_to%')]")

    ks_list_view_layout = fields.Selection([('layout_1', 'Default layout'),
                                            ('layout_2', 'Layout 1'),
                                            ('layout_3', 'Layout 2'),
                                            ('layout_4', 'Layout 3')], string="List View Layout",
                                           default="layout_1")

    ks_is_date_ranges = fields.Boolean('Date Ranges',
                                       help=' Checkbox to apply default date range filter. The date filter applied will also reflect on the main page.')
    ks_query_start_date = fields.Datetime()
    ks_query_end_date = fields.Datetime()
    ks_is_external_db = fields.Boolean(string="External Database")
    ks_external_db_type = fields.Selection([('ks_postgres', 'Postgres DB'), ('ks_sql', 'MYSQL DB')],
                                           string="Type of External DB")
    ks_host = fields.Char(string="Host" ,help="database server address e.g.,localhost or an IP address.")
    ks_db_name = fields.Char(string="Database Name", help=" the name of the database that you want to connect.")
    ks_db_password = fields.Char(string="Password", help="password used to authenticate db.")
    ks_db_user = fields.Char(string="Database User", help="the username used to authenticate db.")
    ks_port = fields.Char(string="Port", help="the port number that defaults to 5432(postgres) and 3306(MYSQL) if it is not provided")
    ks_is_external_api = fields.Boolean(string="External API")
    ks_url = fields.Char(string="URL")
    ks_api_header = fields.Text(string="API header")
    ks_api_data_lines = fields.One2many('ks.dashboard.api', 'ks_dashboard_datatype_id', string=" Data-Type Lines")
    data_source = fields.Selection(selection_add=[('external_api', 'External API')])

    @api.onchange('data_source')
    def make_invisible(self):
        if self.data_source == 'excel':
            self.excel_bool = True
            self.model_bool = False
            self.csv_bool = False
            self.ks_is_external_api = False
        elif self.data_source == 'odoo':
            self.model_bool = True
            self.excel_bool = False
            self.csv_bool = False
            self.ks_is_external_api = False
        elif self.data_source == 'csv':
            self.csv_bool = True
            self.model_bool = False
            self.excel_bool = False
            self.ks_is_external_api = False
        elif self.data_source == 'external_api':
            self.csv_bool = False
            self.model_bool = False
            self.excel_bool = False
            self.ks_is_external_api = True
        else:
            self.model_bool = False
            self.excel_bool = False
            self.csv_bool = False
            self.ks_is_external_api = False

    @api.onchange('ks_url', 'ks_api_header')
    def ks_get_data_from_api(self):
        try:
            if self.ks_url and self.ks_api_header:
                header = json.loads("".join(self.ks_api_header.split()))
                ks_api_response = requests.get(self.ks_url, headers=header)
                if ks_api_response.status_code == 200:
                    data = ks_api_response.json()
                    data_key = data['data'][0].keys()
                    self.ks_api_data_lines = [(5, 0, 0)]
                    for rec in data_key:
                        self.write({
                            'ks_api_data_lines': [(0, 0, {
                                'name': rec
                            })]
                        })
                    self.ks_model_id = False
                else:
                    raise ValidationError(_("API Responds with the following status %s") % ks_api_response.status_code)
            else:
                self.ks_api_data_lines = [(5, 0, 0)]
        except Exception as e:
            raise ValidationError(_("Please request to API that generates response in format  {'data':[{...},{...},]}"))


    def api_create_table(self):
            tablemodel = 'x_' + 'usa.data_' + self.name_seq
            tablename = 'usa_data' + self.name_seq
            ks_api_model = self.env['ir.model'].search([('model', '=', tablemodel)])
            if ks_api_model:
                self.ks_model_id = ks_api_model.id
            else:
                if self.ks_api_data_lines:
                    values = []
                    for rec in self.ks_api_data_lines:
                        ks_dict = {}
                        if not rec.ttype:
                            raise ValidationError('Please Enter the type under Column Data Type Tab')
                        ks_dict['name'] = rec.name.lower().replace(' ', '_')
                        ks_dict['type'] = rec.ttype
                        values.append(ks_dict)

                    model_creation = self.env['ir.model'].sudo().create({
                        'name': tablename,
                        'model': tablemodel,
                        'order': 'x_name asc, id desc',  # valid order
                    })
                    self.ks_model_id = model_creation.id
                    for value in values:
                        column_name = value.get('name')
                        column_type = value.get('type')
                        model_creation.write({
                            'field_id': [(0, 0, {
                                'name': 'x_' + column_name,
                                'ttype': column_type,
                                'field_description': column_name.replace('_', ' ')
                            })]
                        })
                    self.env['ir.model.access'].sudo().create({
                        'name': model_creation.name + ' all_user',
                        'model_id': model_creation.id,
                        'perm_read': True,
                        'perm_write': True,
                        'perm_create': True,
                        'perm_unlink': True,
                    })

                    if self.ks_url and self.ks_api_header:
                        header = json.loads("".join(self.ks_api_header.split()))
                        ks_api_response = requests.get(self.ks_url,headers=header)
                        if ks_api_response.status_code == 200:
                            data = ks_api_response.json()
                            ks_new_data = []
                            for ks_item in data['data']:
                                ks_new_dict = {}
                                for key, value in ks_item.items():
                                    new_key = 'x_' + key.lower().replace(' ', '_')
                                    if (self.env['ir.model.fields'].search(
                                            [('model', '=', tablemodel), ('name', '=', new_key)])).ttype == "date":
                                        try:
                                            # Try to parse the date string as a full date
                                            ks_new_dict[new_key] = datetime.strptime(str(value), "%Y-%m-%d")
                                        except ValueError:
                                            try:
                                                # Try to parse the date string as a year and month
                                                ks_new_dict[new_key] = datetime.strptime(str(value), "%Y-%m")
                                            except ValueError:
                                                try:
                                                    # Try to parse the date string as a year
                                                    ks_new_dict[new_key] = datetime.strptime(str(value), "%Y")
                                                except ValueError:
                                                    ks_new_dict[new_key] = None
                                    else:
                                        ks_new_dict[new_key] = value
                                ks_new_data.append(ks_new_dict)

                            for ks_item in ks_new_data:
                                try:
                                    self.env[tablemodel].create(ks_item)
                                except Exception as e:
                                    raise ValidationError(_("%s. Please enter correct data-type of item") %e)
                        else:
                            raise ValidationError(
                                _("API Responds with the following status %s") % ks_api_response.status_code)
                    else:
                        raise ValidationError(_("Please Enter correct Url"))
                else:
                    self.ks_api_data_lines = [(5, 0, 0)]



    @api.depends('ks_record_count_type', 'ks_model_id', 'ks_domain', 'ks_record_field', 'ks_date_filter_field',
                 'ks_item_end_date', 'ks_item_start_date', 'ks_compare_period', 'ks_year_period',
                 'ks_dashboard_item_type', 'ks_domain_extension', 'ks_data_format', 'ks_custom_query')
    def ks_get_record_count(self):
        for rec in self:
            rec.ks_record_count = rec._ksGetRecordCount(domain=[])

    def _ksGetRecordCount(self, domain=[]):
        for rec in self:
            if rec.ks_dashboard_item_type and rec.ks_dashboard_item_type == 'ks_kpi' and rec.ks_data_calculation_type == 'query' and rec.ks_query_result:
                ks_kpi_data = json.loads(rec.ks_query_result)
                ks_data_list = [{'record_field': False, 'record_data': 0, 'model': False}]
                ks_data_list[0]['record_data'] = list(ks_kpi_data.values())[0]
                # TODO: adding try catch bcz flow is not working properly for Strings
                try:
                    float(ks_data_list[0]['record_data'])
                except Exception:
                    raise ValidationError(_("Cannot Convert query result to float"))

                return ks_data_list[0]['record_data']
            else:
                result = super(KsDashboardNinjaItemAdvance, self)._ksGetRecordCount(domain)

            return result

    @api.depends('ks_chart_measure_field', 'ks_map_record_field', 'ks_funnel_record_field', 'ks_chart_cumulative_field', 'ks_chart_relation_groupby',
                 'ks_chart_date_groupby', 'ks_domain', 'ks_dashboard_item_type', 'ks_model_id', 'ks_sort_by_field', 'ks_sort_by_order',
                 'ks_record_data_limit', 'ks_chart_data_count_type', 'ks_chart_measure_field_2', 'ks_goal_enable',
                 'ks_standard_goal_value', 'ks_goal_bar_line', 'ks_chart_relation_sub_groupby', 'ks_chart_date_sub_groupby',
                 'ks_date_filter_field', 'ks_item_start_date', 'ks_item_end_date', 'ks_compare_period', 'ks_year_period',
                 'ks_unit', 'ks_unit_selection', 'ks_chart_unit', 'ks_fill_temporal', 'ks_domain_extension', 'ks_multiplier_active',
                 'ks_multiplier_lines', 'ks_scatter_measure_x_id', 'ks_scatter_measure_y_id',
                 'ks_custom_query', 'ks_data_calculation_type', 'ks_query_result', 'ks_xlabels', 'ks_ylabels',
                 'ks_bar_chart_stacked')
    def ks_get_chart_data(self):
        for rec in self:
            if rec.ks_dashboard_item_type == "ks_funnel_chart":
                rec.ks_sort_by_order = "DESC"
                rec.ks_sort_by_field = rec.ks_funnel_record_field
                rec.ks_chart_measure_field = rec.ks_funnel_record_field
                rec.ks_chart_data = rec._ks_get_chart_data(domain=[])
            elif rec.ks_dashboard_item_type == "ks_map_view":
                rec.ks_chart_measure_field = rec.ks_map_record_field
                rec.ks_chart_relation_groupby = rec.ks_map_chart_relation_groupby
                rec.ks_chart_data = rec._ks_get_chart_data(domain=[])
            elif rec.ks_dashboard_item_type == "ks_scatter_chart":
                rec.ks_chart_relation_groupby  = rec.ks_scatter_measure_x_id
                # rec.ks_chart_relation_groupby = rec.ks_scatter_measure_y_id
                rec.ks_chart_data = rec._ks_get_chart_data(domain=[])
            else:
                rec.ks_chart_data = rec._ks_get_chart_data(domain=[])

    def _ks_get_chart_data(self, domain=[]):
        for rec in self:
            if rec.ks_dashboard_item_type and rec.ks_dashboard_item_type not in ['ks_tile', 'ks_list_view', 'ks_kpi']:
                if rec.ks_data_calculation_type != 'query':
                    return super(KsDashboardNinjaItemAdvance, self)._ks_get_chart_data(domain)
                else:
                    if rec.ks_query_result:
                        records = json.loads(rec.ks_query_result)
                        ks_chart_data = {'labels': [], 'domains': [], 'datasets': [],
                                         'ks_data_calculation_type': rec.ks_data_calculation_type,
                                         'ks_show_data_value': rec.ks_show_data_value,
                                         'ks_dashboard_item_type': rec.ks_dashboard_item_type,
                                         'ks_show_records': rec.ks_show_records,
                                         'ks_data_format': rec.ks_data_format,
                                         'ks_chart_item_color': rec.ks_chart_item_color,
                                         'ks_bar_chart_stacked': rec.ks_bar_chart_stacked,
                                         'ks_semi_circle_chart': rec.ks_semi_circle_chart,
                                         'ks_hide_legend': rec.ks_hide_legend,
                                         'ks_data_label_type': rec.ks_data_label_type,
                                         'ks_chart_measure_field_2': rec.ks_chart_measure_field_2.ids,
                                         'ks_chart_cumulative_field': rec.ks_chart_cumulative_field.ids,
                                         }
                        if records:
                            if rec.ks_unit and rec.ks_unit_selection == 'monetary':
                                ks_chart_data['ks_selection'] = rec.ks_unit_selection
                                ks_chart_data['ks_currency'] = rec.env.user.company_id.currency_id.id
                            elif rec.ks_unit and rec.ks_unit_selection == 'custom':
                                ks_chart_data['ks_selection'] = rec.ks_unit_selection
                                if rec.ks_chart_unit:
                                    ks_chart_data['ks_field'] = rec.ks_chart_unit
                            if rec.ks_xlabels and rec.ks_ylabels:
                                ks_yaxis = json.loads(rec.ks_ylabels)

                                y_labels = []
                                for y_axis in ks_yaxis.keys():
                                    data_row = {'data': [], 'label': ks_yaxis[y_axis]['measure']}

                                    if rec.ks_dashboard_item_type in ['ks_bar_chart', 'ks_horizontalBar_chart',
                                                                      'ks_line_chart']:
                                        chart_type = ks_yaxis[y_axis]['chart_type']
                                        if rec.ks_dashboard_item_type in ['ks_horizontalBar_chart',
                                                                      'ks_line_chart']:
                                            chart_type = 'bar'

                                        if chart_type in ['bar', 'line']:
                                            data_row['type'] = chart_type
                                        if rec.ks_bar_chart_stacked:
                                            data_row['stack'] = ks_yaxis[y_axis]['group']
                                        if ks_yaxis[y_axis]['chart_type'] == 'line':
                                            y_labels.insert(0, y_axis)
                                            ks_chart_data['datasets'].insert(0, data_row)
                                        else:
                                            y_labels.append(y_axis)
                                            ks_chart_data['datasets'].append(data_row)
                                    else:
                                        y_labels.append(y_axis)
                                        ks_chart_data['datasets'].append(data_row)

                                for res in records.get('records'):

                                    if res.get(rec.ks_xlabels, False):
                                        ks_chart_data['labels'].append(res[rec.ks_xlabels])
                                        counter = 0
                                        for y_axis in y_labels:
                                            if res.get(y_axis, False):
                                                ks_chart_data['datasets'][counter]['data'].append(res[y_axis])
                                            counter += 1
                        return json.dumps(ks_chart_data)

                    else:
                        return False
            else:
                return False

    @api.depends('ks_custom_query', 'ks_data_calculation_type')
    def ks_get_list_view_data(self):
        for rec in self:
            if rec.ks_list_view_type and rec.ks_dashboard_item_type and rec.ks_dashboard_item_type == 'ks_list_view':
                ks_list_view_data = {'label': [], 'data_rows': [], 'date_index': [], 'type': 'query'}
                if rec.ks_data_calculation_type != 'query':
                    return super(KsDashboardNinjaItemAdvance, self).ks_get_list_view_data()
                elif rec.ks_data_calculation_type == 'query' and rec.ks_query_result:
                    ks_list_view_data = rec.ks_format_query_result(rec.ks_query_result)
                    rec.ks_list_view_data = json.dumps(ks_list_view_data)
                else:
                    rec.ks_list_view_data = False
            else:
                rec.ks_list_view_data = False

    def _ksGetListViewData(self, domain=[]):
        rec = self
        ks_list_view_data = {'label': [], 'data_rows': [], 'date_index': [], 'type': 'query'}
        if rec.ks_list_view_type and rec.ks_dashboard_item_type and rec.ks_dashboard_item_type == 'ks_list_view':
            if rec.ks_data_calculation_type != 'query':
                return super(KsDashboardNinjaItemAdvance, self)._ksGetListViewData(domain)
            elif rec.ks_data_calculation_type == 'query' and rec.ks_query_result:
                ks_list_view_data = rec.ks_format_query_result(rec.ks_query_result)
            else:
                ks_list_view_data = False
        else:
            ks_list_view_data = False
        return ks_list_view_data

    def ks_format_query_result(self, ks_query_result):
        query_result = json.loads(ks_query_result)

        ks_list_view_data = {
            'label': [], 'data_rows': [],
            'date_index': [], 'type': 'query', 'records': [], 'columns': {},
            'total': len(query_result.get('records', []))
        }

        records = query_result.get('records', [])
        if not self._context.get('export_all', False):
            records = records[:self.ks_pagination_limit]

        if query_result:
            ks_list_fields = query_result.get('header')

            for field in ks_list_fields:
                field_name = field.replace("_", " ")
                ks_list_view_data['columns'][field] = { 'field_description': field_name.title(), 'type': 'char' }
                # ks_list_view_data['label'].append(field.title())
            for res in records:
                record = {'data': {}, 'ks_column_type': []}
                for field in ks_list_fields:
                    record['data'][field] = { 'value': res[field] }
                    # data_row['data'].append(res[field])
                    # data_row['ks_column_type'].append('char')
                ks_list_view_data['records'].append(record)

            return ks_list_view_data
        else:
            return ks_list_view_data

    def get_item_config(self, params = {}):
         config = super(KsDashboardNinjaItemAdvance, self).get_item_config(params)

         config.update({
             'ks_data_calculation_type': self.ks_data_calculation_type,
             # 'ks_is_external_api': self.ks_is_external_api,
             # 'ks_url': self.ks_url,
             # 'ks_api_header': self.ks_api_header,
         })

         return config
         # item[""] = rec.
         # # item['ks_list_view_layout'] = rec.ks_list_view_layout
         # item['
         # item['']= rec.ks_url
         # item[''] = rec.ks_api_header

         # item['data_source'] = rec.data_source

         return item

    def _get_list_item_config(self, item_domain1):
        result = super(KsDashboardNinjaItemAdvance, self)._get_list_item_config(item_domain1)
        result.update({
            'ks_list_view_layout': self.ks_list_view_layout,
            # 'ks_list_view_type': self.ks_list_view_type,
            # 'ks_pagination_limit': self.ks_pagination_limit,
            # 'list_view_type': self.ks_list_view_type,
        })
        return result



    # def ks_test_connection(self):
    #     try:
    #         if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_postgres':
    #             connection = psycopg2.connect(
    #                 host=self.ks_host,
    #                 database=self.ks_db_name,
    #                 user=self.ks_db_user,
    #                 password=self.ks_db_password,
    #                 port=self.ks_port
    #             )
    #             cursor = connection.cursor()
    #
    #         else:
    #             connection = mysql.connector.connect(
    #                 host=self.ks_host,
    #                 database=self.ks_db_name,
    #                 user=self.ks_db_user,
    #                 password=self.ks_db_password,
    #                 port=self.ks_port,
    #                 auth_plugin='mysql_native_password'
    #             )
    #             cursor = connection.cursor()
    #     except Exception as e:
    #         raise ValidationError(_("Error: Unable to connect to the database. Reason: %s") %e)
    #
    #     finally:
    #     # Close the cursor and the database connection in the finally block
    #         if 'connection' in locals():
    #             cursor.close()
    #             connection.close()
    #             self.ks_db_connection = True
    #             return {
    #                 'type': 'ir.actions.client',
    #                 'tag': 'display_notification',
    #                 'params': {
    #                     'title': _('Success'),
    #                     'message': 'Connection Successful',
    #                     'sticky': False,
    #                 }
    #             }


    @api.depends('ks_custom_query', 'ks_data_calculation_type', 'ks_query_start_date', 'ks_query_end_date',
                 'ks_is_date_ranges', 'ks_dashboard_item_type', 'ks_is_external_db')
    def ks_run_query(self):
        selected_start_date = False
        selected_end_date = False
        ks_start_date = False
        ks_end_date = False

        # FIX: bad approaches and code issues
        for rec in self:
            if rec.ks_is_date_ranges:
                ks_type = 'date'
                ks_start_date = 'ks_start_date'
                ks_end_date = 'ks_end_date'
                if rec.ks_custom_query and (
                        ("%(ks_start_date)" in rec.ks_custom_query) or ("%(ks_end_date)" in rec.ks_custom_query)):
                    ks_type = 'date'
                    ks_start_date = 'ks_start_date'
                    ks_end_date = 'ks_end_date'
                if rec.ks_custom_query and (("%(ks_start_datetime)" in rec.ks_custom_query) or (
                        "%(ks_start_datetime)" in rec.ks_custom_query)):
                    ks_type = 'datetime'
                    ks_start_date = 'ks_start_datetime'
                    ks_end_date = 'ks_end_datetime'
                if self._context.get('ksDateFilterSelection', False):
                    ksDateFilterSelection = self._context.get('ksDateFilterSelection', False)

                    if ksDateFilterSelection == 'l_custom':
                        ks_timezone = self._context.get('tz') or self.env.user.tz
                        selected_start_date = self._context['ksDateFilterStartDate']
                        selected_end_date = self._context['ksDateFilterEndDate']
                        ks_is_def_custom_filter = self._context.get('ksIsDefultCustomDateFilter', False)
                        if selected_start_date and selected_end_date and not ks_is_def_custom_filter and ks_type == 'datetime':
                            selected_start_date = ks_convert_into_utc(selected_start_date, ks_timezone)
                            selected_end_date = ks_convert_into_utc(selected_end_date, ks_timezone)
                        if ks_type == 'date' and ks_is_def_custom_filter:
                            selected_start_date = ks_convert_into_local(selected_start_date, ks_timezone)
                            selected_end_date = ks_convert_into_local(selected_end_date, ks_timezone)
                    if ksDateFilterSelection not in ['l_custom', 'l_none']:
                        ks_get_date_ranges = ks_get_date(ksDateFilterSelection, rec, ks_type)
                        selected_start_date = ks_get_date_ranges['selected_start_date']
                        selected_end_date = ks_get_date_ranges['selected_end_date']
            if rec.ks_dashboard_item_type == 'ks_bar_chart' or rec.ks_dashboard_item_type == 'ks_horizontalBar_chart':
                ks_is_group_column = True
            else:
                ks_is_group_column = False
            # with api.Environment.manage():
            ks_query = rec.ks_custom_query
            if rec.ks_data_calculation_type == 'query' and rec.ks_dashboard_item_type not in ['ks_tile', 'ks_kpi'] \
                    and rec.ks_custom_query:
                if ks_query and "{#MYCOMPANY}" in ks_query:
                    ks_query = ks_query.replace("{#MYCOMPANY}", str(self.env.company.id))
                if ks_query and "{##MYCOMPANY}" in ks_query:
                    ks_query = ks_query.replace("{##MYCOMPANY}", str(tuple(self.env.companies.ids)) if len(self.env.companies.ids) > 1 else f"({self.env.companies.ids[0]})")
                if ks_query and "{#UID}" in ks_query:
                    ks_query = ks_query.replace("{#UID}", str(self.env.user.id))

                if rec.ks_dashboard_item_type == 'ks_list_view':
                    rec.ks_query_result = rec.ks_get_list_query_result(ks_query, selected_start_date,
                                                                       selected_end_date)
                else:
                    # with api.Environment.manage():
                    try:
                        type_code = []
                        # conn = sql_db.db_connect(self.env.cr.dbname)
                        if rec.ks_is_external_db == True and rec.ks_external_db_type == 'ks_postgres':
                            connection = psycopg2.connect(
                                host=rec.ks_host,
                                database=rec.ks_db_name,
                                user=rec.ks_db_user,
                                password=rec.ks_db_password,
                                port=rec.ks_port
                            )
                            new_env = connection.cursor()
                        elif rec.ks_is_external_db == True and rec.ks_external_db_type == 'ks_sql':
                            connection = mysql.connector.connect(
                                host=rec.ks_host,
                                database=rec.ks_db_name,
                                user=rec.ks_db_user,
                                password=rec.ks_db_password,
                                port=rec.ks_port,
                                auth_plugin='mysql_native_password'
                            )
                            new_env = connection.cursor()
                        else:
                            new_env = self.pool.cursor()
                        if rec.ks_is_date_ranges:
                            start_date = rec.ks_query_start_date
                            end_date = rec.ks_query_end_date
                            if selected_end_date or selected_start_date:
                                start_date = selected_start_date if selected_start_date else selected_end_date - relativedelta.relativedelta(
                                    years=1000)
                                end_date = selected_end_date if selected_end_date else selected_start_date + relativedelta.relativedelta(
                                    years=1000)
                            if rec.ks_is_external_db == True and rec.ks_external_db_type == 'ks_sql':
                                new_env.execute(
                                    "select * from (" + ks_query + ")" + "as ks_chart_query limit %(ks_limit)s",
                                    {ks_start_date: str(
                                        start_date - relativedelta.relativedelta(years=10)),
                                        ks_end_date: str(
                                            end_date + relativedelta.relativedelta(years=10)),
                                        'ks_limit': 5000})
                                header_rec = [col[0] for col in new_env.description]
                            else:
                                start_date = datetime.fromisoformat(start_date) if isinstance(start_date,str) else start_date
                                end_date = datetime.fromisoformat(end_date) if isinstance(end_date,str) else end_date

                                new_env.execute("with ks_chart_query as (" + ks_query + ")" +
                                                "select * from ks_chart_query limit %(ks_limit)s",
                                                {ks_start_date: str(
                                                    start_date - relativedelta.relativedelta(years=10)),
                                                    ks_end_date: str(
                                                        end_date + relativedelta.relativedelta(years=10)),
                                                    'ks_limit': 5000})
                                header_rec = [col.name for col in new_env.description]
                            if rec.ks_is_external_db == True:
                                rows = new_env.fetchall()
                                result = [dict(zip(header_rec, row)) for row in rows]
                            else:
                                result = new_env.dictfetchall()
                            if result:
                                for header_key in header_rec:
                                    if type(result[0][header_key]).__name__ == 'float' or \
                                            type(result[0][header_key]).__name__ == 'int':
                                        type_code.append('numeric')
                                    else:
                                        type_code.append('string')
                            if rec.ks_is_external_db == True and rec.ks_external_db_type == 'ks_sql':
                                new_env.execute(
                                    "select * from (" + ks_query + ")" + "as ks_chart_query limit %(ks_limit)s",
                                    {ks_start_date: str(start_date),
                                     ks_end_date: str(end_date), 'ks_limit': 5000, })
                                header = [col[0] for col in new_env.description]
                            else:
                                new_env.execute("with ks_chart_query as (" + ks_query + ")" +
                                                "select * from ks_chart_query limit %(ks_limit)s",
                                                {ks_start_date: str(start_date),
                                                 ks_end_date: str(end_date), 'ks_limit': 5000, })
                                header = [col.name for col in new_env.description]
                        else:
                            if rec.ks_is_external_db == True and rec.ks_external_db_type == 'ks_sql':
                                new_env.execute(
                                    "select * from (" + ks_query + ")" + "as ks_chart_query limit %(ks_limit)s",
                                    {'ks_limit': 5000})
                                header = [col[0] for col in new_env.description]
                            else:
                                new_env.execute("with ks_chart_query as (" + ks_query + ")" +
                                                "select * from ks_chart_query limit %(ks_limit)s",
                                                {'ks_limit': 5000})
                                header = [col.name for col in new_env.description]
                        if rec.ks_is_external_db == True:
                            rows = new_env.fetchall()
                            records = [dict(zip(header, row)) for row in rows]
                        else:
                            records = new_env.dictfetchall()
                        if records:
                            type_code.clear()
                            for header_key in header:
                                if type(records[0][header_key]).__name__ == 'float' or \
                                        type(records[0][header_key]).__name__ == 'int' or\
                                        type(records[0][header_key]).__name__ == 'Decimal':
                                    type_code.append('numeric')
                                else:
                                    type_code.append('string')

                    except ProgrammingError as e:
                        if e.args[0] == 'no results to fetch':
                            raise ValidationError(_("You can only read the Data from Database"))
                        else:
                            raise ValidationError(_(str(e)))
                    except Exception as e:
                        if type(e).__name__ == 'KeyError':
                            raise ValidationError(_(
                                'Wrong date variables, Please use ks_start_date and ks_end_date in custom query'))
                        raise ValidationError(_(str(e)))
                    else:
                        if rec.ks_is_external_db == True:
                            connection.close()
                            new_env.close()
                    finally:
                        if rec.ks_is_external_db != True:
                            new_env.close()


                    for res in records:
                        keys_to_delete = []
                        for key in res:
                            if type(res[key]).__name__ == 'datetime':
                                res[key] = res[key].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            elif type(res[key]).__name__ == 'date':
                                res[key] = res[key].strftime(DEFAULT_SERVER_DATE_FORMAT)
                            elif type(res[key]).__name__ == 'Decimal':
                                res[key] = int(res[key])
                            elif type(res[key]).__name__ == 'time':
                                res[key] = res[key].strftime("%H-%M-%S")
                            elif type(res[key]).__name__ not in ['char','Decimal','str','float','int','text','bool','binary','date','datetime']:
                                res[key] = None


                    rec.ks_query_result = json.dumps({'header': header,
                                                      'records': records, 'type_code': type_code,
                                                      'ks_is_group_column': ks_is_group_column})

            elif rec.ks_dashboard_item_type in ['ks_kpi'] \
                    and rec.ks_custom_query:
                if rec.ks_is_date_ranges and not (selected_start_date or selected_end_date):
                    selected_start_date = rec.ks_query_start_date
                    selected_end_date = rec.ks_query_end_date
                ks_query_result = rec.ks_get_kpi_result(ks_query, selected_start_date, selected_end_date,
                                                        ks_start_date=ks_start_date, ks_end_date=ks_end_date)

                # TODO: adding try catch bcz flow is not working properly for datetime object
                try:
                    rec.ks_query_result = json.dumps(ks_query_result)
                except Exception:
                    raise ValidationError(_("Serialization of query result failed. Please check your query."))

            else:
                rec.ks_query_result = False

    def ks_get_kpi_result(self, ks_query, selected_start_date, selected_end_date, ks_start_date=False,
                          ks_end_date=False):

        if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_postgres':
            connection = psycopg2.connect(
                host=self.ks_host,
                database=self.ks_db_name,
                user=self.ks_db_user,
                password=self.ks_db_password,
                port=self.ks_port
            )
            new_env = connection.cursor()
        elif self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
            connection = mysql.connector.connect(
                host=self.ks_host,
                database=self.ks_db_name,
                user=self.ks_db_user,
                password=self.ks_db_password,
                port=self.ks_port,
                auth_plugin='mysql_native_password'
            )
            new_env = connection.cursor()
        else:
            new_env = self.pool.cursor()

        if ks_query and "{#MYCOMPANY}" in ks_query:
            ks_query = ks_query.replace("{#MYCOMPANY}", str(self.env.user.company_id.id))
        if ks_query and "{##MYCOMPANY}" in ks_query:
            ks_query = ks_query.replace("{##MYCOMPANY}", str(tuple(self.env.companies.ids)) if len(self.env.companies.ids) > 1 else f"({self.env.companies.ids[0]})")
        if ks_query and "{#UID}" in ks_query:
            ks_query = ks_query.replace("{#UID}", str(self.env.user.id))

        start_date = selected_start_date
        end_date = selected_end_date

        if not selected_start_date and selected_end_date:
            start_date = selected_end_date - relativedelta.relativedelta(
                years=1000)
        if not selected_end_date and selected_start_date:
            end_date = selected_start_date + relativedelta.relativedelta(
                years=1000)

        self.ks_validate_kpi_query(ks_query, start_date, end_date, ks_start_date=ks_start_date,
                                   ks_end_date=ks_end_date)
        if self.ks_is_date_ranges:
            if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                new_env.execute(
                    "select * from (" + ks_query + ")" + "as ks_list_query",
                    {ks_start_date: str(start_date),
                     ks_end_date: str(end_date)})
                header_rec = [col[0] for col in new_env.description]
            else:
                new_env.execute("with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query"
                            , {ks_start_date: str(start_date),
                               ks_end_date: str(end_date)})
                header_rec = [col.name for col in new_env.description]
        else:
            if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                new_env.execute(
                    "select * from (" + ks_query + ")" + "as ks_list_query")
                header_rec = [col[0] for col in new_env.description]
            else:
                new_env.execute("with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query")
                header_rec = [col.name for col in new_env.description]

        if self.ks_is_external_db == True:
            row = new_env.fetchone()
            result = dict(zip(header_rec, row))
            if type(result[header_rec[0]]).__name__ == 'Decimal':
                result[header_rec[0]] = str(result[header_rec[0]])
        else:
            result = new_env.dictfetchone()
        if len(result.keys()) == 1:
            return result
        else:
            raise ValidationError(_("Query must be return single entity value"))

    def ks_validate_kpi_query(self, ks_query, start_date, end_date, ks_start_date=False,
                              ks_end_date=False):
        try:
            if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_postgres':
                connection = psycopg2.connect(
                    host=self.ks_host,
                    database=self.ks_db_name,
                    user=self.ks_db_user,
                    password=self.ks_db_password,
                    port=self.ks_port
                )
                new_env = connection.cursor()
            elif self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                connection = mysql.connector.connect(
                    host=self.ks_host,
                    database=self.ks_db_name,
                    user=self.ks_db_user,
                    password=self.ks_db_password,
                    port=self.ks_port,
                    auth_plugin='mysql_native_password'
                )
                new_env = connection.cursor()
            else:
                new_env = self.pool.cursor()

            if self.ks_is_date_ranges:
                if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                    new_env.execute(
                        "select * from (" + ks_query + ")" + "as ks_list_query limit 5",
                        {ks_start_date: str(start_date),
                         ks_end_date: str(end_date)})
                    header_rec = [col[0] for col in new_env.description]
                else:
                    new_env.execute("with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query limit 5"
                                , {ks_start_date: str(start_date),
                                   ks_end_date: str(end_date)})
                    header_rec = [col.name for col in new_env.description]
            else:
                if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                    new_env.execute(
                        "select * from (" + ks_query + ")" + "as ks_list_query limit 5")
                    header_rec = [col[0] for col in new_env.description]
                else:
                    new_env.execute("with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query limit 5")
                    header_rec = [col.name for col in new_env.description]

            if self.ks_is_external_db == True:
                rows = new_env.fetchall()
                result = [dict(zip(header_rec, row)) for row in rows]
            else:
                result = new_env.dictfetchall()
            if len(result) != 1:
                raise ValidationError(_("Query must be return single entity value"))
            elif len(result[0].keys()) != 1:
                raise ValidationError(_("Query must be return single entity value"))
            else:
                ks_validate = True
        except ProgrammingError as e:
            if e.args[0] == 'no results to fetch':
                raise ValidationError(_("You can only read the Data from Database"))
            else:
                raise ValidationError(_(str(e)))
        except Exception as e:
            if type(e).__name__ == 'KeyError':
                raise ValidationError(
                    _('Wrong date variables, Please use ks_start_date and ks_end_date in custom query'))
            raise ValidationError(_(str(e)))

    def ks_get_list_query_result(self, ks_query, selected_start_date, selected_end_date, ks_offset=0,
                                 ks_export_all=False):
        # with api.Environment.manage():
        try:
            type_code = []
            ks_type = 'datetime'
            # new_cr = self.pool.cursor()
            # conn = sql_db.db_connect(self.env.cr.dbname)
            if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_postgres':
                connection = psycopg2.connect(
                    host=self.ks_host,
                    database=self.ks_db_name,
                    user=self.ks_db_user,
                    password=self.ks_db_password,
                    port=self.ks_port
                )
                new_env = connection.cursor()
            elif self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                connection = mysql.connector.connect(
                    host=self.ks_host,
                    database=self.ks_db_name,
                    user=self.ks_db_user,
                    password=self.ks_db_password,
                    port=self.ks_port,
                    auth_plugin='mysql_native_password'
                )
                new_env = connection.cursor()
            else:
                new_env = self.pool.cursor()
            if self.ks_is_date_ranges:
                ks_start_date = 'ks_start_date'
                ks_end_date = 'ks_end_date'
                if self.ks_custom_query and (
                        ("%(ks_start_date)" in self.ks_custom_query) or ("%(ks_end_date)" in self.ks_custom_query)):
                    ks_type = 'date'
                    ks_start_date = 'ks_start_date'
                    ks_end_date = 'ks_end_date'
                if self.ks_custom_query and (("%(ks_start_datetime)" in self.ks_custom_query) or (
                        "%(ks_start_datetime)" in self.ks_custom_query)):
                    ks_type = 'datetime'
                    ks_start_date = 'ks_start_datetime'
                    ks_end_date = 'ks_end_datetime'

            # Pagination didn't worked after 10000 records
            limit = 10000
            if ks_query and "{#MYCOMPANY}" in ks_query:
                ks_query = ks_query.replace("{#MYCOMPANY}", str(self.env.company.id))
            if ks_query and "{##MYCOMPANY}" in ks_query:
                ks_query = ks_query.replace("{##MYCOMPANY}", str(tuple(self.env.companies.ids)) if len(self.env.companies.ids) > 1 else f"({self.env.companies.ids[0]})")
            if ks_query and "{#UID}" in ks_query:
                ks_query = ks_query.replace("{#UID}", str(self.env.user.id))

            if self._context.get('export_all', False):
                if self._context.get('ksDateFilterSelection', False):
                    ksDateFilterSelection = self._context.get('ksDateFilterSelection', False)
                    if ksDateFilterSelection == 'l_custom':
                        ks_timezone = self._context.get('tz') or self.env.user.tz
                        selected_start_date = self._context['ksDateFilterStartDate']
                        selected_end_date = self._context['ksDateFilterEndDate']
                        ks_is_def_custom_filter = self._context.get('ksIsDefultCustomDateFilter', False)
                        if selected_start_date and selected_end_date and not ks_is_def_custom_filter and ks_type == 'datetime':
                            selected_start_date = ks_convert_into_utc(selected_start_date, ks_timezone)
                            selected_end_date = ks_convert_into_utc(selected_end_date, ks_timezone)
                        if ks_type == 'date' and ks_is_def_custom_filter:
                            selected_start_date = ks_convert_into_local(selected_start_date, ks_timezone)
                            selected_end_date = ks_convert_into_local(selected_end_date, ks_timezone)
                    if ksDateFilterSelection not in ['l_custom', 'l_none'] and not selected_start_date and not selected_end_date:
                        ks_get_date_ranges = ks_get_date(ksDateFilterSelection, self, 'datetime')
                        selected_start_date = ks_get_date_ranges['selected_start_date']
                        selected_end_date = ks_get_date_ranges['selected_end_date']

            if self.ks_is_date_ranges:
                start_date = self.ks_query_start_date
                end_date = self.ks_query_end_date
                if selected_end_date or selected_start_date:
                    start_date = selected_start_date if selected_start_date else selected_end_date - relativedelta.relativedelta(
                        years=1000)
                    end_date = selected_end_date if selected_end_date else selected_start_date + relativedelta.relativedelta(
                        years=1000)
                if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                    new_env.execute(
                        "select * from (" + ks_query + ")" + "as ks_chart_query limit %(ks_limit)s offset %(ks_offset)s",
                        {ks_start_date: str(start_date - relativedelta.relativedelta(years=10)),
                         ks_end_date: str(end_date + relativedelta.relativedelta(years=10)),
                         'ks_limit': limit, 'ks_offset': ks_offset
                         })
                    header_rec = [col[0] for col in new_env.description]
                else:
                    start_date_dt = datetime.fromisoformat(str(start_date))
                    end_date_dt = datetime.fromisoformat(str(end_date))
                    adjusted_start_date = start_date_dt - relativedelta.relativedelta(years=10)
                    adjusted_end_date = end_date_dt + relativedelta.relativedelta(years=10)

                    new_env.execute(
                        "WITH ks_list_query AS (" + ks_query + ") " +
                        "SELECT * FROM ks_list_query LIMIT %(ks_limit)s OFFSET %(ks_offset)s",
                        {
                            'ks_start_date': adjusted_start_date.isoformat(),
                            'ks_end_date': adjusted_end_date.isoformat(),
                            'ks_limit': limit,
                            'ks_offset': ks_offset
                        }
                    )
                    header_rec = [col.name for col in new_env.description]
                if self.ks_is_external_db == True:
                    rows = new_env.fetchall()
                    result = [dict(zip(header_rec, row)) for row in rows]
                else:
                    result = new_env.dictfetchall()
                if result:
                    for header_key in header_rec:
                        if type(result[0][header_key]).__name__ == 'float' or \
                                type(result[0][header_key]).__name__ == 'int':
                            type_code.append('numeric')
                        else:
                            type_code.append('string')
                if self._context.get('export_all', False):
                    if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                        new_env.execute(
                            "select * from (" + ks_query + ")" + "as ks_chart_query offset %(ks_offset)s",
                            {ks_start_date: str(start_date),
                             ks_end_date: str(end_date),
                             'ks_offset': ks_offset})
                        header = [col[0] for col in new_env.description]
                    else:
                        new_env.execute("with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query "
                                                                                     " offset %(ks_offset)s",
                                        {ks_start_date: str(start_date),
                                         ks_end_date: str(end_date),
                                         'ks_offset': ks_offset})
                        header = [col.name for col in new_env.description]
                else:
                    if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                        new_env.execute(
                            "select * from (" + ks_query + ")" + "as ks_chart_query limit %(ks_limit)s offset %(ks_offset)s",
                            {ks_start_date: str(start_date),
                             ks_end_date: str(end_date),
                             'ks_limit': limit, 'ks_offset': ks_offset})
                        header = [col[0] for col in new_env.description]
                    else:
                        new_env.execute(
                            "with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query limit "
                                                                         "%(ks_limit)s offset %(ks_offset)s",
                            {ks_start_date: str(start_date),
                             ks_end_date: str(end_date),
                             'ks_limit': limit, 'ks_offset': ks_offset})
                        header = [col.name for col in new_env.description]
            else:
                if self._context.get('export_all', False):
                    if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                        new_env.execute(
                            "select * from (" + ks_query + ")" + "as ks_chart_query offset %(ks_offset)s",
                            {'ks_offset': ks_offset})
                        header = [col[0] for col in new_env.description]
                    else:
                        new_env.execute("with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query "
                                                                                     " offset %(ks_offset)s",
                                        {'ks_offset': ks_offset})
                        header = [col.name for col in new_env.description]
                else:
                    if self.ks_is_external_db == True and self.ks_external_db_type == 'ks_sql':
                        new_env.execute(
                            "select * from (" + ks_query + ")" + "as ks_chart_query limit %(ks_limit)s offset %(ks_offset)s",
                            {'ks_limit': limit, 'ks_offset': ks_offset})
                        header = [col[0] for col in new_env.description]
                    else:
                        new_env.execute(
                            "with ks_list_query as (" + ks_query + ")" + "select * from ks_list_query limit "
                                                                         "%(ks_limit)s offset %(ks_offset)s",
                            {'ks_limit': limit, 'ks_offset': ks_offset})
                        header = [col.name for col in new_env.description]
            if self.ks_is_external_db == True:
               rows = new_env.fetchall()
               records = [dict(zip(header, row)) for row in rows]
            else:
               records = new_env.dictfetchall()
            if records:
                type_code.clear()
                for header_key in header:
                    if type(records[0][header_key]).__name__ == 'float' or \
                            type(records[0][header_key]).__name__ == 'int' or \
                            type(records[0][header_key]).__name__ == 'Decimal':
                        type_code.append('numeric')
                    else:
                        type_code.append('string')

        except ProgrammingError as e:
            if e.args[0] == 'no results to fetch':
                raise ValidationError(_("You can only read the Data from Database"))
            else:
                raise ValidationError(_(str(e)))
        except Exception as e:
            if type(e).__name__ == 'KeyError':
                raise ValidationError(
                    _(
                        'Wrong date variables, Please use ks_start_date and ks_end_date or ks_start_datetime and ks_end_datetime in custom query'))
            raise ValidationError(_(str(e)))

        else:
            if self.ks_is_external_db == True:
                connection.close()
                new_env.close()
        finally:
            if self.ks_is_external_db != True:
                new_env.close()
        for res in records:
            keys_to_delete=[]
            for key in res:
                if type(res[key]).__name__ == 'datetime':
                    res[key] = res[key].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                elif type(res[key]).__name__ == 'date':
                    res[key] = res[key].strftime(DEFAULT_SERVER_DATE_FORMAT)
                elif type(res[key]).__name__ == 'Decimal':
                    res[key] = str(res[key])
                elif type(res[key]).__name__ == 'time':
                    res[key] = res[key].strftime("%H-%M-%S")
                elif type(res[key]).__name__ not in ['char', 'Decimal','str', 'float', 'int', 'text', 'bool', 'binary',
                                                         'date', 'datetime']:
                    res[key] = None

        return json.dumps({'header': header,
                           'records': records, 'type_code': type_code,
                           'ks_is_group_column': False})

    # @api.model
    def ks_get_next_offset(self, offset, item_domain={}):
        # record = self.browse(ks_item_id)
        record = self
        ks_offset = offset['offset']
        selected_start_date = False
        selected_end_date = False
        if self._context.get('ksDateFilterSelection', False):
            ksDateFilterSelection = self._context.get('ksDateFilterSelection', False)
            if ksDateFilterSelection == 'l_custom':
                ks_timezone = self._context.get('tz') or self.env.user.tz
                selected_start_date = self._context['ksDateFilterStartDate']
                selected_end_date = self._context['ksDateFilterEndDate']
                selected_start_date = ks_convert_into_utc(selected_start_date, ks_timezone)
                selected_end_date = ks_convert_into_utc(selected_end_date, ks_timezone)
            if ksDateFilterSelection not in ['l_custom', 'l_none']:
                ks_get_date_ranges = ks_get_date(ksDateFilterSelection, self, 'datetime')
                selected_start_date = ks_get_date_ranges['selected_start_date']
                selected_end_date = ks_get_date_ranges['selected_end_date']
        if self.ks_data_calculation_type == 'custom':
            return super(KsDashboardNinjaItemAdvance, self).ks_get_next_offset(offset, item_domain)
        else:
            ks_query = str(self.ks_custom_query)
            ks_start_date = record.ks_query_start_date
            ks_end_date = record.ks_query_end_date
            if selected_start_date or selected_end_date:
                ks_start_date = selected_start_date
                ks_end_date = selected_end_date
            ks_query_result = self.ks_get_list_query_result(ks_query, ks_start_date, ks_end_date,
                                                            ks_offset=int(ks_offset))
            ks_list_view_data = self.ks_format_query_result(ks_query_result)
            ks_list_view_data['total'] += int(ks_offset)
        return {
            'ks_list_view_data': ks_list_view_data,
            # 'offset': int(ks_offset) + 1,
            # 'next_offset': int(ks_offset) + len(ks_list_view_data['data_rows']),
            # 'limit': record.ks_record_data_limit if record.ks_record_data_limit else 0,
        }

    @api.onchange('ks_query_start_date', 'ks_query_end_date')
    def ks_check_valid_datetime(self):
        for rec in self:
            if rec.ks_query_start_date and rec.ks_query_end_date:
                if rec.ks_query_start_date >= rec.ks_query_end_date:
                    raise ValidationError(_("Start Date should be less than End Date"))

    @api.onchange('ks_custom_query','ks_is_external_db','ks_external_db_type')
    def ks_empty_labels(self):
        for rec in self:
            rec.ks_xlabels = False
            rec.ks_ylabels = False

    @api.onchange('ks_is_date_ranges')
    def ks_onchange_date_ranges(self):
        for rec in self:
            rec.ks_custom_query = False

    @api.onchange('ks_is_external_db','ks_external_db_type')
    def ks_onchange_external_db(self):
        for rec in self:
            rec.ks_custom_query = False
            rec.ks_host = False
            rec.ks_db_name = False
            rec.ks_db_password = False
            rec.ks_db_user = False
            rec.ks_port = False

    #   function to handle the sorting for list view
    def ks_get_list_data_orderby_extend(self, order_id, sort_order, offset, domain={}):
        ks_filter_domain = domain.get('ks_domain_1', [])
        ks_field = self._context.get('field', False)
        ks_domain = []

        if self._context.get('ksDateFilterSelection', False):
            ks_date_filter_selection = self._context['ksDateFilterSelection']
            if ks_date_filter_selection == 'l_custom':
                self = self.with_context(
                    ksDateFilterStartDate = parse(self._context['ksDateFilterStartDate']))
                self = self.with_context(
                    ksDateFilterEndDate = parse(self._context['ksDateFilterEndDate']))
                self = self.with_context(ksIsDefultCustomDateFilter=False)
        else:
            ks_date_filter_selection = self.ks_dashboard_ninja_board_id.ks_date_filter_selection
            self = self.with_context(ksDateFilterStartDate=self.ks_dashboard_ninja_board_id.ks_dashboard_start_date)
            self = self.with_context(ksDateFilterEndDate=self.ks_dashboard_ninja_board_id.ks_dashboard_end_date)
            self = self.with_context(ksDateFilterSelection=ks_date_filter_selection)
        if ks_date_filter_selection not in ['l_custom', 'l_none']:
            ks_date_data = ks_get_date(ks_date_filter_selection, self, 'datetime')
            self = self.with_context(ksDateFilterStartDate=ks_date_data["selected_start_date"])
            self = self.with_context(ksDateFilterEndDate=ks_date_data["selected_end_date"])
        self = self.with_context(ksIsDefultCustomDateFilter=True)
        ks_proper_domain = self.ks_convert_into_proper_domain(self.ks_domain, self, ks_filter_domain)

        if len(ks_proper_domain) > 0:
            ks_domain = ks_domain + ks_proper_domain

        list_view_data = self.get_list_view_record(order_id, sort_order, ks_domain, ksoffset=offset)
        return list_view_data

class KsDashboardAPI(models.Model):
    _name = 'ks.dashboard.api'
    _description = 'Dashboard Ninja API datatype'

    ks_dashboard_datatype_id = fields.Many2one('ks_dashboard_ninja.item', string="API Dashboard Item Id")
    name = fields.Char(string="Name")
    ttype = fields.Selection([('char', 'char'), ('date', 'date'), ('float', 'float'),
                              ('integer', 'integer')],
                             string='Type')
