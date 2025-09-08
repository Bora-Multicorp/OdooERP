# Copyright 2023 Karthik <karthik@sodexis.com>
# Copyright 2020 Kevin Graveman <k.graveman@onestein.nl>
# Copyright 2015-2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models
from odoo.exceptions import AccessError


# class ResPartner(models.Model):
#     _inherit = "res.partner"

#     company_ids = fields.Many2many(
#         comodel_name="res.company",
#         column1="partner_id",
#         column2="company_id",
#         relation="res_partner_company_rel",
#     )

#     @api.model
#     def search(self, args, offset=0, limit=None, order=None):
#         dom = self.env["multi.company.abstract"]._patch_company_domain(args)
#         return super().search(dom, offset=offset, limit=limit, order=order)


class ResPartner(models.Model):
    _inherit = "res.partner"

    company_ids = fields.Many2many(
        comodel_name="res.company",
        column1="partner_id",
        column2="company_id",
        relation="res_partner_company_rel",
    )

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        dom = self.env["multi.company.abstract"]._patch_company_domain(args)
        return super().search(dom, offset=offset, limit=limit, order=order)
