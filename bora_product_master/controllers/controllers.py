# -*- coding: utf-8 -*-
# from odoo import http


# class BoraProductMaster(http.Controller):
#     @http.route('/bora_product_master/bora_product_master', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/bora_product_master/bora_product_master/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('bora_product_master.listing', {
#             'root': '/bora_product_master/bora_product_master',
#             'objects': http.request.env['bora_product_master.bora_product_master'].search([]),
#         })

#     @http.route('/bora_product_master/bora_product_master/objects/<model("bora_product_master.bora_product_master"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('bora_product_master.object', {
#             'object': obj
#         })

