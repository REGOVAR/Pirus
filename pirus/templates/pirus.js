


function buildProgressBar(percentage, pbTheme, containerId) {
    var style="progress-bar "

    if  (pbTheme == "ERROR" || pbTheme == "CANCELED")
        { style += "progress-bar-danger"}
    else if (pbTheme == "DONE" || pbTheme == "UPLOADED" || pbTheme == "CHECKED" || pbTheme == 'READY')
        { style += "progress-bar-success"}
    else if (pbTheme == "PAUSE")
        { style += "progress-bar-warning"}
    else if (pbTheme == "RUNNING" || pbTheme == "UPLOADING")
        { style += "progress-bar-striped active"}
    else if (pbTheme == "WAITING") { style += "progress-bar-warning progress-bar-striped active"}



    var html = "<div class='progress'>\
                <div class='" + style + "' role='progressbar' aria-valuenow='" + percentage + "' aria-valuemin='0' aria-valuemax='0' \
                    style='min-width: 2em; width: " + percentage + "%;'>\
                    " + percentage + "% \
                </div>\
            </div>"

    if (containerId !== null)
    {
        $("#" + containerId).html(html)
    }

    return html
}


function buildPopup(popupMsg, popupStyle, containerId) {
    var container = $("#" + containerId)
    container.html('<div class="alert alert-' + popupStyle + ' hidden" id="support-alert">' + popupMsg + '</div>')
}

function addFileEntry(fileId) {
    $.ajax({ url: rootURL + "/file/" + fileId, type: "GET"}).done(function(jsonData)
    {

        $("#filesList tr:last").after('<tr id="fileEntry-' + fileId + '"></tr>')
        var percentage = (jsonData["size"] / jsonData["size_total"] * 100).toFixed(2)
        buildProgressBar(percentage, jsonData["status"], "fileEntry-" + fileId)
        $('#filesList').DataTable();
    })
}


function humansize(nbytes)
{
    var suffixes = ['o', 'Ko', 'Mo', 'Go', 'To', 'Po']
    if (nbytes == 0) return '0 o'

    var i = 0
    while (nbytes >= 1024 && i < suffixes.length-1)
    {
        nbytes /= 1024.
        i += 1
    }
    f = Math.round(nbytes * 100) / 100
    return f + " " + suffixes[i]
}


// 0=id, 1=name, 2=desc, 3=status
var browser_pipe_ready_tpl = "<tr class=\"treegrid-{0}\"><td class=\"onHoverBtn\"> <i class=\"fa fa-puzzle-piece\" aria-hidden=\"true\"></i> <a title=\"Run the pipeline\" data-toggle=\"modal\"  href=\"#runConfigModal\" onclick=\"javascript:init_run('{0}')\">{1} <i class=\"fa fa-play\" aria-hidden=\"true\"></i></a></td><td>{2}</td><td>{3}</td></tr>"
var browser_pipe_tpl = "<tr class=\"treegrid-{0}\"><td class=\"onHoverBtn\"> <i class=\"fa fa-puzzle-piece\" aria-hidden=\"true\"></i> {1}</td><td>{2}</td><td>{3}</td></tr>"
var browser_run_tpl  = "<tr class=\"treegrid-{0} treegrid-parent-{1} {5}\"><td> <i class=\"fa fa-tasks\" aria-hidden=\"true\"></i> {2}</td><td>{3}</td><td>{4}</td></tr>"
var browser_folder_tpl = "<tr class=\"treegrid-{0} treegrid-parent-{1}\"><td> <i class=\"fa fa-folder-open-o\" aria-hidden=\"true\"></i> {2}</td><td></td><td></td></tr>"
var browser_file_tpl = "<tr class=\"treegrid-{0} treegrid-parent-{1}\"><td> {2}</td><td>{3}</td><td>{4}</td></tr>"

function init_pirus_browser()
{
    $.ajax({ url: rootURL + "/pipeline?sublvl=1", type: "GET"}).done(function(jsonFile)
    {
        var data = jsonFile["data"];
        var html = ""
        var file_id = 0
        for (var p=0; p<data.length; p++)
        {
            pipe = data[p]
            var p_percentage  = (pipe["upload_offset"] / pipe["size"] * 100).toFixed(0)
            var p_status      = pipe["status"]
            var p_description = pipe["description"]
            var p_name        = pipe["name"]
            if (p_status != 'READY')
            {
                p_status      = buildProgressBar(p_percentage, pipe["status"], null)
                p_description = "Deployment in progress"
                p_name        = p_name + " (" + humansize(pipe["upload_offset"]) + " / " + humansize(pipe["size"]) + ")"
            }
            
            if (p_status == 'READY')
                html += browser_pipe_ready_tpl.format(pipe["id"], p_name, p_description, p_status)
            else
                html += browser_pipe_tpl.format(pipe["id"], p_name, p_description, p_status)

            for (var r=0; r<pipe["runs"].length; r++)
            {
                run = pipe["runs"][r]
                var r_percentage  = (run["progress"]["value"] / run["progress"]["max"] * 100).toFixed(0)
                var r_status      = buildProgressBar(r_percentage, run["status"], null)
                var r_description = run["description"]
                var r_name        = run["name"]
                var r_class       = (run["status"] == "DONE") ? "text-success" : (run["status"] == "ERROR" || run["status"] == "CANCELED" ) ? "text-danger" : ""
                html += browser_run_tpl.format(run["id"], pipe["id"], r_name, r_description, r_status, r_class)

                html += browser_folder_tpl.format(run["id"]+"i", run["id"], "Inputs")
                for (var f=0; f<run["inputs"].length; f++)
                {
                    file = run["inputs"][f]
                    var f_percentage  = (file["upload_offset"] / file["size"] * 100).toFixed(0)
                    var f_status      = buildProgressBar(f_percentage, file["status"], null)
                    var f_comments    = file["comments"]
                    var f_name        = file["name"] + "(" + humansize(file["size"]) + ")"
                    html += browser_file_tpl.format(run["id"]+"i"+file["id"], run["id"]+"i", f_name, f_comments, f_status)
                }

                html += browser_folder_tpl.format(run["id"]+"o", run["id"], "Outputs")
                for (var f=0; f<run["outputs"].length; f++)
                {
                    file = run["outputs"][f]
                    var f_percentage  = (file["upload_offset"] / file["size"] * 100).toFixed(0)
                    var f_status      = buildProgressBar(f_percentage, file["status"], null)
                    var f_comments    = file["comments"]
                    var f_name        = file["name"] + "(" + humansize(file["size"]) + ")"
                    html += browser_file_tpl.format(run["id"]+"o"+file["id"], run["id"]+"o", f_name, f_comments, f_status)
                }

            }


            

        }
        $("#pirusBrowser").html(html)


        $('.tree').treegrid({
            'initialState': 'collapsed'
        });
    })
}

console.debug("{0} is dead, but {1} is alive! {0} {2}".format("ASP", "ASP.NET"))