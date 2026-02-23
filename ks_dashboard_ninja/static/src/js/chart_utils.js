
import { renderToString } from "@web/core/utils/render";
import { localization } from "@web/core/l10n/localization";

export function renderNoDataGraph(chartRootObject){
    let modal = am5.Modal.new(chartRootObject, {
        content: `<div class="overview-sec-dasboards container-fluid h-100 graph_text">
            <div class="d-flex flex-column justify-content-center align-items-center h-100 no-data">
                <div>
                    <svg width="210" height="189" viewBox="0 0 210 189" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M107.547 0.412278L100.714 2.1793L16.5297 23.9494L9.69664 25.7164C6.37997 26.5781 3.53958 28.7239 1.79863 31.683C0.0576835 34.6421 -0.441653 38.173 0.410174 41.5008L30.0397 156.718C30.899 160.044 33.0388 162.893 35.9897 164.638C38.9406 166.384 42.4616 166.885 45.7802 166.031L45.7978 166.026L143.613 140.731L143.631 140.727C146.947 139.865 149.788 137.719 151.529 134.76C153.269 131.801 153.769 128.27 152.917 124.942L123.287 9.72474C122.428 6.3988 120.288 3.55047 117.337 1.80464C114.387 0.0588202 110.866 -0.441921 107.547 0.412278Z" fill="#F2F2F2"/>
                        <path d="M108.476 4.02447L100.382 6.11738L18.7182 27.2357L10.6251 29.3286C8.26323 29.9422 6.24051 31.4703 5.00073 33.5776C3.76096 35.6848 3.40536 38.1992 4.01197 40.5691L33.6415 155.786C34.2534 158.155 35.7772 160.183 37.8786 161.427C39.98 162.67 42.4874 163.026 44.8506 162.418L44.8683 162.414L142.683 137.119L142.701 137.114C145.063 136.5 147.086 134.972 148.325 132.865C149.565 130.758 149.921 128.243 149.314 125.874L119.685 10.6561C119.073 8.28764 117.549 6.25929 115.448 5.01605C113.346 3.77281 110.839 3.4162 108.476 4.02447Z" fill="white"/>
                        <path d="M102.367 41.3351L52.8847 54.1312C52.332 54.2741 51.7454 54.191 51.2538 53.9002C50.7622 53.6094 50.406 53.1346 50.2635 52.5804C50.121 52.0262 50.2038 51.4379 50.4938 50.945C50.7839 50.4521 51.2573 50.0948 51.8099 49.9519L101.292 37.1558C101.845 37.0134 102.431 37.0969 102.922 37.3877C103.413 37.6786 103.769 38.1531 103.912 38.707C104.054 39.2609 103.971 39.8489 103.682 40.3416C103.392 40.8344 102.919 41.1918 102.367 41.3351Z" fill="#F2F2F2"/>
                        <path d="M112.775 46.1647L54.6972 61.1837C54.1445 61.3266 53.5579 61.2435 53.0663 60.9527C52.5747 60.6618 52.2185 60.1871 52.076 59.6329C51.9335 59.0787 52.0163 58.4904 52.3063 57.9974C52.5964 57.5045 53.0698 57.1473 53.6224 57.0044L111.701 41.9854C112.253 41.8424 112.84 41.9255 113.331 42.2164C113.823 42.5072 114.179 42.9819 114.322 43.5361C114.464 44.0903 114.381 44.6786 114.091 45.1716C113.801 45.6645 113.328 46.0217 112.775 46.1647Z" fill="#F2F2F2"/>
                        <path d="M110.492 72.941L61.0097 85.7371C60.736 85.8079 60.4512 85.8239 60.1713 85.7843C59.8915 85.7447 59.6222 85.6502 59.3788 85.5061C59.1354 85.3621 58.9227 85.1715 58.7528 84.945C58.5828 84.7186 58.4591 84.4608 58.3885 84.1864C58.3179 83.912 58.3019 83.6263 58.3415 83.3457C58.381 83.0651 58.4752 82.795 58.6188 82.5509C58.7624 82.3069 58.9526 82.0935 59.1784 81.9231C59.4042 81.7527 59.6613 81.6286 59.9349 81.5578L109.417 68.7617C109.691 68.691 109.976 68.6749 110.256 68.7146C110.535 68.7542 110.805 68.8487 111.048 68.9927C111.291 69.1367 111.504 69.3274 111.674 69.5538C111.844 69.7803 111.968 70.0381 112.038 70.3125C112.109 70.5869 112.125 70.8726 112.085 71.1532C112.046 71.4338 111.952 71.7039 111.808 71.9479C111.664 72.192 111.474 72.4053 111.249 72.5757C111.023 72.7461 110.766 72.8703 110.492 72.941Z" fill="#F2F2F2"/>
                        <path d="M120.904 77.7701L62.8261 92.7891C62.5524 92.8599 62.2676 92.8759 61.9877 92.8363C61.7079 92.7966 61.4386 92.7021 61.1952 92.5581C60.9518 92.4141 60.7391 92.2235 60.5692 91.997C60.3992 91.7706 60.2755 91.5128 60.2049 91.2384C60.1343 90.9639 60.1183 90.6783 60.1579 90.3977C60.1974 90.1171 60.2916 89.847 60.4352 89.6029C60.5788 89.3588 60.769 89.1455 60.9948 88.9751C61.2206 88.8047 61.4777 88.6806 61.7513 88.6098L119.829 73.5908C120.382 73.4479 120.969 73.531 121.46 73.8218C121.952 74.1127 122.308 74.5874 122.451 75.1416C122.593 75.6958 122.51 76.2841 122.22 76.777C121.93 77.27 121.457 77.6272 120.904 77.7701Z" fill="#F2F2F2"/>
                        <path d="M118.623 104.546L69.1411 117.343C68.5886 117.485 68.0022 117.402 67.511 117.111C67.0197 116.82 66.6638 116.345 66.5213 115.791C66.3788 115.238 66.4616 114.649 66.7513 114.157C67.041 113.664 67.514 113.307 68.0663 113.163L117.549 100.367C118.101 100.224 118.688 100.307 119.179 100.598C119.671 100.889 120.027 101.364 120.17 101.918C120.312 102.472 120.229 103.06 119.939 103.553C119.649 104.046 119.176 104.404 118.623 104.546Z" fill="#F2F2F2"/>
                        <path d="M129.031 109.377L70.953 124.396C70.6792 124.467 70.3942 124.483 70.1142 124.443C69.8342 124.404 69.5646 124.31 69.321 124.166C69.0774 124.022 68.8645 123.831 68.6945 123.604C68.5244 123.378 68.4005 123.12 68.3299 122.845C68.2593 122.571 68.2433 122.285 68.2829 122.004C68.3225 121.723 68.4169 121.453 68.5607 121.209C68.7045 120.965 68.8949 120.752 69.121 120.581C69.347 120.411 69.6043 120.287 69.8782 120.216L127.956 105.197C128.509 105.054 129.096 105.137 129.587 105.428C130.079 105.719 130.435 106.194 130.577 106.748C130.72 107.302 130.637 107.891 130.347 108.383C130.057 108.876 129.584 109.234 129.031 109.377Z" fill="#F2F2F2"/>
                        <path d="M44.4375 67.2515L26.9262 71.78C26.6612 71.8482 26.3801 71.8082 26.1444 71.6688C25.9088 71.5294 25.7379 71.3019 25.6693 71.0364L21.6496 55.4053C21.5816 55.1396 21.6215 54.8577 21.7605 54.6214C21.8995 54.3851 22.1263 54.2138 22.3912 54.145L39.9025 49.6165C40.1674 49.5483 40.4486 49.5883 40.6842 49.7277C40.9199 49.8671 41.0907 50.0945 41.1593 50.3601L45.179 65.9911C45.2471 66.2569 45.2072 66.5388 45.0682 66.7751C44.9292 67.0114 44.7023 67.1827 44.4375 67.2515Z" fill="#E6E6E6"/>
                        <path d="M52.5625 98.858L35.0512 103.386C34.7862 103.455 34.5051 103.415 34.2694 103.275C34.0338 103.136 33.8629 102.908 33.7943 102.643L29.7746 87.0118C29.7066 86.746 29.7465 86.4641 29.8855 86.2278C30.0245 85.9915 30.2513 85.8202 30.5162 85.7514L48.0275 81.223C48.2924 81.1548 48.5736 81.1947 48.8092 81.3341C49.0449 81.4735 49.2157 81.701 49.2843 81.9666L53.304 97.5976C53.372 97.8633 53.3322 98.1453 53.1932 98.3815C53.0542 98.6178 52.8273 98.7892 52.5625 98.858Z" fill="#E6E6E6"/>
                        <path d="M60.6914 130.463L43.1801 134.992C42.9151 135.06 42.634 135.02 42.3983 134.881C42.1627 134.741 41.9918 134.514 41.9232 134.248L37.9035 118.617C37.8355 118.352 37.8754 118.07 38.0144 117.833C38.1534 117.597 38.3802 117.426 38.6451 117.357L56.1564 112.828C56.4214 112.76 56.7025 112.8 56.9381 112.94C57.1738 113.079 57.3446 113.306 57.4132 113.572L61.4329 129.203C61.501 129.469 61.4611 129.751 61.3221 129.987C61.1831 130.223 60.9563 130.395 60.6914 130.463Z" fill="#E6E6E6"/>
                        <path d="M175.795 29.6182H74.7432C71.317 29.622 68.0322 30.9886 65.6096 33.418C63.1869 35.8475 61.8242 39.1414 61.8203 42.5771V161.564C61.8242 165 63.1869 168.294 65.6096 170.723C68.0322 173.153 71.317 174.519 74.7432 174.523H175.795C179.221 174.519 182.506 173.153 184.928 170.723C187.351 168.294 188.714 165 188.718 161.564V42.5771C188.714 39.1414 187.351 35.8475 184.928 33.418C182.506 30.9886 179.221 29.622 175.795 29.6182Z" fill="#E6E6E6"/>
                        <path d="M175.794 33.3486H74.7417C72.3019 33.3514 69.9627 34.3245 68.2375 36.0546C66.5122 37.7846 65.5418 40.1303 65.5391 42.577V161.564C65.5418 164.011 66.5122 166.356 68.2375 168.086C69.9627 169.816 72.3019 170.79 74.7417 170.792H175.794C178.233 170.789 180.572 169.816 182.298 168.086C184.023 166.356 184.993 164.011 184.996 161.564V42.577C184.993 40.1303 184.023 37.7847 182.298 36.0546C180.572 34.3246 178.233 33.3514 175.794 33.3486Z" fill="white"/>
                        <path d="M160.584 98.732H109.483C109.2 98.7324 108.92 98.6768 108.658 98.5685C108.397 98.4602 108.159 98.3013 107.959 98.1008C107.759 97.9004 107.6 97.6624 107.492 97.4004C107.384 97.1384 107.328 96.8576 107.328 96.574C107.328 96.2904 107.384 96.0096 107.492 95.7476C107.6 95.4857 107.759 95.2477 107.959 95.0472C108.159 94.8468 108.397 94.6879 108.658 94.5796C108.92 94.4713 109.2 94.4157 109.483 94.416H160.584C161.154 94.4167 161.701 94.6443 162.104 95.0489C162.507 95.4536 162.733 96.0021 162.733 96.574C162.733 97.146 162.507 97.6945 162.104 98.0991C161.701 98.5038 161.154 98.7314 160.584 98.732Z" fill="#E6E6E6"/>
                        <path d="M169.461 106.015H109.483C109.2 106.016 108.92 105.96 108.658 105.852C108.397 105.743 108.159 105.584 107.959 105.384C107.759 105.184 107.6 104.946 107.492 104.684C107.384 104.422 107.328 104.141 107.328 103.857C107.328 103.574 107.384 103.293 107.492 103.031C107.6 102.769 107.759 102.531 107.959 102.33C108.159 102.13 108.397 101.971 108.658 101.863C108.92 101.754 109.2 101.699 109.483 101.699H169.461C170.031 101.699 170.579 101.927 170.982 102.331C171.386 102.736 171.613 103.285 171.613 103.857C171.613 104.43 171.386 104.978 170.982 105.383C170.579 105.788 170.031 106.015 169.461 106.015Z" fill="#E6E6E6"/>
                        <path d="M160.584 131.372H109.483C109.2 131.372 108.92 131.316 108.658 131.208C108.397 131.1 108.159 130.941 107.959 130.74C107.759 130.54 107.6 130.302 107.492 130.04C107.384 129.778 107.328 129.497 107.328 129.214C107.328 128.93 107.384 128.649 107.492 128.387C107.6 128.125 107.759 127.887 107.959 127.687C108.159 127.486 108.397 127.328 108.658 127.219C108.92 127.111 109.2 127.055 109.483 127.056H160.584C161.154 127.056 161.702 127.283 162.105 127.688C162.509 128.092 162.736 128.641 162.736 129.214C162.736 129.786 162.509 130.335 162.105 130.74C161.702 131.144 161.154 131.372 160.584 131.372Z" fill="#E6E6E6"/>
                        <path d="M169.461 138.655H109.483C109.2 138.655 108.92 138.6 108.658 138.491C108.397 138.383 108.159 138.224 107.959 138.024C107.759 137.823 107.6 137.585 107.492 137.323C107.384 137.061 107.328 136.78 107.328 136.497C107.328 136.213 107.384 135.932 107.492 135.67C107.6 135.409 107.759 135.171 107.959 134.97C108.159 134.77 108.397 134.611 108.658 134.502C108.92 134.394 109.2 134.339 109.483 134.339H169.461C169.743 134.339 170.024 134.394 170.285 134.502C170.546 134.611 170.784 134.77 170.984 134.97C171.184 135.171 171.343 135.409 171.451 135.67C171.559 135.932 171.615 136.213 171.615 136.497C171.615 136.78 171.559 137.061 171.451 137.323C171.343 137.585 171.184 137.823 170.984 138.024C170.784 138.224 170.546 138.383 170.285 138.491C170.024 138.6 169.743 138.655 169.461 138.655Z" fill="#E6E6E6"/>
                        <path d="M98.038 109.321H79.9538C79.6802 109.321 79.4179 109.212 79.2244 109.018C79.031 108.824 78.9222 108.561 78.9219 108.287V92.1441C78.9222 91.8698 79.031 91.6068 79.2244 91.4128C79.4179 91.2188 79.6802 91.1097 79.9538 91.1094H98.038C98.3115 91.1097 98.5738 91.2188 98.7673 91.4128C98.9607 91.6068 99.0696 91.8698 99.0699 92.1441V108.287C99.0696 108.561 98.9607 108.824 98.7673 109.018C98.5738 109.212 98.3115 109.321 98.038 109.321Z" fill="#E6E6E6"/>
                        <path d="M98.038 141.961H79.9538C79.6802 141.961 79.4179 141.852 79.2244 141.658C79.031 141.464 78.9222 141.201 78.9219 140.926V124.784C78.9222 124.509 79.031 124.246 79.2244 124.052C79.4179 123.858 79.6802 123.749 79.9538 123.749H98.038C98.3115 123.749 98.5738 123.858 98.7673 124.052C98.9607 124.246 99.0696 124.509 99.0699 124.784V140.926C99.0696 141.201 98.9607 141.464 98.7673 141.658C98.5738 141.852 98.3115 141.961 98.038 141.961Z" fill="#E6E6E6"/>
                        <path d="M160.643 62.3971H122.968C122.398 62.3971 121.85 62.1697 121.447 61.765C121.043 61.3603 120.816 60.8114 120.816 60.2391C120.816 59.6667 121.043 59.1178 121.447 58.7131C121.85 58.3084 122.398 58.0811 122.968 58.0811H160.643C161.214 58.0811 161.761 58.3084 162.165 58.7131C162.568 59.1178 162.795 59.6667 162.795 60.2391C162.795 60.8114 162.568 61.3603 162.165 61.765C161.761 62.1697 161.214 62.3971 160.643 62.3971Z" fill="#CCCCCC"/>
                        <path d="M169.52 69.6803H122.968C122.686 69.6803 122.406 69.6245 122.145 69.516C121.884 69.4076 121.647 69.2486 121.447 69.0482C121.247 68.8478 121.088 68.6099 120.98 68.3481C120.872 68.0863 120.816 67.8057 120.816 67.5223C120.816 67.2389 120.872 66.9583 120.98 66.6964C121.088 66.4346 121.247 66.1967 121.447 65.9963C121.647 65.7959 121.884 65.637 122.145 65.5285C122.406 65.4201 122.686 65.3643 122.968 65.3643H169.52C170.091 65.3643 170.638 65.5916 171.042 65.9963C171.445 66.401 171.672 66.9499 171.672 67.5223C171.672 68.0946 171.445 68.6435 171.042 69.0482C170.638 69.4529 170.091 69.6803 169.52 69.6803Z" fill="#CCCCCC"/>
                        <path d="M114.628 78.5072H79.8952C79.6216 78.5069 79.3593 78.3978 79.1658 78.2038C78.9724 78.0098 78.8636 77.7468 78.8633 77.4724V50.2896C78.8636 50.0153 78.9724 49.7523 79.1658 49.5583C79.3593 49.3643 79.6216 49.2552 79.8952 49.2549H114.628C114.902 49.2552 115.164 49.3643 115.357 49.5583C115.551 49.7523 115.66 50.0153 115.66 50.2896V77.4724C115.66 77.7468 115.551 78.0098 115.357 78.2038C115.164 78.3978 114.902 78.5069 114.628 78.5072Z" fill="#E84A5F"/>
                    </svg>
                </div>
                <h3 class="mb-0">
                    No Data Found!!
                </h3>
            </div>
        </div>`,
        className: 'asd'

    });
    modal.open();
}

