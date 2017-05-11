# PirusBasic Pipeline

This document explain you how to build a simple pipeline image for Pirus.

## Requirement
 * You need LXD on your computer to create it
 * You should read the official doc of Pirus

## Instructions

    # create a container
    lxc launch images:ubuntu/xenial pirus
    # configure it
    lxc exec pirus -- /bin/bash

    # following directories are mandatory
    mkdir -p /pipeline/{job,inputs,outputs,logs,db}

    # need curl if you want to notify server with the progress of your run
    apt install curl jq nano --fix-missing

    # Create the script run.sh. this will be the "entry point" of your run
    # An example can be found on github (https://github.com/REGOVAR/Pirus/blob/master/examples/pipelines/PirusBasic/run.sh)
    nano /pipeline/job/run.sh
    chmod +x /pipeline/job/run.sh

    # To allow users to configure your pipeline, you shall put in your container a form.json file
    # that will describe a form to set parameter for your pipe.
    # An example can be found on github (https://github.com/REGOVAR/Pirus/blob/master/examples/pipelines/PirusBasic/form.json)
    nano /pipeline/form.json

    # You can also put a a custom logo (png or jpeg file) in your pipeline.

    # exit the container
    exit

    # stop it and create an image
    lxc stop pirus
    lxc publish pirus --alias=PirusSimple

    # Your Pipeline is ready to use on your server


## Export image as file and edit image conf to create a piruse package installable on any pirus server

    lxc image export PirusSimple
    # following command shall be done as root to avoid image corruption
    # (as it will try to create symlink to computer resource in /dev folder by example)
    sudo tar xf <the_name_of_lxc_export_something_like_a8d44d24fcs...8fzef54e5>.tar.gz

    # add folowing informations into the metadata.yaml file
    sudo nano metadata.yaml

    # if json
    "pirus":
    {
        "name" : "Pirus Simple",               # required : the name of your pipe
        "description" : "Test pipeline",       # optional : the purpose of your pipe
        "version": "1.0.0",                    # optional : the version of your pipe
        "pirus_api": "1.0.0",                  # optional : the pirus api version
        "license" : "AGPLv3",                  # optional : the license of your pipe
        "developers" : ["Olivier GUEUDELOT"],  # optional : a list of name
        "run" : "/pipeline/job/run.sh",        # required : the command command that shall be execute to run your pipe (use absolute path)
        "inputs" : "/pipeline/inputs",         # optional : absolute path to the folder (in the container) where inputs files for the pipe shall be put
        "outputs" : "/pipeline/outputs",       # optional : absolute path to the folder (in the container) where ouputs files of the pipe will be put
        "databases" : "/pipeline/db",          # optional : absolute path to the folder (in the container) where tierce databases (hg19 by example) shall be put
        "logs" : "/pipeline/logs",             # optional : absolute path to the folder (in the container) where log of the run will be put
        "form" : "/pipeline/form.json",        # optional : absolute path to the json file that describe the form for the user to configure the run of the pipe
        "icon" : "/pipeline/logo.png"          # optional : absolute path to the image that shall be used as logo for the pipe
    }
    # if yaml
    pirus:
        name: "Pirus Simple"  # required
        description: "Test pipeline for pirus"
        version : "1.0.0"
        pirus_api: "1.0.0"
        license: "AGPLv3"
        developers: ["Olivier GUEUDELOT"]
        run: "/pipeline/job/run.sh"  # required
        logs: "/pipeline/logs"
        inputs: "/pipeline/inputs"
        outputs: "/pipeline/outputs"
        databases: "/pipeline/db"
        form: "/pipeline/form.json"
        icon: "/pipeline/logo.png"


    # You can repackage the image in tar.xz, to save space
    sudo tar cfJ PirusSimple.tar.xz metadata.yaml rootfs templates
    sudo rm -fr metadata.yaml rootfs templates
    sudo chown olivier:olivier PirusSimple.tar.xz
