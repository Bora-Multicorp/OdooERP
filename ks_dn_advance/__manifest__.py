# -*- coding: utf-8 -*-


{
    'name': 'Advanced Dashboard Ninja with AI',

    'summary': """
        Dashboard Ninja Advance for Odoo allows you to showcase your complex data in 
        form of interactive and engaging charts or list views. Manage the complicated data of 
        your business and get a detailed insight into your sale. Dashboard Ninja Advance,
        Dashboard Ninja, Modern Odoo Dashboards, Powerful Dashboard, Beautiful Dashboard, 
        Modern Dashboard, Chart Dashboard, Graph Dashboard, Pie Chart Dashboard, Ninja Dashboard.
    """,

    'description': """
Best Odoo Dashboard Apps
        Slider Dashboard Apps
        Odoo Query Dashboard Apps
        Display Dashboard Apps
        All in One Dashboard
        TV Dashboard Apps
        List View Layout
        Dashboards item Slider
        Full Screen Dashboard Item
        TV View Dashboard
        Custom Database View
        Complex Data Dashboard
        Different Models Dashboard
        Multi Models Data
        Custom Report Dashboard
        Multi Report Dashboard
        Complex Data Item
        Slider Report
        Multiple Table in Single Dashboard
        Bulk Data in Single Dashboard
        Graph View Dashboard Apps
        Pie Chart Dashboard Apps
        Widget View Dashboard
        Best Odoo Apps
        Dashboard For Websites
        Odoo Dashboard apps
        Dashboard apps
        Dashboards for Websites
        HR Dashboard Apps
        Sales Dashboard Apps
        inventory Dashboard Apps
        Lead Dashboards
        Opportunity Dashboards
        CRM Dashboards
        Best POS Apps
        POS Dashboards
        Web Dynamic Apps,
        Report Import/Export,
        Date Filter Apps
        Tile Dashboard Apps
        Dashboard Widgets,
        Dashboard Manager Apps,
        Debranding Apps
        Customize Dashboard Apps
        Charts Dashboard Apps
        Invoice Dashboard Apps
        Project management Apps
        Visualization charts
        Finance Dashboard
        Accounting Report
        Accounting Valuation
        Accounting Quantities
        Dashboard for Odoo
        Accounting Metrics
        Expense Dashboard Apps
        Invoicing Dashboard
        Vendor Payable Report
        Stock management System
        Purchase Order Dashboards
        Sales Order Dashboards
        Stock Alert Apps
        Inventory Alert Apps
        Product Dashboard
        Sales Dashboard
        Best Dashboard Apps
        Inventory Report
        Inventory Valuation
        Inventory Quantities
        V14 Dashboard
        Dashboard v14.0,
        Odoo Dashboard v14.0
        New Odoo Dashboard Apps
        Dashboard Ninja Advance
""",

    'author': 'Ksolves India Ltd.',

    'license': 'OPL-1',

    'currency': 'EUR',

    'price': '149',

    'website': 'https://store.ksolves.com/',

    'maintainer': 'Ksolves India Ltd.',

    'live_test_url': 'https://ksdnadvance18.kappso.com/web/demo_login',

    'category': 'Services',

    'version': '18.0.1.1.6',

    'support': 'sales@ksolves.com',

    'depends': ['ks_dashboard_ninja', 'mail'],

    'external_dependencies': {'python': ['mysql-connector']},

    'data': ['security/ir.model.access.csv',
             'views/ks_dashboard_ninja_item_view_inherit.xml',
             'views/ks_dashboard_form_view_inherit.xml',
             'views/ks_mail_template.xml'],

    'module_type': 'official',

    'images': ['static/description/banner/banner.gif'],

    'assets': {'web.assets_backend': [
        'ks_dn_advance/static/src/css/ks_tv_dashboard.css',
        'ks_dn_advance/static/src/components/**/*',
        'ks_dn_advance/static/src/js/ks_labels.js',
        'ks_dn_advance/static/src/js/ks_ylabels.js',
        'ks_dn_advance/static/src/js/ks_dashboard_ninja_tv_list_preview.js',
        'ks_dn_advance/static/src/xml/**/*',
        ("remove", "ks_dn_advance/static/src/**/*.dark.scss"),
        ],
        'web.assets_web_dark': [
            'ks_dn_advance/static/src/**/*.dark.scss',
        ],
        'web.assets_frontend': [
            'ks_dn_advance/static/src/css/ks_tv_dashboard.css',
        ],
        'web.assets_qweb': ['ks_dn_advance/static/src/xml/**/*']},

    'uninstall_hook': 'ks_dna_uninstall_hook',
}
