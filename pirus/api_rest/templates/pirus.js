
var demo_pirus_displayed_run;
var demo_pirus_displayed_file;
var demo_pirus_displayed_pipe;

var demo_pirus_selection = [];





/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* Demo browser methods
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */


function display_status_bar(file_id)
{
    var details =  $('#fileEntry-' + file_id + ' td:nth-child(5)').html();
    $('#demo_footer').html((details == "None") ? "&nbsp;" : details);
}


function show_tab(tab_id, id)
{
    $('#browser_content > div').each( function( index, element )
    {
        $(element).addClass("collapse");
    });
    $('#' + tab_id).removeClass("collapse");
    
    // Manage display of run data
    if (tab_id == 'browser_run')
    {        
        demo_pirus_displayed_run = id;
        $.ajax({ url: rootURL + "/run/" + id + "/monitoring", type: "GET"}).done(function(jsonFile)
        {
            data = jsonFile["data"];
            progress = Math.round(parseInt(data["progress"]["value"]) / Math.max(1, (parseInt(data["progress"]["max"]) - parseInt(data["progress"]["min"]))) * 100);

            // Header style / control according to the status of the run
            if ($.inArray(data["status"],["PAUSE", "WAITING"]) > -1) $('#browser_run_monitoring_header').attr('class', 'orange');
            if ($.inArray(data["status"], ["ERROR", "CANCELED"]) > -1) $('#browser_run_monitoring_header').attr('class', 'red');
            if ($.inArray(data["status"], ["INITIALIZING", "RUNNING", "FINISHING"]) > -1) $('#browser_run_monitoring_header').attr('class', 'blue');
            if ($.inArray(data["status"],["DONE"]) > -1) $('#browser_run_monitoring_header').attr('class', 'green');
            $('#browser_run_monitoring_progress').attr('style', 'right:'+ (100-Math.max(1, progress)) + '%');

            // Logs 
            $("#browser_run_name").html("<img src=\"{0}\" width=\"30px\" style=\"vertical-align:middle\"/> Run : {1}".format(data["pipeline_icon"], data["name"]));
            $("#browser_run_details").html("Pipeline {0} : <b>{1} % </b>".format(data["pipeline_name"], progress));
            $("#browser_run_status").html(data["status"]);
            $("#browser_run_playpause").attr("href", "{0}/run/{1}/{2}".format(rootURL, data["id"], (data["status"] in ["PAUSE"]) ? "play" : "pause"));
            $("#browser_run_playpause").html((data["status"] in ["PAUSE"]) ? "<i class=\"fa fa-play\" aria-hidden=\"true\"></i>" : "<i class=\"fa fa-pause\" aria-hidden=\"true\"></i>");

            $("#browser_run_stop").attr("href", "{0}/run/{1}/stop".format(rootURL, data["id"]));

            if (data["vm_info"])
            {
                var html = "<ul>";
                for (k in data["vm"])
                {
                    html += "<li><b>{0} :</b> {1}</li>".format(k, data["vm"][k]);
                }
                $("#browser_run_monitoring_vm").html(html);
            }
            else
            {
                $("#browser_run_monitoring_vm").html("<i>{0}</i>".format(data["vm"]));
            }


            $("#browser_run_monitoring_stdout").text((data["out_tail"] == "") ? "... No log on stdOut ..." : data["out_tail"]);
            $("#browser_run_monitoring_stdout").animate({scrollTop : $("#browser_run_monitoring_stdout")[0].scrollHeight }, 1000 );

            $("#browser_run_monitoring_stderr").text((data["err_tail"] == "") ? "... No log on stdErr ..." : data["err_tail"]);
            $("#browser_run_monitoring_stderr").animate({scrollTop : $("#browser_run_monitoring_stderr")[0].scrollHeight}, 1000 );

            $("#browser_run_monitoring_refresh").attr("onclick", "javascript:monitor_run('"+id+"')");
        });


        // Inputs / outputs
        $.ajax({ url: rootURL + "/run/" + id + "/io", type: "GET"}).done(function(jsonFile)
        {
            data = jsonFile["data"];
            if (data["inputs"].length > 0)
            {
                html = "<ul>";
                for (var i=0; i<data["inputs"].length; i++)
                {
                    html += "<li><a href=\"" + rootURL + "/dl/f/" + data["inputs"][i]["id"] + "\" title=\"Download\">" + data["inputs"][i]["name"] + "</a> (" + humansize(data["inputs"][i]["size"]) + ")</li>";
                }
                html += "</ul>";
                $("#monitoring_tab_inputs").html(html);
            }
            else
            {
                $("#monitoring_tab_inputs").html("<i>No input file for this run.</i>");
            }

            if (data["outputs"].length > 0)
            {
                html = "<ul>"
                for (var i=0; i<data["outputs"].length; i++)
                {
                    html += "<li><a href=\"" + rootURL + "/dl/f/" + data["outputs"][i]["id"] + "\" title=\"Download\">" + data["outputs"][i]["name"] + "</a> (" + humansize(data["outputs"][i]["size"]) + ")</li>"
                }
                html += "</ul>"
                $("#monitoring_tab_outputs").html(html)
            }
            else
            {
                $("#monitoring_tab_outputs").html("<i>No ouputs file for this run.</i>");
            }
        });
    }


    // Display of a file
    if (tab_id == "browser_file")
    {
        demo_pirus_displayed_file = id;
        $.ajax({ url: rootURL + "/file/" + id, type: "GET"}).done(function(jsonFile)
        {
            data = jsonFile["data"];
            progress = Math.round(data["upload_offset"] / Math.max(1, data["size"]) * 100);

            // Header style / control according to the status of the file
            if ($.inArray(data["status"],["PAUSE"]) > -1) $('#browser_file_header').attr('class', 'orange');
            if ($.inArray(data["status"], ["ERROR"]) > -1) $('#browser_file_header').attr('class', 'red');
            if ($.inArray(data["status"], ["UPLOADING"]) > -1) $('#browser_file_header').attr('class', 'blue');
            if ($.inArray(data["status"],["UPLOADED", "CHECKED"]) > -1) $('#browser_file_header').attr('class', 'green');
            $('#browser_file_progress').attr('style', 'right:'+ (100-Math.max(1, progress)) + '%');

            
            $("#browser_file_icon").html(get_file_icon(data["type"]));
            $("#browser_file_name").html(data["name"]);
            if ($.inArray(data["status"], ["UPLOADING", "PAUSE", "ERROR"]) > -1)
                $("#browser_file_details").html("Size : {0} / <b>{1}</b>".format(humansize(data["upload_offset"]), humansize(data["size"])));
            else
                $("#browser_file_details").html("Size : <b>{0}</b>".format(humansize(data["size"])));
            if ($.inArray(data["status"],["PAUSE"]) > -1)
                $("#browser_file_status").html(data["status"] + "<br/><span style=\"font-size:12px; font-style:italic; font-weight:100;\">since " + data["status"] + "</span>");
            else
                $("#browser_file_status").html(data["status"]);

            // Infos panel
            html = "<ul>";
            for (var k in data)
            {
                if (typeof data[k] !== 'function') 
                {
                    html += "<li><b>{0} : </b>{1}</li>".format(k, data[k]);
                }
            }
            html += "</ul>";
            $("#file_tab_infos").html(html);

            // Edit panel
            $("#file_tab_edit_name").val(data["name"]);
            $("#file_tab_edit_type").val(data["type"]);
            $("#file_tab_edit_comments").val(data["comments"]);
            $("#file_tab_edit_tags").val(data["tags"]);

            // Preview panel
            $("#file_tab_preview").html("<i>No preview available.</i>");
        });
    }
}