export function setChartTheme(root, theme = 'default'){
    switch(theme){
        case "default":
            root.setThemes([am5themes_Animated.new(root)]);
            break;
        case "dark":
            root.setThemes([am5themes_Dataviz.new(root)]);
            break;
        case "material":
            root.setThemes([am5themes_Material.new(root)]);
            break;
        case "moonrise":
            root.setThemes([am5themes_Moonrise.new(root)]);
            break;
    };
}

    // TODO: Add zooming_enabled, view

export function renderGraph(rootObj, rootEl, chartConfig, itemConfig, canvasClickCallback, chartType=false){
    try {
//        let $ks_gridstack_container = chartRootElement

//        var self = this;
//        let graph_render = chartRootElement;
//        if(view === 'dashboard_view'){
//            if($ks_gridstack_container.find('.ks_chart_card_body').length){
//                graph_render = $ks_gridstack_container.find('.ks_chart_card_body')[0];
//            }else{
//                $($ks_gridstack_container.find('.ks_dashboarditem_chart_container')[0]).append("<div class='card-body ks_chart_card_body'>");
//                graph_render = $ks_gridstack_container.find('.ks_chart_card_body')[0];
//            }
//        }
//        else if(view === 'preview'){
//            if($ks_gridstack_container.find(".graph_text").length){
//                $ks_gridstack_container.find(".graph_text").remove();
//            }
//            graph_render = $ks_gridstack_container[0]
//        }
        rootObj.dispose?.()

        const isRtl = localization.direction === "rtl"
        const chart_data = chartConfig;
        const theme = itemConfig.ks_chart_item_color
        const root  = am5.Root.new(rootEl);
        const data_format = itemConfig.ks_data_format
        const isStackedBarChart = itemConfig.ks_bar_chart_stacked
        const zooming_enabled = itemConfig.zooming_enabled

        let item = itemConfig
        let ks_labels = chart_data['labels'];
        let ks_data = chart_data.datasets;
        let chart_type = chartType || item.ks_dashboard_item_type
        let data = []

        if(item.ks_chart_cumulative_field && ks_data?.length){
            for(var i=0;i<ks_data.length;i++){
                var ks_temp_com = 0;
                var datasets = {};
                var cumulative_data = []
                if(ks_data[i].ks_chart_cumulative_field){
                    for(var j=0; j< ks_data[i].data.length; j++){
                        ks_temp_com = ks_temp_com + ks_data[i].data[j];
                        cumulative_data.push(ks_temp_com);
                    }
                    datasets.label = 'Cumulative ' + ks_data[i].label;
                    datasets.data = cumulative_data;
                    if(item.ks_chart_cumulative){
                        datasets.type = 'line';
                    }
                    ks_data.push(datasets);
                }
            }
        }



        if (ks_data && ks_labels && ks_data.length && ks_labels.length){
            setChartTheme(root, theme);

            for (let i = 0 ; i < ks_labels.length ; i++){
                let data2 = {}
                for (let dataObj of ks_data){
                    data2[dataObj.label] = dataObj.data[i]
                }
                data2["category"] = ks_labels[i]
                data.push(data2)
            }

            switch (chart_type) {
                    case "ks_bar_chart":
                    case "ks_bullet_chart":
                        var wheely_val = zooming_enabled ? "zoomX" : "none"

                        var chart = root.container.children.push(am5xy.XYChart.new(root, {
                                                                        panX: false, panY: false, wheelX: "panX",
                                                                        wheelY: wheely_val, layout: root.verticalLayout
                                                                    }))
                        var xRenderer = am5xy.AxisRendererX.new(root, {
                                            minGridDistance: 15,
                                            minorGridEnabled: true
                                        })

                        var rotations_angle = chart_type == 'ks_bar_chart' ? -45 : -90

                        xRenderer.labels.template.setAll({
                            direction: "rtl",
                            rotation: rotations_angle,
                            centerY: am5.p50,
                            centerX: am5.p100,
                            paddingRight: 10
                        })

                        var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {categoryField: "category",
                        renderer: xRenderer,tooltip: am5.Tooltip.new(root, {})}));

                        xRenderer.grid.template.setAll({location: 1})

                        xAxis.data.setAll(data);

                        var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {extraMin: 0,
                        extraMax: 0.1,renderer: am5xy.AxisRendererY.new(root, {strokeOpacity: 0.1}) }));

                        let label_format_text = data_format === "exact" ? "{valueY.formatNumber('0.00')}" : "{valueY}";

                        if(isRtl){
                            yAxis.get("renderer").labels.template.setAll({
                                paddingRight: 30,
                                paddingLeft: 30
                            });
                        }
                        // Add series

                        for (let k = 0; k < ks_data.length ; k++){
                            if (chart_type == "ks_bar_chart" && isStackedBarChart == true && ks_data[k].type != "line"){
                                var tooltip = am5.Tooltip.new(root, {
                                    pointerOrientation: "horizontal",
                                    textAlign: "center",
                                    centerX: am5.percent(96),
                                    labelText: `{categoryX}, {name}: ${label_format_text}`
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })

                                var series = chart.series.push(am5xy.ColumnSeries.new(root, {
                                    stacked: true,
                                    name: `${ks_data[k].label}`,
                                    xAxis: xAxis,
                                    yAxis: yAxis,
                                    valueYField:`${ks_data[k].label}`,
                                    categoryXField: "category",
                                    tooltip: tooltip
                                }));
                                series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) )
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                series.data.setAll(data);
                            }
                            else if (chart_type == "ks_bar_chart" && ks_data[k].type != "line"){
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96),
                                    pointerOrientation: "horizontal",
                                    labelText: "{categoryX}, {name}: {valueY}"
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })

                                var series = chart.series.push(am5xy.ColumnSeries.new(root, {
                                    name: `${ks_data[k].label}`,
                                    xAxis: xAxis,
                                    yAxis: yAxis,
                                    valueYField:`${ks_data[k].label}`,
                                    categoryXField: "category",
                                    tooltip: tooltip

                                }));
                                series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                series.data.setAll(data);

                            }
                            else if (chart_type == "ks_bullet_chart"){
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96),
                                    labelText: `${ks_data[k].label}: {valueY}`
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })

                                var series = chart.series.push(am5xy.ColumnSeries.new(root, {
                                name: `${ks_data[k].label}`,
                                xAxis: xAxis,
                                yAxis: yAxis,
                                valueYField:`${ks_data[k].label}`,
                                categoryXField: "category",
                                clustered: false,
                                tooltip: tooltip
                                }));

                                series.columns.template.setAll({
                                    width: am5.percent(80-(10*k)),
                                    tooltipY: 0,
                                    strokeOpacity: 0
                                });
                                series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                series.data.setAll(data);
                            }

                            if (item.ks_show_records == true && series){
                                series.columns.template.setAll({
                                    tooltipY: 0,
                                    templateField: "columnSettings"
                               });
                                var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
                                        behavior: "zoomY"
                                }));
                               cursor.lineY.set("forceHidden", true);
                               cursor.lineX.set("forceHidden", true);
                            }
                            if (item.ks_show_data_value == true && series){
                                series.bullets.push(function () {
                                    return am5.Bullet.new(root, {
                                            sprite: am5.Label.new(root, {
                                              text:  label_format_text,
                                              centerY: am5.p100,
                                              centerX: am5.p50,
                                              populateText: true,
                                              ...(isRtl && {direction: "rtl"}),
                                            })
                                    });
                                });
                            }
                            if (chart_type == "ks_bar_chart" && item.ks_chart_measure_field_2 && ks_data[k].type == "line"){
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96),
                                    pointerOrientation: "horizontal",
                                    labelText: "{categoryX}, {name}: {valueY}"
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })

                                var series2 = chart.series.push(
                                    am5xy.LineSeries.new(root, {
                                        name: `${ks_data[k].label}`,
                                        xAxis: xAxis,
                                        yAxis: yAxis,
                                        valueYField:`${ks_data[k].label}`,
                                        categoryXField: "category",
                                        tooltip: tooltip
                                    })
                                );

                                series2.strokes.template.setAll({strokeWidth: 3,templateField: "strokeSettings"});
                                series2.strokes.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                series2.data.setAll(data);

                                series2.bullets.push(function() {
                                    return am5.Bullet.new(root, {
                                        sprite: am5.Circle.new(root, {
                                            strokeWidth: 3,
                                            stroke: series2.get("stroke"),
                                            radius: 5,
                                            fill: root.interfaceColors.get("background")
                                        })
                                    });
                                });
                            }
                        }
                        break;
                    case "ks_horizontalBar_chart":
                        var wheely_val = zooming_enabled ? "zoomX" : "none"
                        var chart = root.container.children.push(am5xy.XYChart.new(root, {
                                                panX: false, panY: false, wheelX: "panX",
                                                wheelY: wheely_val, layout: root.verticalLayout
                                            }));
                        var yRenderer = am5xy.AxisRendererY.new(root, {
                                inversed: true,
                                minGridDistance: 30,
                                minorGridEnabled: true,
                                cellStartLocation: 0.1,
                                cellEndLocation: 0.9
                            })
                        yRenderer.labels.template.setAll({
                              direction: "rtl",
                        });
                        var yAxis = chart.yAxes.push(am5xy.CategoryAxis.new(root, {
                            categoryField: "category",
                            renderer: yRenderer
                        }))

                    yAxis.data.setAll(data);

                    var xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, {
                        renderer: am5xy.AxisRendererX.new(root, {
                            strokeOpacity: 0.1
                        }),
                        min: 0
                    }));
                    for (let k = 0;k<ks_data.length ; k++){
                        var tooltip = am5.Tooltip.new(root, {
                            textAlign: "center",
                            centerX: am5.percent(96),
                            pointerOrientation: "horizontal",
                            labelText: "{categoryY}, {name}: {valueX}"
                        });

                        tooltip.label.setAll({
                            direction: "rtl"
                        })

                    if (isStackedBarChart == true){
                        var series = chart.series.push(am5xy.ColumnSeries.new(root, {
                            stacked: true,
                            name: `${ks_data[k].label}`,
                            xAxis: xAxis,
                            yAxis: yAxis,
                            valueXField:`${ks_data[k].label}`,
                            categoryYField: "category",
                            sequencedInterpolation: true,
                            tooltip: tooltip
                        }));

                    }else if (chart_type == "ks_horizontalBar_chart" && ks_data[k].type != "line"){
                        var series = chart.series.push(am5xy.ColumnSeries.new(root, {
                            name: `${ks_data[k].label}`,
                            xAxis: xAxis,
                            yAxis: yAxis,
                            valueXField:`${ks_data[k].label}`,
                            categoryYField: "category",
                            sequencedInterpolation: true,
                            tooltip: tooltip

                        }));
                    }
                        if (item.ks_show_records == true && series){
                            series.columns.template.setAll({
        //                        width: am5.percent(80-(10*k)),
                                height: am5.p100,
                                strokeOpacity: 0
                           });
                           var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
                                    behavior: "zoomY"
                            }));
                           cursor.lineY.set("forceHidden", true);
                           cursor.lineX.set("forceHidden", true);
                        }
                        if (item.ks_show_data_value == true && series){
                            let label_format_text = data_format === "exact" ? "{valueX.formatNumber('0.00')}" : "{valueX}"
                            series.bullets.push(function () {
                                return am5.Bullet.new(root, {
        //                            locationX: 1,
                                        sprite: am5.Label.new(root, {
                                          text:  label_format_text,
                                          centerY: am5.p50,
                                          centerX: am5.p50,
                                          populateText: true,
                                          ...(isRtl && {direction: "rtl"})
                                        })
                                });
                            });
                        }
                        if (series){
                            series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                    self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                }
