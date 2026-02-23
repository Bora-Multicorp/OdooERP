/** @odoo-module */

import { registry } from "@web/core/registry";
const { useEffect, useRef,onWillUpdateProps, Component,onMounted} = owl;


export class KsXLabels extends Component{
        setup() {
            const self = this;
            this.select_label = useRef("select_label")
            useEffect(()=>{this.mount()})
        }
    get ks_columns_list(){
        var self = this;
        var field = this.props.record.data;
        var ks_query_result = JSON.parse(field.ks_query_result);
        if (ks_query_result.header.length){
            self.ks_check_for_labels();
            var ks_columns_list =  self.ks_columns
        }else{
            var ks_columns_list = false
        }
        return ks_columns_list
    }

    mount(){
        var self = this;
        if (this.select_label.el){
        if (self.props.record.data.ks_xlabels=="") {
            $(this.select_label.el).val(false)
        }else{
            $(this.select_label.el).val(this.props.record.data.ks_xlabels)
       }
       if (this.props.readonly == true) {
        $(this.select_label.el).find('.ks_label_select').addClass('ks_not_click');
       }
       }
    }


        get value(){
            var self = this;
            var field = self.props.record.data;

            if(field.ks_query_result){
                var ks_query_result = JSON.parse(field.ks_query_result);
                var value= self.ks_columns[self.value]
            }else{
                var value = false
            }
            return value

        }
        ks_toggle_icon_input_click(e){
            var self = this;
            if (e.target.id==""){
                this.props.record.update({ [this.props.name]: e.target.value })
            }
        }

        ks_check_for_labels(){
            var self = this;
            self.ks_columns = {false:false};
            var query_result = JSON.parse(self.props.record.data.ks_query_result);
            if (self.props.name === "ks_ylabels"){
                query_result.header.forEach(function(key){
                    if(typeof(query_result[0][key]) === "number") {
                        self.ks_columns[key] = self.ks_title(key.replace("_", " "));
                    }
                });
            } else {
                query_result.header.forEach(function(key){
                    self.ks_columns[key] = self.ks_title(key.replace("_", " "));
                });
            }
        }

        ks_title(str) {
            var split_str = str.toLowerCase().split(' ');
            for (var i = 0; i < split_str.length; i++) {
                split_str[i] = split_str[i].charAt(0).toUpperCase() + split_str[i].substring(1);
                str = split_str.join(' ');
            }
            return str;
        }
}

KsXLabels.template = "ks_select_labels";
export const KsXLabelsfield={
    component:KsXLabels
}

registry.category("fields").add('ks_x_labels', KsXLabelsfield);