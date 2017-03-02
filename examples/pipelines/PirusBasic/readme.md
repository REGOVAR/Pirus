# PirusBasic Pipeline

This document explain you how to build a simple pipeline image for Pirus. 

## Requirement
 * You need LXD on your computer to create it
 * You should read the official doc of Pirus

##Instructions

    # create a container
    lxc launch images:ubuntu/xenial pirus
    # configure it
    lxc exec pirus -- /bin/bash
    
    # following directories are mandatory
    mkdir /pipeline/
    mkdir /pipeline/run
    mkdir /pipeline/inputs
    mkdir /pipeline/outputs
    mkdir /pipeline/logs
    mkdir /pipeline/db
    
    # need curl if you want to notify server with the progress of your run
    apt install curl jq nano
    
    # Create the script run.sh. this will be the "entry point" of your run
    # An example can be found on github (https://github.com/REGOVAR/Pirus/blob/master/examples/pipelines/PirusBasic/run.sh)
    nano /pipeline/run/run.sh
    chmod +x /pipeline/run/run.sh
    
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


## TODO : export image as file and edit image conf to create a piruse package installable on any pirus server

    lxc image export PirusSimple
    # following command shall be done as root to avoid image corruption 
    # (as it will try to create symlink to computer resource in /dev folder by example)
    sudo tar xf a847ed7......3c4e2987e75.tar.gz

    # add folowing informations into the metadata.yaml file
    sudo nano metadata.yaml
    
    # if json
    "pirus":
    {
        "name" : "Pirus Simple",
        "description" : "Test pipeline for pirus",
        "version": "1.0.0",
        "pirus_api": "1.0.0",
        "license" : "AGPLv3",
        "developers" : ["Olivier GUEUDELOT"],
        "run" : "/pipeline/run/run.sh",
        "inputs" : "/pipeline/inputs",
        "outputs" : "/pipeline/outputs",
        "databases" : "/pipeline/db",
        "logs" : "/pipeline/logs",
        "form" : "/pipeline/form.json",
        "icon" : "/pipeline/logo.png"
    }
    # if yaml
    pirus:
        name: "Pirus Simple"
        description: "Test pipeline for pirus"
        version : "1.0.0"
        pirus_api: "1.0.0"
        license: "AGPLv3"
        developers: ["Olivier GUEUDELOT"]
        run: "/pipeline/run/run.sh"
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
