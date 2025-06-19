# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PartnerLocationType(models.Model):
    _name = "res.partner.location.type"
    _description = "Partner Location Type"

    name = fields.Char('Type', required=True)

class PartnerAddressType(models.Model):
    _name = "res.partner.address.type"
    _description = "Partner Address Type"

    name = fields.Char('Address Type', required=True)



