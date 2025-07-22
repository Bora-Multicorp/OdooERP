# -*- coding: utf-8 -*-


from odoo import models


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='name', download=False,
                       mimetype=None, default_mimetype='application/octet-stream',
                       access_token=None):

        obj = None
        if xmlid:
            obj = self._xmlid_to_obj(self.env, xmlid)
        if id and model == 'survey.user_input.line' and access_token:
            obj = self.env[model].browse(int(id))
            if obj and obj.sudo().access_token == access_token:
                obj = obj.sudo()
                self = self.sudo()
        if obj:
            obj.check_access_rights('read')
            obj.check_access_rule('read')
        return super(Http, self).binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype=default_mimetype, access_token=access_token)


        

                