//                            });

                            series.data.setAll(data);
                        }

                     if (chart_type == "ks_horizontalBar_chart" && ks_data[k].type == "line"){
                        var series2 = chart.series.push(
                            am5xy.LineSeries.new(root, {
                                name: `${ks_data[k].label}`,
                                xAxis: xAxis,
                                yAxis: yAxis,
                                valueXField:`${ks_data[k].label}`,
                                categoryYField: "category",
                                sequencedInterpolation: true,
                                tooltip: am5.Tooltip.new(root, {
                                    pointerOrientation: "horizontal",
                                    labelText: "{categoryY}, {name}: {valueX}"
                                })
                            })
                        );

                        series2.strokes.template.setAll({strokeWidth: 3,templateField: "strokeSettings"});
                        series2.strokes.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                            if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                            }
//                        });


                        series2.bullets.push(function() {
                            return am5.Bullet.new(root, {
                                sprite: am5.Circle.new(root, {
                                    strokeWidth: 3,
                                    stroke: series2.get("stroke"),
                                    radius: 5,
                                    fill: root.interfaceColors.get("background")
                                })
                            });
                        });
                         series2.data.setAll(data);
                    }
                }
                break;
                case "ks_line_chart":
                case "ks_area_chart":
                    if(zooming_enabled){
                        var wheely_val = "zoomX";
                    }else{
                        var wheely_val = 'none';
                    }

                    var chart = root.container.children.push(am5xy.XYChart.new(root, {panX: false,panY: false,
                    wheelX: "panX",wheelY: wheely_val,layout: root.verticalLayout}));
                    var xRenderer = am5xy.AxisRendererX.new(root, {
                        minGridDistance: 15,
                        minorGridEnabled: true
                        });
                    xRenderer.labels.template.setAll({
                          direction: "rtl",
                      rotation: -45,
                      centerY: am5.p50,
                      centerX: am5.p100,
                      paddingRight: 10
                    });
                    var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
                        categoryField: "category",
                        maxDeviation: 0.2,
                        renderer: xRenderer,
                        tooltip: am5.Tooltip.new(root, {})
                    }));
                    xAxis.data.setAll(data);

                    var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {extraMin: 0,
                    extraMax: 0.1,renderer: am5xy.AxisRendererY.new(root, {strokeOpacity: 0.1}) }));

                     if(isRtl){
                        yAxis.get("renderer").labels.template.setAll({
                            paddingRight: 30,
                            paddingLeft: 30
                        });
                     }

                    for (let k = 0;k<ks_data.length ; k++){

                        var tooltip = am5.Tooltip.new(root, {
                            textAlign: "center",
                            centerX: am5.percent(96),
                            labelText: "[bold]{categoryX}[/]\n{name}: {valueY}"
                        });
                        tooltip.label.setAll({
                            direction: "rtl"
                        })

                        var series = chart.series.push(am5xy.LineSeries.new(root, {
                            name: `${ks_data[k].label}`,
                            xAxis: xAxis,
                            yAxis: yAxis,
                            valueYField: `${ks_data[k].label}`,
                            categoryXField: "category",
                            alignLabels: true,
                            tooltip: tooltip
                        }));
                        series.strokes.template.setAll({strokeWidth: 2,templateField: "strokeSettings"});

                        series.bullets.push(function() {
                            var graphics = am5.Rectangle.new(root, {
                                width:7,
                                height:7,
                                centerX:am5.p50,
                                centerY:am5.p50,
                                fill: series.get("stroke")
                            });
                            if (chart_type == "ks_area_chart" || chart_type == "ks_line_chart"){
                                graphics.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                            }
                            return am5.Bullet.new(root, {
                                sprite: graphics
                            });
                        });
                        if (item.ks_show_data_value == true && series){
                            let label_format_text = data_format === "exact" ? "{valueY.formatNumber('0.00')}" : "{valueY}"
                            series.bullets.push(function () {
                                return am5.Bullet.new(root, {
                                    sprite: am5.Label.new(root, {
                                        text:  label_format_text,
                                        centerX:am5.p50,
                                        centerY:am5.p100,
                                        populateText: true,
                                        ...(isRtl && {direction: "rtl"})
                                     })
                                });
                            });
                        }
                        if (chart_type === "ks_area_chart"){
                            series.fills.template.setAll({
                                fillOpacity: 0.5,
                                visible: true
                            });
                        }

                        series.data.setAll(data);
                    }

                    if (item.ks_show_records == true){
                        var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
                            behavior: "none"
                        }));
                        cursor.lineY.set("forceHidden", true);
                        cursor.lineX.set("forceHidden", true);

                    }
                    break;
                    case "ks_pie_chart":
                    case "ks_doughnut_chart":
                        var series = []
                        if (item.ks_semi_circle_chart == true && (chart_type == "ks_pie_chart" || chart_type == "ks_doughnut_chart")){
                             if (chart_type == 'ks_doughnut_chart'){
                                var chart = root.container.children.push(
                                    am5percent.PieChart.new(root, {
                                       innerRadius : am5.percent(50),
                                       layout: root.verticalLayout,
                                       startAngle: 180,
                                       endAngle: 360,
                                }));
                            }else{
                                var chart = root.container.children.push(
                                    am5percent.PieChart.new(root, {
                                        radius: am5.percent(90),
                                        layout: root.verticalLayout,
                                        startAngle: 180,
                                        endAngle: 360,
                                    }));
                            }
                            var legend = chart.children.push(am5.Legend.new(root, {
                              centerX: am5.percent(50),
                              x: am5.percent(50),
                              layout: am5.GridLayout.new(root, {
                                maxColumns: 3,
                                fixedWidthGrid: true
                              }),
                              y: am5.percent(100),
                              centerY: am5.percent(100),
                              reverseChildren: true,
                            }));
                            if(isRtl){
                               legend.labels.template.setAll({
                                   textAlign: "right"
                               });
                               legend.itemContainers.template.setAll({
                                    reverseChildren: true,
                                    paddingLeft: 20,
                                    paddingRight: 20,
                               });
                           }
                            for (let k = 0;k<ks_data.length ; k++){
                                series[k] = chart.series.push(
                                    am5percent.PieSeries.new(root, {
                                    name: `${ks_data[k].label}`,
                                    valueField: `${ks_data[k].label}`,
                                    categoryField: "category",
                                    alignLabels: false,
                                    startAngle: 180,
                                    endAngle: 360,
                                }));
                            }
                        }else{
                            if (chart_type == "ks_doughnut_chart"){
                                var chart = root.container.children.push(
                                    am5percent.PieChart.new(root, {
                                    innerRadius: am5.percent(50),
                                    layout: root.verticalLayout,
                                }));
                            }else{
                                var chart = root.container.children.push(
                                    am5percent.PieChart.new(root, {
                                    radius: am5.percent(90),
                                    layout: root.verticalLayout,
                                }));
                            }

                           var legend = chart.children.push(am5.Legend.new(root, {
                              centerX: am5.percent(50),
                              x: am5.percent(50),
                              layout: am5.GridLayout.new(root, {
                                maxColumns: 3,
                                fixedWidthGrid: true
                              }),
                              y: am5.percent(100),
                              centerY: am5.percent(100),
                              reverseChildren: true,
                            }));
                           if(isRtl){
                               legend.labels.template.setAll({
                                   textAlign: "right",
    //                               marginLeft: 5,
                               });
                               legend.itemContainers.template.setAll({
                                    reverseChildren: true,
                                    paddingLeft: 20,
                                    paddingRight: 20,
                               });
                           }

                           for (let k = 0;k<ks_data.length ; k++){
                                series[k] = chart.series.push(
                                    am5percent.PieSeries.new(root, {
                                    name: `${ks_data[k].label}`,
                                    valueField: `${ks_data[k].label}`,
                                    categoryField: "category",
                                    alignLabels: false,
                                })
                                );
                            }
                        }
                        var bgColor = root.interfaceColors.get("background");
                        for (let rec of series){
                            rec.ticks.template.setAll({ forceHidden: true })
                            rec.slices.template.setAll({
                                stroke: bgColor,
                                strokeWidth: 2,
                                templateField: "settings",
                            });
                            rec.slices.template.events.on("click", function(ev) {
                                rec.slices.each(function(slice) {
                                    if(slice == ev.target){
                                        canvasClickCallback(ev);
                                    }

//                                    if(slice == ev.target && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard'] && item.ks_data_calculation_type === 'custom'){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
                                })
                            });

                            if (item.ks_show_records == true){
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96)
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })
                                rec.slices.template.setAll({
                                    tooltipText: "[bold]{category}[/]\n{name}: {value}",
                                    tooltip: tooltip
                                });
                            }
                            if (item.ks_show_data_value == true){
                                rec.labels.template.setAll({
                                    text: item.ks_data_label_type == 'value' ? "{value}" : ("{valuePercentTotal}%"),
                                    inside: true,
                                    textType: data?.length>10? "radial" : "circular",
                                    centerX: am5.percent(80)
                                })
                            }
                            else{
                                rec.labels.template.setAll({forceHidden:true})
                            }
                            rec.data.setAll(data)
                             if(item.ks_hide_legend == true && series){
                                legend.data.setAll(rec.dataItems);
                             }

                            rec.appear(1000, 100);
                        }
    //                    legend.data.setAll(chart.series.values);

    //                    root.rtl = true
                        break;
                    case "ks_polarArea_chart":
                    case "ks_radar_view":
                    case "ks_flower_view":
                    case "ks_radialBar_chart":
                        if(zooming_enabled){
                            var wheely_val = "zoomX";
                        }else{
                            var wheely_val = 'none';
                        }
                        var chart = root.container.children.push(am5radar.RadarChart.new(root, {
                            panX: false,
                            panY: false,
                            wheelX: "panX",
                            wheelY: wheely_val,
                            radius: am5.percent(80),
                            layout: root.verticalLayout,
                        }));

                        if (chart_type == "ks_flower_view"){
                            var xRenderer = am5radar.AxisRendererCircular.new(root, {});
                            xRenderer.labels.template.setAll({
                                radius: 10,
                                cellStartLocation: 0.2,
                                cellEndLocation: 0.8
                            });
                        }else if (chart_type == "ks_radialBar_chart"){
                            var xRenderer = am5radar.AxisRendererCircular.new(root, {
                                strokeOpacity: 0.1,
                                minGridDistance: 50
                             });
                            xRenderer.labels.template.setAll({
                                radius: 23,
                                maxPosition: 0.98
                            });
                        }else{
                            var xRenderer = am5radar.AxisRendererCircular.new(root, {});
                            xRenderer.labels.template.setAll({
                                radius: 10,
                            });
                        }
                        if (chart_type == "ks_radialBar_chart"){
                            var xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, {
                                renderer: xRenderer,
                                extraMax: 0.1,
                                tooltip: am5.Tooltip.new(root, {})
                            }));

                            var yAxis = chart.yAxes.push(am5xy.CategoryAxis.new(root, {
                                categoryField: "category",
                                renderer: am5radar.AxisRendererRadial.new(root, { minGridDistance: 20 })
                            }));
                            yAxis.get("renderer").labels.template.setAll({
                                oversizedBehavior: "truncate",
                                textAlign: "center",
                                maxWidth: 150,
                                ellipsis: "..."
                            });
                        }else{
                            var xAxis = chart.xAxes.push(am5xy.CategoryAxis.new(root, {
                                maxDeviation: 0,
                                categoryField: "category",
                                renderer: xRenderer,
                                tooltip: am5.Tooltip.new(root, {})
                            }));
                            xAxis.data.setAll(data);

                            var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
                                renderer: am5radar.AxisRendererRadial.new(root, {})
                            }));
                        }
                        if (chart_type == "ks_polarArea_chart"){
                            for (let k = 0;k<ks_data.length ; k++) {
                                var series = chart.series.push(am5radar.RadarColumnSeries.new(root, {
                                    stacked: true,
                                    name: `${ks_data[k].label}`,
                                    xAxis: xAxis,
                                    yAxis: yAxis,
                                    valueYField: `${ks_data[k].label}`,
                                    categoryXField: "category",
                                    alignLabels: true,
                                }));

                            series.set("stroke", root.interfaceColors.get("background"));
                            if (item.ks_show_records == true){
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96)
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })
                                series.columns.template.setAll({
                                    width: am5.p100,
                                    strokeOpacity: 0.1,
                                    tooltipText: "{name}: {valueY}",
                                    tooltip: tooltip
                                });
                            }
                            series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                    self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                }
