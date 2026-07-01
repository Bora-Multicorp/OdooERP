{
    "name": "Contact Multi-Company",
    "summary": "Assign contacts to multiple companies with company-scoped record rules",
    "version": "18.0.1.0.0",
    "category": "Contacts",
    "depends": ["base_multi_company", "base"],
    "data": [
        "views/res_partner_view.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "license": "AGPL-3",
    "installable": True,
}
