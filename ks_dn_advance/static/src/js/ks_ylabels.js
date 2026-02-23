/** @odoo-module */

import { registry } from "@web/core/registry";
const { useEffect, useRef,onMounted,Component} = owl;

export class KsYLabels extends Component{
       setup(){
            this.ks_columns = {};
            this.ylabel = useRef("y_label")
            this.ks_rows_keys = [];
            this.ks_rows_chart_type = {};
            useEffect(()=>{
                this.mount()
            });

       }


        get y_label(){
            var self = this;
            var field = this.props.record.data;
            var ks_query_result = JSON.parse(field.ks_query_result);
            if ( ks_query_result.header.length){
                self.ks_check_for_labels();
                var info = {
                    label_rows: self.ks_columns,
                    chart_type: self.ks_rows_chart_type,
                    ks_is_group_column: ks_query_result.ks_is_group_column
                }
            }
            return info
        }



        ks_check_for_labels(){
            var self = this;
            self.ks_columns = {};
            self.ks_rows_keys = [];
            self.ks_rows_chart_type = {};
            self.ks_value={};
            if(self.props.record.data.ks_ylabels !=""){
                var ks_columns = JSON.parse(self.props.record.data.ks_ylabels);
                Object.keys(ks_columns).forEach(function(key){
                    var chart_type = ks_columns[key]['chart_type'];
                    self.ks_rows_chart_type[key] = chart_type;
                    ks_columns[key]['chart_type'] = {}
                    if(self.props.record.data.ks_dashboard_item_type === 'ks_bar_chart'){
                        var chart_type_temp = self.props.record.data.ks_dashboard_item_type.split("_")[1];
                        if (chart_type_temp !== chart_type) {
                            chart_type = chart_type_temp;
                        }
                        ks_columns[key]['chart_type'][chart_type] = self.ks_title(chart_type);
                        if (chart_type === "bar"){
                            ks_columns[key]['chart_type']["line"] = "Line";
                        } else {
                            ks_columns[key]['chart_type']["bar"] = "Bar"
                        }
                    } else {
                        var chart_type = self.props.record.data.ks_dashboard_item_type.split("_")[1];
                        ks_columns[key]['chart_type'][chart_type] = self.ks_title(chart_type);
                        self.ks_rows_chart_type[key] = chart_type;
                        if (chart_type === "bar") ks_columns[key]['chart_type']["line"] = "Line";
                    }
                    self.ks_rows_keys.push(key);
                });
                self.ks_columns = ks_columns;
            } else {
                var query_result = JSON.parse(self.props.record.data.ks_query_result);

                query_result.header.forEach(function(key){
                    for(var i =0;i< query_result.header.length; i++){
                        if(query_result.type_code[query_result.header.indexOf(key)] !== 'numeric'){
                            continue;
                        }
                        if(query_result.type_code[query_result.header.indexOf(key)] == 'numeric') {
                            var ks_row = {}
                            ks_row['measure'] = self.ks_title(key.replace("_", " "));
                            ks_row['chart_type'] = {}
                            var chart_type = self.props.record.data.ks_dashboard_item_type.split("_")[1];
                            ks_row['chart_type'][chart_type] = self.ks_title(chart_type);
                            if (chart_type === "bar") ks_row['chart_type']["line"] = "Line";
                            ks_row['group'] = " ";
                            self.ks_columns[key] = JSON.parse(JSON.stringify(ks_row));
                            if (chart_type === "bar"){
                            delete(ks_row['chart_type']['line'])
                            ks_row['chart_type']='bar'
                            self.ks_value[key]=ks_row
                            }else{
                            ks_row['chart_type']=self.props.record.data.ks_dashboard_item_type.split("_")[1]
                            self.ks_value[key]=ks_row
                            }
                        }
                        break;
                    }
                });
            }
        }

        mount(){
            var self = this;
            if(self.props.record.data.ks_query_result){
                var ks_query_result = JSON.parse(self.props.record.data.ks_query_result);
                if ( ks_query_result.header.length){
                    self.ks_check_for_labels()
                    if (Object.keys(self.ks_rows_chart_type).length==0){
                        this.props.record.update({ [this.props.name]: JSON.stringify(self.ks_value) })
                    }
                }

                if (this.props.readonly == true) {
                    $(this.ylabel.el).find('select').addClass('ks_not_click');
                    $(this.ylabel.el).find('td.ks_stack_group').addClass('ks_not_click');
                }
                self.ks_rows_keys.forEach(function(key){
                    $(self.ylabel.el).attr('id',key).val(self.ks_rows_chart_type[key]);
                })
            }
        }

        ks_toggle_icon_input_click(e){
            var self = this;
            if (e.target.id != ""){
                if ( this.ylabel.el){
                    var ks_tbody =  $(this.ylabel.el).find('tbody.ks_y_axis');
                    ks_tbody.find('select').each(function(){
                    self.ks_columns[this.id]['chart_type'] = this.value;
                    });
                }
            var value = JSON.stringify(self.ks_columns);
            this.props.record.update({ [this.props.name]: value })
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

        ks_group_input_click(e){
            var self = this;
            var ks_tbody =  $(this.ylabel.el).find('tbody.ks_y_axis');

            ks_tbody.find('select').each(function(){
                self.ks_columns[this.id]['chart_type'] = this.value;
            });
            self.ks_columns[e.target.id]['group'] = e.target.textContent.trim();
            var value = JSON.stringify(self.ks_columns);
            this.props.record.update({ [this.props.name]: value })
        }
    }
KsYLabels.template = "ks_y_label_table";

export const ksylabelfield = {
    component: KsYLabels
}

registry.category("fields").add('ks_y_labels', ksylabelfield);
