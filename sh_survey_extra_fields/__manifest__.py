# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "Survey - Extra Fields",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "summary": "organization survey options mo company survey more fields create awesome survey app survey by email field survey by file field survey by url survey by time field odoo survey by range field Survey Extra Field Survey Extra Fields Odoo Survey customization Extra fields in surveys Enhanced survey forms Survey data collection Custom survey questions Survey personalization Advanced survey features Survey form flexibility Additional survey fields Survey data customization Extended survey options Survey response variety Survey field expansion Tailored survey questions Survey form extensions Enhanced data collection Extra fields for feedback Survey form modification Customizable survey design Survey response diversity",
    "description": """Online survey is the best way to get a review about your organize/company so you have to some type of question for user like product review so they need to upload an images or documents like much more type of questions. Currently in odoo provide only few type of field in Survey.So here we build a module that can helps you to add that fields in your survey very easily like email, file, url, time, range, week, month, password, color etc. you can easily add all this field in survey no need any professional IT skills.""",
    "version": "0.0.4",
    "depends": ["survey"],
    "data": [
        "security/ir.model.access.csv",
        "views/survey_views.xml",
        "views/survey_templates.xml",
        "views/survey_survey_views.xml",
    ],
    "assets" : {
        "survey.survey_assets" : [
            "sh_survey_extra_fields/static/src/scss/sh_survey_extra_fields.scss",
            "sh_survey_extra_fields/static/src/js/sh_survey_extra_fields.js",
            #"sh_survey_extra_fields/static/src/lib/filter-multi-select-bundle.min.js",
            #"sh_survey_extra_fields/static/src/lib/bootstrap-multiselect.js",
            "sh_survey_extra_fields/static/src/css/filter_multi_select.css",
            #"sh_survey_extra_fields/static/src/lib/jSignature.js"
        ]
    },
    "images": ["static/description/background.png", ],
    "application": True,
    "auto_install": False,
    "installable": True,
    "license": "OPL-1",
    "price": 25,
    "currency": "EUR",
}
