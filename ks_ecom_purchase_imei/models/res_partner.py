# -*- coding: utf-8 -*-
from email.policy import default

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re
from datetime import timedelta, date
from lxml import etree

class CustomContact(models.Model):
    _inherit = 'res.partner'

    is_ecommerce_vendor = fields.Boolean(default=False, tracking=True,string="Is Ecommerce Vendor")

    sla_lead_time_days = fields.Integer(
        string="SLA Lead Time (Days)",
        help="Committed delivery lead time for this vendor"
    )

