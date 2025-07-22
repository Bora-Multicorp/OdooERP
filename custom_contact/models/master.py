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

class ConstitutionofBusiness(models.Model):
    _name = "constitution.business"
    _description = "Constitution of Business"

    name = fields.Char('Name', required=True)

class NumberManagingPartnerDirectors (models.Model):
    _name = "number.partner.director"
    _description = "Number of Managing Partner / Directors"

    name = fields.Char('Name', required=True)