//                            });
                            series.data.setAll(data);
                            }
                            xAxis.data.setAll(data);
                        }else if (chart_type == "ks_flower_view"){
                            for (let k = 0;k<ks_data.length ; k++){
                                var series = chart.series.push(
                                    am5radar.RadarColumnSeries.new(root, {
                                    name: `${ks_data[k].label}`,
                                    xAxis: xAxis,
                                    yAxis: yAxis,
                                    valueYField: `${ks_data[k].label}`,
                                    categoryXField: "category"
                                 })
                                );

                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96)
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })

                                series.columns.template.setAll({
                                    tooltip: tooltip,
                                    tooltipText: "{name}: {valueY}",
                                    width: am5.percent(100)
                                });
                                series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                series.data.setAll(data);
                            }

                        }else if (chart_type == "ks_radialBar_chart"){
                            for (let k = 0;k<ks_data.length ; k++) {
                                var series = chart.series.push(am5radar.RadarColumnSeries.new(root, {
                                    stacked: true,
                                    name: `${ks_data[k].label}`,
                                    xAxis: xAxis,
                                    yAxis: yAxis,
                                    valueXField: `${ks_data[k].label}`,
                                    categoryYField: "category"
                                }));

                                series.set("stroke",root.interfaceColors.get("background"));
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96)
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })

                                series.columns.template.setAll({
                                    width: am5.p100,
                                    strokeOpacity: 0.1,
                                    tooltipText: "{name}: {valueX}  {category}",
                                    tooltip: tooltip
                                });
                                series.columns.template.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                series.data.setAll(data);
                            }
                            yAxis.data.setAll(data);
                       }else{
                            for (let k = 0;k<ks_data.length ; k++){
                                var tooltip = am5.Tooltip.new(root, {
                                    textAlign: "center",
                                    centerX: am5.percent(96),
                                    labelText: "{valueY}"
                                });
                                tooltip.label.setAll({
                                    direction: "rtl"
                                })
                                var series = chart.series.push(am5radar.RadarLineSeries.new(root, {
                                    name:`${ks_data[k].label}`,
                                    xAxis: xAxis,
                                    yAxis: yAxis,
                                    valueYField: `${ks_data[k].label}`,
                                    categoryXField: "category",
                                    alignLabels: true,
                                    tooltip: tooltip
                                }));

                                series.strokes.template.setAll({
                                strokeWidth: 2,

                                });
                            series.bullets.push(function() {
                                var graphics = am5.Circle.new(root, {
                                    fill: series.get("fill"),
                                    radius: 5
                                });
                                graphics.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                return am5.Bullet.new(root, {
                                    sprite: graphics
                                });
                            });
                            series.data.setAll(data);
                        }
                            xAxis.data.setAll(data);
                       }

                        break;

                    case "ks_scatter_chart":
                    if(zooming_enabled){
                            var wheely_val = "zoomX";
                        }else{
                            var wheely_val = 'none';
                        }
                    var chart = root.container.children.push(am5xy.XYChart.new(root, {panX: false,panY: false,
                     wheelX: "panX",wheelY: wheely_val,layout: root.verticalLayout}));
                        var xAxis = chart.xAxes.push(am5xy.ValueAxis.new(root, {
                            renderer: am5xy.AxisRendererX.new(root, { minGridDistance: 50 }),
                            tooltip: am5.Tooltip.new(root, {})
                        }));
                        xAxis.ghostLabel.set("forceHidden", true);

                        var yAxis = chart.yAxes.push(am5xy.ValueAxis.new(root, {
                            renderer: am5xy.AxisRendererY.new(root, {}),
                            tooltip: am5.Tooltip.new(root, {})
                        }));
                        yAxis.ghostLabel.set("forceHidden", true);

                        var tooltip = am5.Tooltip.new(root, {
                            textAlign: "center",
                            centerX: am5.percent(96),
                            labelText: "{name_1}:{valueX} {name}:{valueY}"
                        });
                        tooltip.label.setAll({
                                direction: "rtl"
                        })

                        for (let k = 0;k<ks_data.length ; k++){
                            var series = chart.series.push(am5xy.LineSeries.new(root, {
                                name:`${ks_data[k].label}`,
                                name_1 : chart_data.groupby,
                                calculateAggregates: true,
                                xAxis: xAxis,
                                yAxis: yAxis,
                                valueYField: `${ks_data[k].label}`,
                                valueXField: "category",
                                tooltip: tooltip
                            }));

                            series.bullets.push(function() {
                                var graphics = am5.Triangle.new(root, {
                                    fill: series.get("fill"),
                                    width: 10,
                                    height: 7
                                });
                                graphics.events.on("click", (ev) => canvasClickCallback(ev) );
//                                    if (item.ks_data_calculation_type === 'custom' && self.ks_dashboard_data && !self.ks_dashboard_data['ks_ai_dashboard']){
//                                        self.onChartCanvasClick_funnel(ev,`${item.id}`, item)
//                                    }
//                                });
                                return am5.Bullet.new(root, {
                                    sprite: graphics
                                });
                            });
                             var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
                                behavior: "none",
                                snapToSeries: [series]
                                }));
                                cursor.lineY.set("forceHidden", true);
                                cursor.lineX.set("forceHidden", true);
                            series.strokes.template.set("strokeOpacity", 0);
                            series.data.setAll(data);

                        }
                        break;
                }







    //            if(chart_type == 'ks_radar_view'|| chart_type == 'ks_radialBar_chart'|| chart_type == 'ks_flower_view'|| chart_type == 'ks_polarArea_chart'){
                root.rtl=true;
                var legend = chart.children.push(
                    am5.Legend.new(root, {
                        centerX: am5.p50,
                        x: am5.p50,
                        layout: root.gridLayout,
                        y: am5.percent(100),
                        centerY: am5.percent(100),
    //                    ...(isRtl && {direction: "rtl"}),
                    })
                );

                legend.labels.template.setAll({
                    textAlign: "right",
                    marginRight:5,
    //                ...(isRtl && {direction: "rtl"}),
                });
                legend.itemContainers.template.setAll({
                    reverseChildren: true,
                });
    //            }
    //            else {
    //                root.rtl=true;
    //                var legend = chart.children.push(
    //                    am5.Legend.new(root, {
    //                        centerX: am5.p50,
    //                        x: am5.p50,
    //                        layout: root.gridLayout,
    //                        y: am5.percent(100),
    //                        centerY: am5.percent(100),
    //                    })
    //                );
    //
    //                legend.labels.template.setAll({
    //                  textAlign: "right",
    //                  marginRight:5
    //                });
    //                legend.itemContainers.template.setAll({
    //                      reverseChildren: true
    //                    });
    //            }
                if(item.ks_hide_legend == true && series && chart_type != 'ks_pie_chart' && chart_type != 'ks_doughnut_chart'){
                    legend.data.setAll(chart.series.values);
                }


                if (data_format && data_format == 'global'){
                    root.numberFormatter.setAll({
                        numberFormat: "#.0a",
                        bigNumberPrefixes: [{"number":1e+3,"suffix":"k"},{ "number": 1e+6, "suffix": "M" },
                        { "number": 1e+9, "suffix": "G" },{ "number": 1e+12, "suffix": "T" },
                        { "number": 1e+15, "suffix": "P" },{ "number": 1e+18, "suffix": "E" }]
                    });
                }else if (data_format && data_format == 'indian'){
                    root.numberFormatter.setAll({
                        numberFormat: "#.0a",
                        bigNumberPrefixes: [{"number":1e+3,"suffix":"Th"},{"number":1e+5,"suffix":"Lakh"},
                        { "number": 1e+7, "suffix": "Cr" },{ "number": 1e+9, "suffix": "Arab" }],
                    });
                }else if (data_format && data_format == 'colombian'){
                    root.numberFormatter.setAll({
                        numberFormat: "#.a",
                        bigNumberPrefixes: [{"number":1e+6,"suffix":"M"},{ "number": 1e+9, "suffix": "M" },{ "number": 1e+12, "suffix": "M" },
                        { "number": 1e+15, "suffix": "M" },{ "number": 1e+18, "suffix": "M" }]
                    });
                }else{
                    root.numberFormatter.setAll({
                        numberFormat: "#"
                    });
                }
                chart.appear(1000, 100);

                if (chart_type != 'ks_pie_chart' &&  chart_type != 'ks_doughnut_chart' && series){
                    series.appear();
                }
        }
        else{
            renderNoDataGraph(root)
//            view === 'dashboard_view' ? $ks_gridstack_container.find('.ks_chart_card_body').append(renderToString("ksNoItemChartView", {})) : $ks_gridstack_container.append(renderToString("ksNoItemChartView", {}))
        }
        return root;
    }
    catch(e){
        console.error("Chart doesn't rendered")
    }
}

