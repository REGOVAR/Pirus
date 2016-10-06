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
    mkdir /pipeline/run
    mkdir /pipeline/inputs
    mkdir /pipeline/outputs
    mkdir /pipeline/logs
    mkdir /pipeline/db
    
    # need curl if you want to notify server with the progress of your run
    apt install curl
    
    # the script run.sh is the "entry point" of your run
    echo "curl ${NOTIFY}50" > /pipeline/run/run.sh
    echo "ls -l /pipeline/database/db > /pipeline/outputs/result.txt" >> /pipeline/run/run.sh
    chmod +x /pipeline/run/run.sh
    
    # exit the container
    exit
    
    # stop it and create an image
    lxc stop pirus
    lxc publish pirus --alias=PirusSimple

    # Your Pipeline is ready to use on your server


## TODO : export image as file and edit image conf to create a piruse package installable on any pirus server