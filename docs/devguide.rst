Developer Guide
###############



Solution organisation
=====================
 * The core team of Pirus project:
    * As sub project of Revogar, the core team of Pirus, is the same as for Regovar : Ikit, dridk, Oodnadatta and Arkanosis. All of them are both consultant and developer.
 * Coding Rules : 
    * https://www.python.org/dev/peps/pep-0008/
 * Git branching strategy : 
    * Dev on master, 
    * One branch by release; with the version number as name (by example branch "v1.0.0" for the v1.0.0)
 * Discussion : 
    * https://regovar.slack.com/
    * dev@regovar.org
 


Architecture
============

See dedicated page


Model
=====


Pipeline
--------
|   **Static property :**
|      public_fields <str[]> : liste des champs exportable pour le enduser (client pirus)
|      
|   **Public properties :**
|      name <str> : (required) human readable name for the pipeline
|      description <str> : little description about the goal of the pipeline
|      version <str> : 
|      pirus_api <str> : (required)
|      license <str> : 
|      developers <str[]> : 
|      size <int> : (required) total size if the pipeline package (used for the upload progress)
|      upload_offset <int> : (required) current offset position of the upload
|      status <str> : (required) can take following value : UPLOADING, PAUSE, ERROR, INSTALLING, READY
|      
|   **Internal properties :**
|      pipeline_file <str> : (required) the full path the the pipeline package is stored on the server
|      root_path <str> : the full path to the root directory where the pipeline is deployed (and so, ready to be used)
|      lxd_alias <str> : alias of the lxd image that shall be use to create a run with this pipeline
|      lxd_inputs_path <str> : full path in the lxc container where inputs files shall be mount for the run
|      lxd_outputs_path <str> : full path in the lxc container where outputs files will be put by the run
|      lxd_logs_path <str> : full path in the lxc container where logs will be put by the run
|      lxd_db_path <str> : full path in the lxc container where databases files shall be mount for the run
|      lxd_run_cmd <str> : bash command that shall be executed in the lxc container of the run to start it
|      form_file <str> : full path on the server where the json file that describe the form to be used to configure a run is
|      icon_file <str> : full path on the server where the icon file of the pipeline is
|
|   **Static methods :**
|      from_id(pipe_id) : return a Pipeline object from the database
|      remove(pipe_id) : uninstall a pipeline on the server and remove the entry in the database
|      install(pipe_id) : install a pipeline; as the pipeline have been uploaded, the entry in database already exists, that's why we only need the pipe_id to install it
|      
|   **Internal methods :**
|      export_server_data(self)
|      export_client_data(self)
|      import_data(self, data)
|      url(self) : return the url that shall be used to download the pipeline package
|      upload_url(self) : return the url that shall be used to upload the pipeline on the server



Run
---
   **Static property :**
      public_fields <str[]> : liste des champs exportable pour le enduser (client pirus)

   **Public properties :**
      pipe_id <str> : (required) the id of the pipe used for this run
      name <str> : (required) the name set by the user for this run
      config <str> : the json config data (result of the config form send by the user) provided to the run as input
      start <str> : 
      end        = StringField()
      status     = StringField()  # WAITING, PAUSE, INITIALIZING, RUNNING, FINISHING, ERROR, DONE, CANCELED
      inputs     = ListField(StringField())
      outputs    = StringField()
      progress   = DynamicField(required=True)

   **Internal properties :**
      lxc_alias <str> : the alias of the lxc container used for the run
      


API
===

See dedicated page for the current api implemented.

 * How to update current api
 * Implement a new version of the api



TUS.IO protocol
===============


