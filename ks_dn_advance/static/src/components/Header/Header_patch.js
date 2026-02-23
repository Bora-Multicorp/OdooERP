
import { patch } from "@web/core/utils/patch";
import { KsHeader } from "@ks_dashboard_ninja/components/Header/Header";
import { _t } from "@web/core/l10n/translation";
import { DashboardTVCarousel } from '@ks_dn_advance/components/dashboard_tv_carousel/dashboard_tv_carousel';
import { KsItems } from '@ks_dashboard_ninja/components/ks_items/ks_items';
import { deepCopy, deepMerge } from "@web/core/utils/objects";

patch(KsHeader.prototype, {

    get dropdowns(){
        let dropdownsToAdd = [
            { name: "Dashboard TV", svg: "dashboard_tv", func:() => this.openDashboardTVCarousel(), class: '', modes: ["manager", "user", "custom_date"] },
            { name: "Email", svg: "email_svg", func:() => this.sendMail(), class: '', modes: ["manager","user", "custom_date"] },
            { name: "Print Dashboard", svg: "print_dashboard", func: () => this.printDashboard(), class: '', modes: ["manager","user", "custom_date"] },
        ]
        const dropdowns = super.dropdowns
        let moreDropdown = dropdowns.find( (dropdown) => dropdown.name === 'More')
        moreDropdown.dropdown_items.push(...dropdownsToAdd)
        return dropdowns
    },

    openDashboardTVCarousel(e){
        if(!this.itemsPresence())   return

        let props = this.props.dashboardActions.ksItemsCommonPropsForStructure()
        let itemsBasicData = deepCopy(props.itemsBasicData)
        props.itemsBasicData = itemsBasicData?.filter(
            (itemBasicData) => itemBasicData.ks_dashboard_item_type !== "ks_to_do"
        ) ?? props.itemsBasicData

        this.dialogService.add(DashboardTVCarousel, {
            componentInfo: {
                component: KsItems,
                props: {
                    ...props,
                    isAIExplanation: true,
                    isItemsPreview: true,
                    isGridStack: false,
                    isColumnStructure: {
                        rootClass: 'carousel ks-custom-carousel w-100',
                        innerRootClass: 'carousel-inner ks-custom-carousel-inner',
                        childClass: 'carousel-item ks-custom-carousel-item px-2',
                    }
                }
            }
        })

    },

    async getDashboardImage(){
        const canvas = await html2canvas(this.props.dashboardRootRef.el, { useCORS: true, allowTaint: false })
        const image = canvas.toDataURL("image/jpeg", 0.90)
        return image
    },

    async getPdf(){
        this.notification.add(_t("Scroll to last chart to ensure every chart gets loaded"), { title: _t("Generating PDF"), type: 'info' })

        const image = await this.getDashboardImage()

        window.jsPDF = window.jspdf.jsPDF
        const pdf = new jsPDF("p", "mm", "a4")
        const imgProps = pdf.getImageProperties(image)
        const pdfPageWidth = pdf.internal.pageSize.getWidth()

        var maxHeight = 300;

        var heightPerPage = (imgProps.height * pdfPageWidth) / imgProps.width
        var heightLeft = heightPerPage;
        var position = 0;

        pdf.addImage(image,'JPEG', 0, 0, pdfPageWidth, heightPerPage, 'FAST')
        heightLeft -= maxHeight;
        while(heightLeft >= 0) {
            position = heightLeft - heightPerPage;
            pdf.addPage();
            pdf.addImage(image, 'JPEG', 0, position,  pdfPageWidth, heightPerPage, 'FAST')
            heightLeft -= maxHeight;
        }

        return pdf;
    },

    async printDashboard(){
        if(!this.itemsPresence())   return;
        let pdf = await this.getPdf()

        if(!pdf)    return
        pdf.save(this.props.dashboardData.name + '.pdf');
    },

    async sendMail() {
        if(!this.itemsPresence() || this.isMailProcess )   return;
        // todo : check the usage of jspdf , is it necessary ??

        this.isMailProcess = true

        let pdf = await this.getPdf()
        if(!pdf){
            this.isMailProcess = false
            return
        }


        const file = pdf.output()
        const base64String = btoa(file)

        let args = [[this.props.dashboardData.id], base64String]
        let response = await this.orm.call('ks_dashboard_ninja.board', 'ks_dashboard_send_mail', args, {})

        if (response['ks_is_send']){
            let msg = response['ks_massage']
            this.notification.add(_t(msg), { title:_t("Success"), type: 'info' })
        }else{
            let msg = response['ks_massage']
            this.notification.add(_t(msg), { title:_t("Fail"), type: 'warning' })

        }
        this.isMailProcess = false
    },

});

