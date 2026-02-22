from odoo import fields, models


class KsEcomTag(models.Model):
    _name = "ks.ecom.tag"
    _description = "E-com Purchase Tag"

    name = fields.Char(required=True, translate=False)

    _sql_constraints = [
        ("ks_ecom_tag_name_unique", "unique(name)", "Tag name must be unique."),
    ]