export function renderFunnelGraph(rootObj, rootEl, chartConfig, itemConfig, canvasClickCallback, chartType=false){
            rootObj?.dispose?.()
            var self =this;
            const isRtl = localization.direction === "rtl"
            let item = itemConfig
            var funnel_data = chartConfig
            try{
                let root = am5.Root.new(rootEl)
                if(funnel_data['labels'] && funnel_data['datasets'].length){
                var ks_labels = funnel_data['labels'];
                var ks_data = funnel_data.datasets[0].data;
                const ks_sortobj = Object.fromEntries(ks_labels.map((key, index) => [key, ks_data[index]]),);
                const keyValueArray = Object.entries(ks_sortobj);
                keyValueArray.sort((a, b) => b[1] - a[1]);

                var data=[];
                if (keyValueArray.length){
                    for (let i=0 ; i<keyValueArray.length ; i++){
                        data.push({"stage":keyValueArray[i][0],"applicants":keyValueArray[i][1]})
                    }

//                    this.root = root
                    const theme = item.ks_chart_item_color
                    switch(theme){
                    case "default":
                        root.setThemes([am5themes_Animated.new(root)]);
                        break;
                    case "dark":
                        root.setThemes([am5themes_Dataviz.new(root)]);
                        break;
                    case "material":
                        root.setThemes([am5themes_Material.new(root)]);
                        break;
                    case "moonrise":
                        root.setThemes([am5themes_Moonrise.new(root)]);
                        break;
                    };

                    var chart = root.container.children.push(
                        am5percent.SlicedChart.new(root, {
                            layout: root.verticalLayout
                        })
                    );
                    // Create series
                    var series = chart.series.push(
                        am5percent.FunnelSeries.new(root, {
                            alignLabels: false,
                            name: "Series",
                            valueField: "applicants",
                            categoryField: "stage",
                            orientation: "vertical",
                        })
                    );
                    series.data.setAll(data);
                     series.appear(1000);
                    if(item.ks_show_data_value && item.ks_data_label_type=="value"){
                        series.labels.template.set("text", "{value.formatNumber('0.00')}");
                    }else if(item.ks_show_data_value && item.ks_data_label_type=="percent"){
                        series.labels.template.set("text", "{valuePercentTotal.formatNumber('0.00')}%");
                    }else{
                        series.ticks.template.set("forceHidden", true);
                        series.labels.template.set("forceHidden", true);
                    }
                    var legend = chart.children.push(
                        am5.Legend.new(root, {
                            centerX: am5.p50,
                            x: am5.p50,
                            layout: am5.GridLayout.new(root, {
                                maxColumns: 3,
                                fixedWidthGrid: true
                            }),
                            y: am5.percent(100),
                            centerY: am5.percent(100),
                            reverseChildren: true,
                        })
                    );
                    if(isRtl){
                        legend.labels.template.setAll({
                           textAlign: "right",
                           marginRight: 5
                        });
                        legend.itemContainers.template.setAll({
                            reverseChildren: true,
                            paddingLeft: 20,
                            paddingRight: 20,
                        });
                   }
                    if(item.ks_hide_legend){
                        legend.data.setAll(series.dataItems);
                    }
                    chart.appear(1000, 100);

                    series.slices._values.forEach((rec)=>{
                        rec.events.on("click", (ev) => canvasClickCallback(ev))
                    })
                }else{
                    renderNoDataGraph(root)
                }
            }else{
                    renderNoDataGraph(root)
                }
                return root;
            }
            catch(e){
                console.error(e)
            }
     }

