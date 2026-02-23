# -*- coding: utf-8 -*-

import base64
import io
import itertools
import json
import operator
from collections import defaultdict
from datetime import datetime

import openpyxl
from lxml import etree
from lxml.builder import E
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.addons.base.models.res_users import name_selection_groups
from odoo.http import content_disposition, request
from odoo.tools import osutil

from odoo import api, fields, models
from odoo.addons.web.controllers import export
from odoo.addons.web.controllers.export import ExportXlsxWriter


def name_boolean_group(id):
    return 'in_group_' + str(id)


class ResGroups(models.Model):
    _inherit = "res.groups"

    view_access = fields.Many2many(
        groups="base.group_system",
    )
    # The inverse field of the field group_id on the res.users.profile model
    # This field should be used a One2one relation as a profile can only be
    # represented by one group. It's declared as a One2many field as the
    # inverse field on the res.users.profile it's declared as a Many2one
    ks_profile_id = fields.One2many(
        comodel_name="user.profiles",
        inverse_name="group_id",
        help="Relation for the groups that represents a profiles",
    )

    ks_profile_ids = fields.Many2many(
        comodel_name="user.profiles",
        relation="res_groups_implied_profiles_rel",
        string="Profiles",
        compute="_compute_profile_ids",
        help="Profiles in which the group is involved",
    )

    parent_ids = fields.Many2many(
        "res.groups",
        "res_groups_implied_rel",
        "hid",
        "gid",
        string="Parents",
        help="Inverse relation for the Inherits field. "
             "The groups from which this group is inheriting",
    )

    trans_parent_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Parent Groups",
        compute="_compute_trans_parent_ids",
        recursive=True,
    )

    ks_profiles_count = fields.Integer("# Profiles", compute="_compute_profiles_count")
    custom = fields.Boolean('Custom')

    def _compute_profiles_count(self):
        for group in self:
            group.ks_profiles_count = len(group.ks_profile_ids)

    @api.depends("parent_ids.trans_parent_ids")
    def _compute_trans_parent_ids(self):
        for group in self:
            group.trans_parent_ids = (
                    group.parent_ids | group.parent_ids.trans_parent_ids
            )

    def _compute_profile_ids(self):
        for group in self:
            if group.trans_parent_ids:
                group.ks_profile_ids = group.trans_parent_ids.ks_profile_id
            else:
                group.ks_profile_ids = group.ks_profile_id

    def ks_action_view_profiles(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "ks_access_manager_ninja.action_res_user_profiles_tree"
        )
        action["context"] = {}
        if len(self.ks_profile_ids) > 1:
            action["domain"] = [("id", "in", self.ks_profile_ids.ids)]
        elif self.ks_profile_ids:
            form_view = [
                (self.env.ref("ks_access_manager_ninja.view_res_user_profiles_form").id, "form")
            ]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = self.ks_profile_ids.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    @api.model
    def _update_user_groups_view(self):
        """ Modify the view with xmlid ``base.user_groups_view``, which inherits
            the user form view, and introduces the reified group fields.
        """
        # remove the language to avoid translations, it will be handled at the view level
        self = self.with_context(lang=None)

        # We have to try-catch this, because at first init the view does not
        # exist but we are already creating some basic groups.
        view = self.env.ref('base.user_groups_view', raise_if_not_found=False)
        if not (view and view._name == 'ir.ui.view'):
            return

        if self._context.get('install_filename') or self._context.get(MODULE_UNINSTALL_FLAG):
            # use a dummy view during install/upgrade/uninstall
            xml = E.field(name="groups_id", position="after")

        else:
            group_no_one = view.env.ref('base.group_no_one')
            group_employee = view.env.ref('base.group_user')
            xml0, xml1, xml2, xml3, xml4 = [], [], [], [], []
            xml_by_category = {}
            xml1.append(E.separator(string='User Type', colspan="2", groups='base.group_no_one'))

            user_type_field_name = ''
            user_type_readonly = str({})
            sorted_tuples = sorted(self.get_groups_by_application(),
                                   key=lambda t: t[0].xml_id != 'base.module_category_user_type')
            for app, kind, gs, category_name in sorted_tuples:  # we process the user type first
                attrs = {}
                # hide groups in categories 'Hidden' and 'Extra' (except for group_no_one)
                if app.xml_id in self._get_hidden_extra_categories():
                    attrs['groups'] = 'base.group_no_one'

                # User type (employee, portal or public) is a separated group. This is the only 'selection'
                # group of res.groups without implied groups (with each other).
                if app.xml_id == 'base.module_category_user_type':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    # test_reified_groups, put the user category type in invisible
                    # as it's used in domain of attrs of other fields,
                    # and the normal user category type field node is wrapped in a `groups="base.no_one"`,
                    # and is therefore removed when not in debug mode.
                    xml0.append(E.field(name=field_name, invisible="1", on_change="1"))
                    user_type_field_name = field_name
                    user_type_readonly = f'{user_type_field_name} != {group_employee.id}'
                    attrs['widget'] = 'radio'
                    # Trigger the on_change of this "virtual field"
                    attrs['on_change'] = '1'
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())

                elif kind == 'selection':
                    # application name with a selection field
                    field_name = name_selection_groups(gs.ids)
                    attrs['readonly'] = user_type_readonly
                    attrs['on_change'] = '1'
                    if category_name not in xml_by_category:
                        xml_by_category[category_name] = []
                        xml_by_category[category_name].append(E.newline())
                    xml_by_category[category_name].append(E.field(name=field_name, **attrs))
                    xml_by_category[category_name].append(E.newline())
                    # add duplicate invisible field so default values are saved on create
                    if attrs.get('groups') == 'base.group_no_one':
                        xml0.append(E.field(name=field_name, **dict(attrs, invisible="1", groups='!base.group_no_one')))

                else:
                    # application separator with boolean fields
                    app_name = app.name or 'Other'
                    xml4.append(E.separator(string=app_name, **attrs))
                    left_group, right_group = [], []
                    attrs['readonly'] = user_type_readonly
                    # we can't use enumerate, as we sometime skip groups
                    group_count = 0
                    for g in gs:
                        # Restrict to show custom group on the user's form
                        if g.custom:
                            continue
                        field_name = name_boolean_group(g.id)
                        dest_group = left_group if group_count % 2 == 0 else right_group
                        if g == group_no_one:
                            # make the group_no_one invisible in the form view
                            dest_group.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            dest_group.append(E.field(name=field_name, **attrs))
                        # add duplicate invisible field so default values are saved on create
                        xml0.append(E.field(name=field_name, **dict(attrs, invisible="1", groups='!base.group_no_one')))
                        group_count += 1
                    xml4.append(E.group(*left_group))
                    xml4.append(E.group(*right_group))

            xml4.append({'class': "o_label_nowrap"})
            user_type_invisible = f'{user_type_field_name} != {group_employee.id}' if user_type_field_name else None

            for xml_cat in sorted(xml_by_category.keys(), key=lambda it: it[0]):
                master_category_name = xml_cat[1]
                xml3.append(E.group(*(xml_by_category[xml_cat]), string=master_category_name))

            field_name = 'user_group_warning'
            user_group_warning_xml = E.div({
                'class': "alert alert-warning",
                'role': "alert",
                'colspan': "2",
                'invisible': f'not {field_name}',
            })
            user_group_warning_xml.append(E.label({
                'for': field_name,
                'string': "Access Rights Mismatch",
                'class': "text text-warning fw-bold",
            }))
            user_group_warning_xml.append(E.field(name=field_name))
            xml2.append(user_group_warning_xml)

            xml = E.field(
                *(xml0),
                E.group(*(xml1), groups="base.group_no_one"),
                E.group(*(xml2), invisible=user_type_invisible),
                E.group(*(xml3), invisible=user_type_invisible),
                E.group(*(xml4), invisible=user_type_invisible, groups="base.group_no_one"), name="groups_id",
                position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))

        # serialize and update the view
        xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")
        if xml_content != view.arch:  # avoid useless xml validation if no change
            new_context = dict(view._context)
            new_context.pop('install_filename', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})

    @api.model
    def get_groups_by_application(self):
        """ Return all groups classified by application (module category), as a list::

                [(app, kind, groups), ...],

            where ``app`` and ``groups`` are recordsets, and ``kind`` is either
            ``'boolean'`` or ``'selection'``. Applications are given in sequence
            order.  If ``kind`` is ``'selection'``, ``groups`` are given in
            reverse implication order.
        """

        def linearize(app, gs, category_name):
            # 'User Type' is an exception
            if app.xml_id == 'base.module_category_user_type':
                return (app, 'selection', gs.sorted('id'), category_name)
            # determine sequence order: a group appears after its implied groups
            order = {g: len(g.trans_implied_ids & gs) for g in gs}
            # We want a selection for Accounting too. Auditor and Invoice are both
            # children of Accountant, but the two of them make a full accountant
            # so it makes no sense to have checkboxes.
            if app.xml_id == 'base.module_category_accounting_accounting':
                return (app, 'selection', gs.sorted(key=order.get), category_name)
            # check whether order is total, i.e., sequence orders are distinct
            if len(set(order.values())) == len(gs):
                return (app, 'selection', gs.sorted(key=order.get), category_name)
            else:
                return (app, 'boolean', gs, (100, 'Other'))

        # classify all groups by application
        by_app, others = defaultdict(self.browse), self.browse()
        for g in self.get_application_groups([]):
            if g.category_id:
                by_app[g.category_id] += g
            else:
                others += g
        res = []
        for app, gs in sorted(by_app.items(), key=lambda it: it[0].sequence or 0):
            # Hide user profile category from user's form
            if app.xml_id == 'ks_access_manager_ninja.ir_module_category_profiles':
                continue
            if app.parent_id:
                res.append(linearize(app, gs, (app.parent_id.sequence, app.parent_id.name)))
            else:
                res.append(linearize(app, gs, (100, 'Other')))

        if others:
            res.append((self.env['ir.module.category'], 'boolean', others, (100, 'Other')))
        return res

    def ks_export_user_groups(self):
        export_id = self.env['ir.exports'].sudo().search([('name', '=', 'Default Template')], limit=1)
        if not export_id:
            export_id = self.env['ir.exports'].create({'name': 'Default Template', 'resource': 'res.groups'})
            export_fields = ['id', 'name', 'category_id/id', 'share', 'model_access/perm_create',
                             'model_access/perm_unlink',
                             'model_access/id', 'users/id', 'implied_ids/id', 'menu_access/id', 'model_access/model_id',
                             'view_access/id', 'model_access/name', 'model_access/perm_write', 'model_access/perm_read',
                             'rule_groups/id'
                             ]
            for field in export_fields:
                self.env['ir.exports.line'].create({'name': field, 'export_id': export_id.id})

        export_fields_list = export_id.export_fields.read()

        fields_data = self.fields_info(
            'res.groups', [f['name'] for f in export_fields_list])
        fields_list = [
            {'name': field['name'], 'label': fields_data[field['name']]}
            for field in export_fields_list
        ]
        data = {"import_compat": True, "context": {
            "params": {"cids": self.env.company.id, },
            "lang": "en_US", "tz": "Asia/Calcutta", "uid": self.env.user.id, "allowed_company_ids": [1]},
                "domain": [["share", "=", False]],
                "fields": fields_list, "groupby": [],
                "ids": self.env['res.groups'].search([]).ids, "model": "res.groups"}
        #
        response = self.base(json.dumps(data, indent=4))
        workbook = openpyxl.load_workbook(filename=io.BytesIO(response.data))
        output = io.BytesIO()
        output.seek(0)
        workbook.save(output)
        request.env['ir.attachment'].create({
            'name': 'Default_res_groups_export' + str(datetime.now()) + '.xlsx',
            'datas': base64.b64encode(output.getvalue()),
            'mimetype': response.mimetype,
            'res_model': 'res.groups',
            'public': True
        })

    def fields_info(self, model, export_fields):
        info = {}
        fields = self.env[model].fields_get()
        if ".id" in export_fields:
            fields['.id'] = fields.get('id', {'string': 'ID'})

        # there's a single fields_get to execute)
        for (base, length), subfields in itertools.groupby(
                sorted(export_fields),
                lambda field: (field.split('/', 1)[0], len(field.split('/', 1)))):
            subfields = list(subfields)
            if length == 2:
                # subfields is a seq of $base/*rest, and not loaded yet
                info.update(self.graft_subfields(
                    fields[base]['relation'], base, fields[base]['string'],
                    subfields
                ))
            elif base in fields:
                info[base] = fields[base]['string']

        return info

    def graft_subfields(self, model, prefix, prefix_string, fields):
        export_fields = [field.split('/', 1)[1] for field in fields]
        return (
            (prefix + '/' + k, prefix_string + '/' + v)
            for k, v in self.fields_info(model, export_fields).items())

    def filename(self, base):
        """ Creates a filename *without extension* for the item / format of
        model ``base``.
        """
        if base not in request.env:
            return base

        model_description = request.env['ir.model']._get(base).name
        return f"{model_description} ({base})"

    def from_group_data(self, fields, groups):
        raise NotImplementedError()

    def base(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        Model = self.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby,
                                           lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = export.GroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas', [])
            response_data = self.from_data(fields, columns_headers, export_data)

        response = request.make_response(response_data,
                                         headers=[('Content-Disposition',
                                                   content_disposition(
                                                       osutil.clean_filename(self.filename(model) + '.xlsx'))),
                                                  ('Content-Type',
                                                   'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')], )

        return response

    def from_data(self, fields, columns_headers, rows):
        with ExportXlsxWriter(fields, columns_headers, len(rows)) as xlsx_writer:
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    xlsx_writer.write_cell(row_index + 1, cell_index, cell_value)

        return xlsx_writer.value
