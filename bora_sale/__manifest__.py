# -*- coding: utf-8 -*-
{
    'name': "bora_sale",

    'summary': "Bora sale operations",

    'description': """
Bora sale operations
    """,

    'author': "Bora",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'sale_management', 'purchase', 'sale', 'sale_stock', 'account', 'prt_report_attachment_preview','product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/pi_unlock_approve_request_views.xml',
        'wizard/pi_unlock_reject_request_views.xml',
        'views/procurement_team_views.xml',
        'views/pi_unlock_approvers.xml',
        'views/sale_order_unlock.xml',
        'views/unlock_button_action_inherited.xml',
        'views/account_move_inherited.xml',
        'views/add_documents.xml',
        'views/pod_in_stock_picking.xml',   
        'views/quotation_to_pi.xml',
        'views/hide_tax_field_dubai.xml',
        'views/invoice_report_print_preview_action.xml',
        'views/custom_invoice_report.xml',
        'views/IFSC_and_branch_code.xml',
        'views/customer_fields_for_india_sale_invoice.xml',
        'views/create_csv_and_download.xml',
        'views/qc_check_on_delivery.xml',
        'data/account_group_in_sales.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'Other proprietary'
}

