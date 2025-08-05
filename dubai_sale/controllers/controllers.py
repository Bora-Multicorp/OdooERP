# -*- coding: utf-8 -*-
# from odoo import http


# class DubaiSale(http.Controller):
#     @http.route('/dubai_sale/dubai_sale', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dubai_sale/dubai_sale/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dubai_sale.listing', {
#             'root': '/dubai_sale/dubai_sale',
#             'objects': http.request.env['dubai_sale.dubai_sale'].search([]),
#         })

#     @http.route('/dubai_sale/dubai_sale/objects/<model("dubai_sale.dubai_sale"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dubai_sale.object', {
#             'object': obj
#         })

