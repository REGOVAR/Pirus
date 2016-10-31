var upload = null
var input = document.querySelector("#tusFileInput")
var alertBox = document.querySelector("#support-alert")
var chunkInput = document.querySelector("#chunksize")
var endpointInput = document.querySelector("#endpoint")

if (!tus.isSupported) {
    alertBox.className = alertBox.className.replace("hidden", "")
}


input.addEventListener("change", function(e) {
    var file = e.target.files[0]
    console.log("selected file", file)

    var endpoint = endpointInput.value
    var chunkSize = parseInt(chunkInput.value, 10)
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
            input.value = ""
            buildPopup("Failed because: " + error, "alert", "tusFileProgress")
        },
        onProgress: function(bytesUploaded, bytesTotal) {
            var percentage = (bytesUploaded / bytesTotal * 100).toFixed(2)
            console.log(bytesUploaded, bytesTotal, percentage + "%")
            buildProgressBar(percentage, "RUN", "tusFileProgress")
        },
        onSuccess: function() {
            input.value = ""
            buildPopup("Download finish !  " + upload.file.name + " is now available for run.", "success", "tusFileProgress")
            $("#uploadFileForm").addClass("hidden")
        }
    }

    upload = new tus.Upload(file, options)
    upload.start()

    fileId = upload.url.substr(upload.url.lastIndexOf('/') + 1)
    addFileEntry(fileId)

    // retrieve file information an load/enable second part of the form
    $.ajax({ url: rootURL + "/file/" + fileId, type: "GET", async: false}).done(function(jsonData)
    {
        $("#uploadFileForm").removeClass("hidden")
        $("#uploadFileFormTags").val(jsonData["tags"])
        $("#uploadFileFormComments").val(jsonData["comments"])
        $("#uploadFileForm").attr('action', rootURL + "/file/" + fileId);

    })
})
