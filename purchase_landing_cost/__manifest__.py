# -*- coding: utf-8 -*-
{
    "name": "Purchase Landing Cost (PU-003)",
    "summary": "Net Landing Cost report per PO with FOC separation",
    "description": """
        Adds FOC (Free of Cost) on product, PU-003 button on PO to open
        Net Landing Cost report with manual inputs (Misc, Freight, Insurance, Exchange Rate)
        and formula-based duty calculations. Products are grouped by FOC.
    """,
    "author": "Ksolves Private Limited",
    "website": "https://www.ksolves.com/",
    "category": "Purchase",
    "version": "1.0",
    "depends": ["product", "purchase"],
    "data": [
        "views/product_template_views.xml",
        "views/purchase_landing_cost_report_views.xml",
        "report/report_purchase_landing_cost.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
