# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "Survey - Matrix Advance",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "summary": "Custom Survey Matrix Module Survey Question Matrix App Survey With Custom Matrix Create Survey Matrix Make Survey Matrix With Barcode Survey Matrix With QRCode Generate Custom Survey Odoo Survey solutions Matrix Advance Survey tools Matrix Advance platform Online survey management Survey data analysis Survey technology Advanced surveying solutions Survey software features Matrix Advance features Customizable surveys Data collection software Survey analytics Matrix Advance benefits Survey data reporting",
    "description": """Currently, in odoo, you can make a survey matrix with 2 options, checkbox & radio button (one choice per row and multiple-choice per row) only, so our module provides to create and add a custom survey matrix. You can handle a survey with different fields like single-line text box, multi-line text box, numerical value, date, date-time, color, email, URL, time, range, week, month, password & file. You can print the survey matrix. Survey Matrix Advance Odoo, Custom Survey Matrix Module, Survey Question Matrix, Survey With Custom Matrix, Create Survey Matrix, Make Survey Matrix With Barcode, Survey Matrix With QRCode, Generate Custom Survey Odoo, Custom Survey Matrix Module, Survey Question Matrix App, Survey With Custom Matrix, Create Survey Matrix, Make Survey Matrix With Barcode, Survey Matrix With QRCode, Generate Custom Survey Odoo""",
    "version": "0.0.1",
    "depends": [
        "sh_survey_extra_fields",
    ],
    "application": True,
    "data": [
        "views/survey_views.xml",
        "views/survey_templates.xml",
    ],
    'assets': {
        'survey.survey_assets': [
            'sh_survey_matrix_adv/static/src/js/survey.js',
            'sh_survey_matrix_adv/static/src/css/sh_survey_matrix_adv.css',
        ]
    },
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "license": "OPL-1",
    "price": 40,
    "currency": "EUR"
}