function select_file(file_id)
{
    var count = Object.keys(demo_pirus_selection).length;
    var check = !$('#fileEntry-' + file_id + ' input')[0].checked;
    $('#fileEntry-' + file_id + ' input').prop('checked', check);
    var file_name =  $('#fileEntry-' + file_id + ' td:nth-child(2)').html().trim();
    if (check)
    {
        if (count == 0) $('#browserNavSelectionPanel > ul').html('');
        demo_pirus_selection[file_id] = file_name;
        $('#browserNavSelectionPanel ul').append('<li id="browserNavSelectionPanel-' + file_id + '">' + file_name + '</li>');
        count += 1
    }
    else
    {
        delete demo_pirus_selection[file_id];
        $('#browserNavSelectionPanel-' + file_id).remove();
        if (count == 1) $('#browserNavSelectionPanel > ul').html('<li class="detail">No file selected</li>');
        count -= 1
    }
    
    $('#selection_count').html(count == 0 ? 0 : count);
}

var activity_inprogress_count = 0
var demo_browser_file_entry =  "<tr id=\"activity_entry_{0}\" onmouseover=\"javascript:display_status_bar('{0}')\" onclick=\"javascript:select_file('{0}')\" style=\"cursor: pointer;\">";
demo_browser_file_entry +=  "<td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td></tr>";



