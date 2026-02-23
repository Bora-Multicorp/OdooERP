/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { FileUploader } from "@web/views/fields/file_handler";
import { onMounted, useEffect } from "@odoo/owl";
import { renderToString } from "@web/core/utils/render";

patch(FileUploader.prototype,{
   setup() {
        super.setup();
        useEffect(
            () => this.changeIcons()
          );
   },

   changeIcons(){
        let ks_upload_parent_field_el = this.fileInputRef?.el?.closest('.upload-file-btn');
        if(ks_upload_parent_field_el){
            let pencil_icon_btn = ks_upload_parent_field_el.querySelector('.fa-pencil');
            let fileUploadIcon = ks_upload_parent_field_el.querySelector('.o_select_file_button.btn-primary');
            let download_icon_btn = ks_upload_parent_field_el.querySelector('.fa-download');
            let trash_icon_btn = ks_upload_parent_field_el.querySelector('.fa-trash');

            if(pencil_icon_btn){
                pencil_icon_btn.classList.remove('fa', 'fa-pencil');
                pencil_icon_btn.innerHTML += renderToString("ks_dashboard_ninja.edit_svg", {})
            }
            if(download_icon_btn){
                download_icon_btn.classList.remove('fa', 'fa-download')
                download_icon_btn.innerHTML += renderToString("ks_dashboard_ninja.download_svg", {})
            }
            if(trash_icon_btn){
                trash_icon_btn.classList.remove('fa', 'fa-trash')
                trash_icon_btn.innerHTML += renderToString("ks_dashboard_ninja.trash_svg", {})
            }
        }
   },
});