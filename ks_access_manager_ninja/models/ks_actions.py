# -*- coding: utf-8 -*-

from odoo import api, models


class IrActionsActions(models.Model):
    _inherit = 'ir.actions.actions'

    @api.model_create_multi
    def create(self, vals):
        """When any new record was created then it will create inside ou custom model also."""
        records = super(IrActionsActions, self).create(vals)
        vals_list = []
        for rec in records:
            vals_list.append({'name': rec.name, 'ks_action_id': rec.id})
        self.env['report.action.data'].create(vals_list)
        return records

    def unlink(self):
        """When any record is deleted then it will delete record inside our custom model as well."""

        self.env['report.action.data'].sudo().search([('ks_action_id', 'in', self.ids)]).unlink()
        return super(IrActionsActions, self).unlink()