function add_new_activity_to_demo_browser(type, id)
{
    $('#inprogress_count').html(activity_inprogress_count);
    var name = "name";
    var details = "details";
    var progress = "progress";
    var status = "status";
    // Retrieve data
    activity_inprogress_count += 1;
    if (type == "file")
    {
        // check if entry already exists (resume previous upload)
        elmnt = $('#fileEntry-' + id);
        if (elmnt.length)
        {
            // elmnt exist, so update it
        }
        else
        {
            // add new entry into the table
        }
        $('#browser_inprogress_files_table').append(demo_browser_file_entry.format(id, name, details, progress, status));
    }
    else if (type == "pipeline")
    {
        $('#browser_inprogress_pipes_table').append(demo_browser_file_entry.format(id, name, size, creation, comments));
    }
    else if (type == "run")
    {
        $('#browser_inprogress_runs_table').append(demo_browser_file_entry.format(id, name, size, creation, comments));
    }

    // Update IHM
}





/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* Filter method
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

$("#browser_filter_input").keyup(function () 
{ 
    // Split the current value of searchInput
    var data = this.value.toUpperCase().split(" ");
    // Create a jquery object of the rows
    var jo = $("#browser_files_table > tbody").find("tr");
    if (this.value == "") 
    {
        jo.show();
        return;
    }
    // hide all the rows
    jo.hide();

    //Recusively filter the jquery object to get results.
    jo.filter(function (i, v) 
    {
        var $t = $(this);
        for (var d = 0; d < data.length; ++d) 
        {
            if ($t.text().toUpperCase().indexOf(data[d]) > -1) 
            {
                return true;
            }
        }
        return false;
    })
    //show the rows that match.
    .show();
});


/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* New Run Popup methods
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

var BrutusinForms = brutusin["json-forms"];
var bf, schema;

var runConfigPipeId;
var runConfigPipeName = "{TODO - Pipe Name}";
var runConfigForm;
var runConfigInputs;

function init_run(pipe_id)
{
    // 1- retrieve pipe-config
    $.ajax(
    {
        url: rootURL + "/pipeline/" + pipe_id + "/form.json",
        type: "GET"
    }).fail(function()
    {
        alert( "ERROR" );
    }).done(function(json) 
    {
        var json_db = [];

        if (json.indexOf("__PIRUS_DB_ALL__") != -1)
        {

            // get list of database
            $.ajax({ url: rootURL + "/db", type: "GET", async: false}).done(function(jsonDB)
            {
                json_db = jsonDB["data"];
            })

            json = json.replace(/"__PIRUS_DB_ALL__"/g, JSON.stringify(json_db));
        }
        runConfigForm = json;
        runConfigPipeId = pipe_id;

        $("#inputFilesList tbody").empty();
        for (var key in demo_pirus_selection)
        {
            var size = $('#fileEntry-' + key + " td:nth-child(3)").html();
            var date = $('#fileEntry-' + key + " td:nth-child(4)").html();
            var comments = $('#fileEntry-' + key + " td:nth-child(5)").html();
            $("#inputFilesList > tbody").append("<tr><td>{0}<br/><span class=\"details\">{3}</span></td><td>{1}</td><td>{2}</td></td>".format(demo_pirus_selection[key], size, date, key));
        }


        
        run_config_step_2();
    })
}


