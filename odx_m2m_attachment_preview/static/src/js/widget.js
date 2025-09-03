/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { FileInput } from "@web/core/file_input/file_input";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { Component } from "@odoo/owl";

export class Many2ManyBinaryField2 extends Component {
    static template = "odx_m2m_attachment_preview.Many2ManyBinaryField";
    static components = {
        FileInput,
    };
    static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        className: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.operations = useX2ManyCrud(() => this.props.record.data[this.props.name], true);
    }
    onFilePreview (fileID) {
        var fileClass = '.attachment-preview-'+ fileID;
        var clickedElement = document.querySelector(''+fileClass+'');
        var mimetype = clickedElement.getAttribute('data-mimetype');
        var fileURL = clickedElement.getAttribute('data-url');
        if (mimetype == 'image/jpeg') { this._previewImage(fileID) }
        else if (mimetype == 'image/jpg') { this._previewImage(fileID)}
        else if (mimetype == 'video/mp4') { this._previewVideo(fileID) }
        else if (mimetype == 'image/png') { this._previewImage(fileID) }
        else if (mimetype == 'application/pdf') { this._previewPDF(fileID) }
        else {

        this._downloadFile(fileURL,fileID) }

    }

    _downloadFile (fileURL,fileID) {

        var url = window.location.origin + '/web/content/' + fileID + '?download=true';
        var a = document.createElement('a');
         a.href = url;
         a.download = url;
         a.style.display = 'none';
         document.body.appendChild(a);
         a.click();
    }

    _previewImage (fileID){
        var imgName = '';
        var modalHtml = '<div class="modal-img"><div class="row"><div class="col"></div><div style="text-align:right;" class="col"><span style="margin-left:auto;"><a id="OrderImgDownloadLink" href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><i class="fa fa-fw fa-download" style="color:#ffffffdb !important;" role="img" aria-label="Download"></i><span style="color:#ffffffdb !important;">Download</span></a><a style="color:#ffffffdb !important;margin-left:15px;" class="close-img">&times;</a></span></div></div><div class="row modal-img-m2m" style="height:90%;"><img class="preview-img-order" id="m2m-zoom-image" src="/web/content/' + fileID + '"/></div><div class="row m2m-zoom-buttons"><div class="col-12" style="text-align:center;"><button id="m2m-prev-btn" title="Previous" ><span class="fa fa-arrow-left"/></button> <button title="Zoom In" id="m2m-zoom-in"><i class="fa fa-fw fa-plus" role="img" aria-label="Zoom In"></i></button><button title="Zoom Out" id="m2m-zoom-out"><i class="fa fa-fw fa-minus" role="img" aria-label="Zoom Out"></i></button><a href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><button title="Download" id="m2m-download-btn"><i class="fa fa-fw fa-download" role="img" aria-label="Download"></i></button></a><a target="_blank" href="/web/content/' + fileID + '"><button title="Open in New Tab" id="m2m-download-btn"><i class="fa fa-fw fa-external-link" role="img" aria-label="Open in New Tab"></i></button></a><button id="m2m-next-btn" title="Next"><i class="fa fa-arrow-right"/></button></div></div></div>';
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        var modalElement = document.querySelector('.modal-img');
        modalElement.style.display = 'block';
        document.querySelector('.close-img').addEventListener('click', function() {
            modalElement.remove();
        });
        modalElement.addEventListener('click', function(event) {
            if (event.target.classList.contains('modal-img-m2m')) {
                modalElement.remove();
            }
        });
        var zoomValue = 100;
        var zoomIncrement = 10;
        var minZoom = 50;
        var maxZoom = 200;
        var self = this;
        var zoomImage = document.getElementById('m2m-zoom-image');
        var zoomInButton = document.getElementById('m2m-zoom-in');
        var zoomOutButton = document.getElementById('m2m-zoom-out');

        function updateZoomLevel() {
            zoomImage.style.transform = 'scale(' + (zoomValue / 100) + ')';
        }

        function handleZoomIn() {
            if (zoomValue < maxZoom) {
                zoomValue += zoomIncrement;
                updateZoomLevel();
            }
        }

        function handleZoomOut() {
            if (zoomValue > minZoom) {
                zoomValue -= zoomIncrement;
                updateZoomLevel();
            }
        }

        zoomInButton.addEventListener('click', handleZoomIn);
        zoomOutButton.addEventListener('click', handleZoomOut);
        var nextButton = document.getElementById('m2m-next-btn');
        var prevButton = document.getElementById('m2m-prev-btn');

        nextButton.addEventListener('click', handleNextButton);
        prevButton.addEventListener('click', handlePrevButton);

        function handleNextButton() {
            var f_name = self.props.name;
            var records = self.props.record.evalContextWithVirtualIds[f_name];
            var recordIds = records.map(record => record);
            var index = recordIds.indexOf(fileID);
            var nextID = recordIds[index + 1];
            modalElement.remove();
            if (nextID) {
                self.onFilePreview(nextID);
            }
        }

        function handlePrevButton() {
            var f_name = self.props.name;
            var records = self.props.record.evalContextWithVirtualIds[f_name];
            var recordIds = records.map(record => record);
            var index = recordIds.indexOf(fileID);
            var prevID = recordIds[index - 1];
            modalElement.remove();
            if (prevID) {
                self.onFilePreview(prevID);
            }
        }
        document.addEventListener('keydown', function(event) {
            if (event.key === "Escape") {
                modalElement.remove();
            }
        });
    }
     _previewVideo (fileID){
        var self = this;
        var imgName = '';
        var modalHtml = '<div class="modal-img"><div class="row"><div class="col"></div><div style="text-align:right;" class="col"><span style="margin-left:auto;"><a id="OrderImgDownloadLink" href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><i class="fa fa-fw fa-download" style="color:#ffffffdb !important;" role="img" aria-label="Download"></i><span style="color:#ffffffdb !important;">Download</span></a><a style="color:#ffffffdb !important;margin-left:15px;" class="close-img">&times;</a></span></div></div><div class="row modal-img-m2m" style="height:90%;"><video class="odx_video"><source src="/web/content/' + fileID + '" /></video></div><div class="row m2m-zoom-buttons"><div class="col-12" style="text-align:center;"><button id="m2m-prev-btn" title="Previous" ><span class="fa fa-arrow-left"/></button><button title="Play/Pause" id="m2m-play-pause"><i class="fa fa-fw fa-pause"  id="icon_ply_pause" role="img" aria-label="Play/Pause"></i></button><button title="Backward 5 seconds" id="m2m-backward"><i class="fa fa-fw fa-backward" role="img" aria-label="Backward 5 seconds"></i></button><button title="Forward 5 seconds" id="m2m-forward"><i class="fa fa-fw fa-fast-forward" role="img" aria-label="Forward 5 seconds"></i></button><a href="/web/content/' + fileID + '" download="/web/content/'+imgName+'"><button title="Download" id="m2m-download-btn"><i class="fa fa-fw fa-download" role="img" aria-label="Download"></i></button></a><a target="_blank" href="/web/content/' + fileID + '"><button title="Open in New Tab" id="m2m-download-btn"><i class="fa fa-fw fa-external-link" role="img" aria-label="Open in New Tab"></i></button></a><button id="m2m-next-btn" title="Next"><i class="fa fa-arrow-right"/></button></div></div></div>';
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        var modalElement = document.querySelector('.modal-img');
        modalElement.style.display = 'block';

        document.querySelector('.close-img').addEventListener('click', function() {
            modalElement.remove();
        });

        modalElement.addEventListener('click', function(event) {
            if (event.target.classList.contains('modal-img-m2m')) {
                modalElement.remove();
            }
        });

        var video = document.querySelector('video');
        video.play();
        var playPauseButton = document.getElementById('m2m-play-pause');
        var forwardButton = document.getElementById('m2m-forward');
        var backwardButton = document.getElementById('m2m-backward');
        var nextButton = document.getElementById('m2m-next-btn');
        var prevButton = document.getElementById('m2m-prev-btn');

        playPauseButton.addEventListener('click', function() {
            var playPauseIcon = document.getElementById('icon_ply_pause');
            if (video.paused) {
                video.play();
                playPauseIcon.classList.remove('fa-play');
                playPauseIcon.classList.add('fa-pause');
            } else {
                video.pause();
                playPauseIcon.classList.remove('fa-pause');
                playPauseIcon.classList.add('fa-play');
            }
        });

        forwardButton.addEventListener('click', function() {
            video.currentTime += 5;
        });

        backwardButton.addEventListener('click', function() {
            video.currentTime -= 5;
        });

        nextButton.addEventListener('click', function() {
            var f_name = self.props.name;
            var records = self.props.record.evalContextWithVirtualIds[f_name];
            var recordIds = records.map(record => record);
            var index = recordIds.indexOf(fileID);
            var nextID = recordIds[index + 1];
            modalElement.remove();
            if (nextID) {
                self.onFilePreview(nextID);
            }
        });

        prevButton.addEventListener('click', function() {
            var f_name = self.props.name;
            var records = self.props.record.evalContextWithVirtualIds[f_name];
            var recordIds = records.map(record => record);
            var index = recordIds.indexOf(fileID);
            var prevID = recordIds[index - 1];
            modalElement.remove();
            if (prevID) {
                self.onFilePreview(prevID);
            }
        });
        document.addEventListener('keydown', function(event) {
            if (event.key === "Escape") {
                modalElement.remove();
            }
        });

    }
    _previewPDF (fileSrc) {
      var self = this;
      var fileName = '';
      var currentPage = 1;
      var totalPageCount = 0;
      var modalHtml = '<div class="modal-pdf modal-img">' +
        '<div class="row">' +
        '<div style="text-align:center;" class="col-12">' +
        '<span id="pageCount" style="line-height:40px;color:#ffffffdb !important;">'+totalPageCount+' Page</span>' +
        '<span style="float:right;">' +
        '<a id="OrderPdfDownloadLink" href="/web/content/' + fileSrc + '" download="/web/content/' + fileName + '">' +
        '<i class="fa fa-fw fa-download" style="color:#ffffffdb !important;" role="img" aria-label="Download"></i>' +
        '<span style="color:#ffffffdb !important;">Download</span></a>' +
        '<a style="color:#ffffffdb !important;margin-left:15px;" class="close-pdf">&times;</a></span></div></div>' +
        '<div class="pdf-container">' +
        '<div id="pdfCanvasContainer"></div>' +
        '</div>' +
        '<div style="position:fixed;bottom:30px;" class="row m2m-zoom-buttons"><div class="col-12" style="text-align:center;"> <button id="m2m-prev-btn" title="Previous" ><span class="fa fa-arrow-left"/> </button><button title="Zoom In" id="m2m-zoom-in"><i class="fa fa-fw fa-plus" role="img" aria-label="Zoom In"></i></button><button title="Zoom Out" id="m2m-zoom-out"><i class="fa fa-fw fa-minus" role="img" aria-label="Zoom Out"></i></button><a href="/web/content/' + fileSrc + '" download="/web/content/'+fileSrc+'"><button title="Download" id="m2m-download-btn"><i class="fa fa-fw fa-download" role="img" aria-label="Download"></i></button></a><button title="Print" id="m2m-print-pdf"><i class="fa fa-fw fa-print" role="img" aria-label="Print"></i></button><a href="/web/content/' + fileSrc + '" target="_blank"><button title="Open in New Tab" id="m2m-download-btn"><i class="fa fa-fw fa-external-link" role="img" aria-label="Open in New Tab"></i></button></a><button id="m2m-next-btn" title="Next"><i class="fa fa-arrow-right"/></button></div></div></div>';
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    var modalElement = document.querySelector('.modal-pdf');
    modalElement.style.display = 'block';

    var pdfjsLib = window['pdfjs-dist/build/pdf'];
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.10.377/pdf.worker.min.js';

    var pdfCanvasContainer = document.getElementById('pdfCanvasContainer');

    pdfjsLib.getDocument('/web/content/' + fileSrc).promise
        .then(pdf => {
            totalPageCount = pdf.numPages;
            var renderPage = function(pageNum) {
                pdf.getPage(pageNum).then(page => {
                    var viewport = page.getViewport({ scale: 1 });
                    var canvas = document.createElement('canvas');
                    canvas.className = 'pdf-page-canvas';
                    pdfCanvasContainer.appendChild(canvas);
                    var context = canvas.getContext('2d');
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    page.render({ canvasContext: context, viewport: viewport }).promise
                        .then(() => {
                            currentPage = pageNum;
                            document.getElementById('pageCount').textContent = totalPageCount + ' Page';
                            pdfCanvasContainer.appendChild(document.createElement('br'));
                            if (pageNum < totalPageCount) { renderPage(pageNum + 1); }
                        })
                        .catch(error => {
                            console.error('Error rendering page:', error);
                        });
                })
                .catch(error => {
                    console.error('Error getting page:', error);
                });
            };
            renderPage(1);
        })
        .catch(error => {
            console.error('Error:', error);
        });

    document.querySelector('.close-pdf').addEventListener('click', function() {
        modalElement.remove();
    });

    modalElement.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal-pdf')) {
            modalElement.remove();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === "Escape") {
            modalElement.remove();
        }
    });

    var zoomValue = 100;
    var zoomIncrement = 10;
    var minZoom = 50;
    var marTop = 10;
    var maxZoom = 200;
    var zoomImage = document.getElementById('pdfCanvasContainer');
    var zoomInButton = document.getElementById('m2m-zoom-in');
    var zoomOutButton = document.getElementById('m2m-zoom-out');
    var printButton = document.getElementById('m2m-print-pdf');
    var nextButton = document.getElementById('m2m-next-btn');
    var prevButton = document.getElementById('m2m-prev-btn');

    function updateZoomLevel() { zoomImage.style.transform = 'scale(' + (zoomValue / 100) + ')'; }
    function handleZoomIn() {
        if (zoomValue < maxZoom) {
            marTop = marTop + 10;
            zoomValue += zoomIncrement;
            updateZoomLevel();
            zoomImage.style.marginTop = marTop.toString() + '%';
        }
    }
    function handleZoomOut() {
        if (zoomValue > minZoom) {
            marTop = marTop - 10;
            zoomValue -= zoomIncrement;
            updateZoomLevel();
            zoomImage.style.marginTop = marTop.toString() + '%';
        }
    }
        function printPDF() {
            var url = '/web/content/' + fileSrc;
            var iframe = document.createElement('iframe');
            iframe.src = url;
            iframe.style.display = 'none';
            document.body.appendChild(iframe);
            iframe.onload = () => {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            };
        }

        function handleNextButton() {
            var f_name = self.props.name;
            var records = self.props.record.evalContextWithVirtualIds[f_name];
            var recordIds = records.map(record => record);
            var index = recordIds.indexOf(fileSrc);
            var nextID = recordIds[index + 1];
            modalElement.remove();
            if (nextID) {
                self.onFilePreview(nextID);
            }
        }

    function handlePrevButton() {
        var f_name = self.props.name;
        var records = self.props.record.evalContextWithVirtualIds[f_name];
        var recordIds = records.map(record => record);
        var index = recordIds.indexOf(fileSrc);
        var prevID = recordIds[index - 1];
        modalElement.remove();
        if (prevID) {
            self.onFilePreview(prevID);
        }
   }

    zoomInButton.addEventListener('click', handleZoomIn);
    zoomOutButton.addEventListener('click', handleZoomOut);
    nextButton.addEventListener('click', handleNextButton);
    prevButton.addEventListener('click', handlePrevButton);
    printButton.addEventListener('click', printPDF);
        }

    get uploadText() {
        return this.props.record.fields[this.props.name].string;
    }
    get files() {
        return this.props.record.data[this.props.name].records.map((record) => {
            return {
                ...record.data,
                id: record.resId,
            };
        });
    }

    getUrl(id) {
        return "/web/content/" + id + "?download=true";
    }

    getExtension(file) {
        return file.name.replace(/^.*\./, "");
    }

     async onFileUploaded(files) {
        for (const file of files) {
            if (file.error) {
                return this.notification.add(file.error, {
                    title: _t("Uploading error"),
                    type: "danger",
                });
            }
            await this.operations.saveRecord([file.id]);
        }
    }

    async onFileRemove(deleteId) {
        const record = this.props.record.data[this.props.name].records.find(
            (record) => record.resId === deleteId
        );
        this.operations.removeRecord(record);
    }
}

export const many2ManyBinaryField2 = {
    component: Many2ManyBinaryField2,
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["many2many"],
    isEmpty: () => false,
    relatedFields: [
        { name: "name", type: "char" },
        { name: "mimetype", type: "char" },
    ],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        className: attrs.class,
    }),
};

registry.category("fields").add("many2many_attachment_preview", many2ManyBinaryField2);