export function renderMapGraph(rootObj, rootEl, chartConfig, itemConfig, canvasClickCallback, chartType=false){
        try{
            rootObj?.dispose?.()
            let item = itemConfig
            const isRtl = localization.direction === "rtl"
            var self = this;
            var map_data = chartConfig;
            var ks_data = [];
            let data = [];
            let label_data = [];
            let query_label_data = [];
            let domain = [];
            let root;
            root = am5.Root.new(rootEl)
            let partner_domain = [];
            var partners = [];
            if (map_data.groupByIds?.length){
                partners = map_data['partner']
            var partners_query = [];
            partners_query = map_data['ks_partners_map']
            var ks_labels = map_data['labels'];
            if (map_data.datasets.length){
                var ks_data = map_data.datasets[0].data;
            }
            if (item.ks_data_calculation_type === 'query'){
                for (let i=0 ; i<ks_labels.length ; i++){
                    if (ks_labels[i] !== false){
                        if (typeof ks_labels[i] == 'string'){
                            if (ks_labels[i].includes(',')){
                                ks_labels[i] = ks_labels[i].split(', ')[1]
                            }
                            query_label_data.push(ks_labels[i])
                        }else{
                            query_label_data.push(ks_labels[i])
                        }
                    }
                }
                for (let i=0 ; i<query_label_data.length ; i++){
                    if (typeof query_label_data[i] == 'string'){
                        for (let j=0 ; j<partners_query.length ; j++){
                            if (query_label_data[i] == partners_query[j].name){
                                data.push({"title":query_label_data[i], "latitude":partners_query[j].partner_latitude, "longitude": partners_query[j].partner_longitude});
                            }
                        }
                    }else{
                          data.push({"title":query_label_data[i], "latitude":partners_query[i].partner_latitude, "longitude": partners_query[i].partner_longitude});
                    }
                }
            }
            if (ks_data.length && ks_labels.length){
                if (item.ks_data_calculation_type !== 'query'){
                    for (let i=0 ; i<ks_labels.length ; i++){
                        if (ks_labels[i] !== false){
                            if (ks_labels[i].includes(',')){
                                ks_labels[i] = ks_labels[i].split(', ')[1]
                            }
                            label_data.push({'title': ks_labels[i], 'value':ks_data[i]})
                        }
                    }
                    for (let i=0 ; i<label_data.length ; i++){
                        for (let j=0 ; j<partners.length ; j++){
                            if (label_data[i].title == partners[j].name){
                                partners[j].name = partners[j].name + ';' + label_data[i].value
                            }
                        }
                    }
                    for (let i=0 ; i<partners.length ; i++){
                        data.push({"title":partners[i].name, "latitude":partners[i].partner_latitude, "longitude": partners[i].partner_longitude});
                    }
                }

//                this.root = root
                root.setThemes([am5themes_Animated.new(root)]);

                // Create the map chart
                var chart = root.container.children.push(
                  am5map.MapChart.new(root, {
                    panX: "rotateX",
                    panY: "translateY",
                    projection: am5map.geoMercator()
                  })
                );

                var cont = chart.children.push(
                  am5.Container.new(root, {
                    layout: root.horizontalLayout,
                    x: 20,
                    y: 40
                  })
                );

                // Add labels and controls
                cont.children.push(
                  am5.Label.new(root, {
                    centerY: am5.p50,
                    text: "Map",
                    ...(isRtl && {direction: "rtl"})
                  })
                );

                var switchButton = cont.children.push(
                  am5.Button.new(root, {
                    themeTags: ["switch"],
                    centerY: am5.p50,
                    icon: am5.Circle.new(root, {
                      themeTags: ["icon"]
                    }),
                    ...(isRtl && {direction: "rtl"})
                  })
                );

                switchButton.on("active", function() {
                  if (!switchButton.get("active")) {
                    chart.set("projection", am5map.geoMercator());
                    chart.set("panY", "translateY");
                    chart.set("rotationY", 0);
                    backgroundSeries.mapPolygons.template.set("fillOpacity", 0);
                  } else {
                    chart.set("projection", am5map.geoOrthographic());
                    chart.set("panY", "rotateY");

                    backgroundSeries.mapPolygons.template.set("fillOpacity", 0.1);
                  }
                });

                cont.children.push(
                  am5.Label.new(root, {
                    centerY: am5.p50,
                    text: "Globe",
                    ...(isRtl && {direction: "rtl"})
                  })
                );

                // Create series for background fill
                var backgroundSeries = chart.series.push(am5map.MapPolygonSeries.new(root, {}));
                backgroundSeries.mapPolygons.template.setAll({
                  fill: root.interfaceColors.get("alternativeBackground"),
                  fillOpacity: 0,
                  strokeOpacity: 0
                });

                    // Add background polygon
                backgroundSeries.data.push({
                  geometry: am5map.getGeoRectangle(90, 180, -90, -180)
                });

                // Create main polygon series for countries
                var polygonSeries = chart.series.push(
                  am5map.MapPolygonSeries.new(root, {
                    geoJSON: am5geodata_worldLow,
                    exclude: ["AQ"]
                  })
                );
                polygonSeries.mapPolygons.template.setAll({
                  tooltipText: "{name}",
                  toggleKey: "active",
                  interactive: true
                });

                polygonSeries.mapPolygons.template.states.create("hover", {
                  fill: root.interfaceColors.get("primaryButtonHover")
                });

                polygonSeries.mapPolygons.template.states.create("active", {
                  fill: root.interfaceColors.get("primaryButtonHover")
                });

                var previousPolygon;

                polygonSeries.mapPolygons.template.on("active", function (active, target) {
                  if (previousPolygon && previousPolygon != target) {
                    previousPolygon.set("active", false);
                  }
                  if (target.get("active")) {
                    polygonSeries.zoomToDataItem(target.dataItem );
                  }
                  else {
                    chart.goHome();
                  }
                  previousPolygon = target;
                });

                // Create line series for trajectory lines
                var lineSeries = chart.series.push(am5map.MapLineSeries.new(root, {}));
                lineSeries.mapLines.template.setAll({
                  stroke: root.interfaceColors.get("alternativeBackground"),
                  strokeOpacity: 0.3
                });

                // Create point series for markers
                var pointSeries = chart.series.push(am5map.MapPointSeries.new(root, {}));
                var colorset = am5.ColorSet.new(root, {});
                const self = root;


                pointSeries.bullets.push(function() {
                  var container = am5.Container.new(self, {
                    tooltipText: "{title}",
                    cursorOverStyle: "pointer"
                  });

                  var circle = container.children.push(
                    am5.Circle.new(self, {
                      radius: 4,
                      tooltipY: 0,
                      fill: colorset.next(),
                      strokeOpacity: 0
                    })
                  );


                  var circle2 = container.children.push(
                    am5.Circle.new(self, {
                      radius: 4,
                      tooltipY: 0,
                      fill: colorset.next(),
                      strokeOpacity: 0,
                      tooltipText: "{title}"
                    })
                  );

                  circle.animate({
                    key: "scale",
                    from: 1,
                    to: 5,
                    duration: 600,
                    easing: am5.ease.out(am5.ease.cubic),
                    loops: Infinity
                  });

                  circle.animate({
                    key: "opacity",
                    from: 1,
                    to: 0.1,
                    duration: 600,
                    easing: am5.ease.out(am5.ease.cubic),
                    loops: Infinity
                  });

                  return am5.Bullet.new(self, {
                    sprite: container
                  });
                });

                for (var i = 0; i < data.length; i++) {
                  var final_data = data[i];
                  addCity(final_data.longitude, final_data.latitude, final_data.title);
                }
                function addCity(longitude, latitude, title) {
                  pointSeries.data.push({
                    geometry: { type: "Point", coordinates: [longitude, latitude] },
                    title: title,
                  });
                }

                // Add zoom control
                chart.set("zoomControl", am5map.ZoomControl.new(root, {}));

                // Set clicking on "water" to zoom out
                chart.chartContainer.get("background").events.on("click", function () {
                  chart.goHome();
                })

                // Make stuff animate on load
                chart.appear(1000, 100);

            }else{
               renderNoDataGraph(root)
            }
            }else{
                renderNoDataGraph(root)
            }
            return root;
        }
        catch(e){
            console.error("Chart doesn't rendered")
        }
    }