function run_config_step_2()
{
    // Retrieve list of selected inputs
    var json_files = []
    var json = runConfigForm
    if (json.indexOf("__PIRUS_INPUT_FILES__") != -1)
    {
        var i = 0;
        for (var key in demo_pirus_selection)
        {
            json_files[i] = demo_pirus_selection[key];
            i++;
        }
        
        json = json.replace(/"__PIRUS_INPUT_FILES__"/g, JSON.stringify(json_files))
    }

    schema = JSON.parse(json);
    schema["properties"]["name"] = {
        "title": "Nom du run",
        "description": "Le nom qui sera affiché pour ce run.",
        "type": "string",
        "required": true
    };
    
    bf = BrutusinForms.create(schema);
    var container = document.getElementById('runConfigContainer');
    container.innerText = ""
    bf.render(container, null);
}

function run_config_step_3()
{
    if (bf.validate())
    {
        config = bf.getData();
        config = JSON.stringify(config, null, 4);


        var html = "<h3>Pipeline : " + runConfigPipeName + "</h3><h4>Inputs</h4>";
        var count = Object.keys(demo_pirus_selection).length;
        if (count > 0)
        {
            html += "<ul>";
            for (var key in demo_pirus_selection)
            {
                html += "<li>{0}</li>".format(demo_pirus_selection[key]);
            }
            html += "</ul>";
        }
        html += "<h4>Config</h4>";
        for (var key in config)
        {
            html += "<li><b>{0}</b> : {1}</li>".format(key, config[key]);
        }
        html += "</ul>";


        $('#runConfirmContainer').html(html);
    }
    else
    {
        // Todo : return on step 2
    }
}
function run_config_step_4()
{
    if (bf.validate())
    {
        config = bf.getData()
        config = JSON.stringify(config, null, 4)
        inputs = []

        debugger;
        var i = 0;
        for (var key in demo_pirus_selection)
        {
            inputs[i] = demo_pirus_selection[key];
            config = config.replace(new RegExp(key, 'g'), demo_pirus_selection[key]);

            i++;
        }

        inputs = JSON.stringify(inputs, null, 4)

        $.ajax(
        {
            url: rootURL + "/run",
            type: "POST",
            data: "{\"pipeline_id\" : \""+ runConfigPipeId +"\", \"config\" : " + config + ", \"inputs\" : " + inputs + "}"
        }).fail(function()
        {
            alert( "ERROR" );
        }).done(function(txt) 
        {
            alert( "SUCCESS\n" + txt);
        })
    }
}














/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */
/* WEBSOCKETS handler
/* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * */

function ws_file_changed(data)
{
    debugger;
    jQuery.each(data, function(index, item) {
        var percentage = (item["upload_offset"] / item["set_notify_all"] * 100).toFixed(2)

        buildProgressBar(percentage, item["status"], "browser_inprogress_pipes_table_td_progress_" + item["id"])
        var tdElement = $("#run-" + item["id"] + "-status")
        tdElement.html(item["status"])
    });
    // Todo : update controls
}



function ws_new_pipeline(msg_data)
{

}

function ws_new_run(msg_data)
{

}

function ws_run_changed(data)
{
    jQuery.each(data, function(index, item) 
    {
        var percentage = (item["progress"]["value"] / item["progress"]["max"] * 100).toFixed(2)
        buildProgressBar(percentage, item["status"], "run-" + item["id"] + "-progress")
        var tdElement = $("#run-" + item["id"] + "-status")
        tdElement.html(item["status"])
    });
    // Todo : update controls
}









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

var demo_pirus_extensions = 
{
    "image" :   ["jpg", "jpeg", "gif", "png", "bmp", "tiff"],
    "archive" : ["zip", "tar.gz", "tar", "tar.xz", "gz", "xz", "rar"],
    "code" :    ["html", "htm", "py"],
    "text" :    ["log", "txt", "vcf", "sam"],
    "pdf" :     ["pdf"],
    "excel" :   ["xls", "xlsx"]
};
function get_file_icon(extension)
{
    for (var k in demo_pirus_extensions)
    {
        if (typeof demo_pirus_extensions[k] !== 'function') 
        {
            if ($.inArray(extension,demo_pirus_extensions[k]) > -1)
                return '<i class="fa fa-file-' + k +'-o" aria-hidden="true"></i>';
        }
    }
    return '<i class="fa fa-file-o" aria-hidden="true"></i>'
}