

// TUS Client for File upload

var pirusFileUpload = null
var pirusFileInput = document.querySelector("#tusFileInput")
var pirusFileAlertBox = document.querySelector("#support-alert")
var pirusFileChunkInput = document.querySelector("#tusFileChunksize")
var pirusFileEndpointInput = document.querySelector("#tusFileEndpoint")


if (!tus.isSupported) {
    pirusFileAlertBox.className = pirusFileAlertBox.className.replace("hidden", "")
}


pirusFileInput.addEventListener("change", function(e) {
    var file = e.target.files[0]
    console.log("selected file", file)

    var endpoint = pirusFileEndpointInput.value
    var chunkSize = parseInt(pirusFileChunkInput.value, 10)
    if (isNaN(chunkSize)) {
        chunkSize = Infinity
    }
    var options = {
        endpoint: endpoint,
        resume: true,
        chunkSize: chunkSize,
        metadata: {
            filename: file.name
        },
        onError: function(error) {
            pirusFileInput.value = ""
            buildPopup("Failed because: " + error, "alert", "tusFileProgress")
        },
        onProgress: function(bytesUploaded, bytesTotal) {
            var percentage = (bytesUploaded / bytesTotal * 100).toFixed(2)
            console.log(bytesUploaded, bytesTotal, percentage + "%")
            buildProgressBar(percentage, "RUN", "tusFileProgress")
        },
        onSuccess: function() {
            pirusFileInput.value = ""
            buildPopup("Download finish !  " + pirusFileUpload.file.name + " is now available for run.", "success", "tusFileProgress")
            $("#uploadFileForm").addClass("hidden")
        }
    }

    pirusFileUpload = new tus.Upload(file, options)
    pirusFileUpload.start()

    fileId = pirusFileUpload.url.substr(pirusFileUpload.url.lastIndexOf('/') + 1)
    
    // retrieve file information an load/enable second part of the form
    $.ajax({ url: rootURL + "/file/" + fileId, type: "GET", async: false}).done(function(jsonData)
    {
        $("#uploadFileForm").removeClass("hidden")
        $("#uploadFileFormTags").val(jsonData["tags"])
        $("#uploadFileFormComments").val(jsonData["comments"])
        $("#uploadFileForm").attr('action', rootURL + "/file/upload/" + fileId);

    })
})















// TUS Client for Pipeline upload

var pirusPipeUpload = null
var pirusPipeInput = document.querySelector("#tusPipeInput")
var pirusPipeChunkInput = document.querySelector("#tusPipeChunkSize")
var pirusPipeEndpointInput = document.querySelector("#tusPipeEndpoint")


if (!tus.isSupported) {
    pirusPipeAlertBox.className = pirusPipeAlertBox.className.replace("hidden", "")
}


pirusPipeInput.addEventListener("change", function(e) {
    var file = e.target.files[0]
    console.log("selected file", file)

    var endpoint = pirusPipeEndpointInput.value
    var chunkSize = parseInt(pirusPipeChunkInput.value, 10)
    if (isNaN(chunkSize)) {
        chunkSize = Infinity
    }
    var options = {
        endpoint: endpoint,
        resume: true,
        chunkSize: chunkSize,
        metadata: {
            filename: file.name
        },
        onError: function(error) {
            pirusPipeInput.value = ""
            buildPopup("Failed because: " + error, "alert", "tusPipeProgress")
        },
        onProgress: function(bytesUploaded, bytesTotal) {
            var percentage = (bytesUploaded / bytesTotal * 100).toFixed(2)
            console.log(bytesUploaded, bytesTotal, percentage + "%")
            buildProgressBar(percentage, "RUN", "tusPipeProgress")
        },
        onSuccess: function() {
            pirusPipeInput.value = ""
            buildPopup("Download finish !  " + pirusPipeUpload.file.name + " Will be soon installed.", "success", "tusPipeProgress")
        }
    }

    pirusPipeUpload = new tus.Upload(file, options)
    pirusPipeUpload.start()
})
