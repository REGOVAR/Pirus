#!python
# coding: utf-8
import ipdb

import os
import sys
import argparse
import json

from argparse import RawTextHelpFormatter
from config import *
from core.model import *
from core.core import pirus




parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter, description="Available commands:"
    "\n  file\t\t- Manage file"
    "\n  pipeline\t- Manage pipelines"
    "\n  job\t\t- Manage job"
    "\n  config\t- Manage the server configuration", 
    usage="pirus [subcommand] [options]", add_help=False)
parser.add_argument("subcommand",  type=str, nargs='*', default=[], help=argparse.SUPPRESS)
parser.add_argument("-h", "--help", help="show this help message and exit", action="store_true")
parser.add_argument("--version", help="show the client version", action="store_true")
parser.add_argument("-v", "--verbose", help="display all messages available", action="store_true")
parser.add_argument("-a", "--async", help="try to execute the command asynchronously (without blocking the shell)", action="store_true")



parser.add_argument("-f",  type=str, nargs='*', default=[], help=argparse.SUPPRESS)
parser.add_argument("-i",  type=str, nargs='*', default=[], help=argparse.SUPPRESS)
parser.add_argument("-c",  type=str, help=argparse.SUPPRESS)





# ===================================================================================================
# CONFIG Commands
# ===================================================================================================

# ===================================================================================================
# FILE Commands
# ===================================================================================================

# ===================================================================================================
# PIPELINE Commands
# ===================================================================================================


parse_pipeline_help_show = """pirus pipeline  show <pipe_id>
      Display information about the requested pipe."""
parse_pipeline_help_check = """pirus pipeline check <local_image_file>
      Check that the image of the pipeline is supported by pirus, and have all mandatory information for the installation."""
parse_pipeline_help_install = """pirus pipeline  install <local_image_file> [--async] [--verbose]
      Install the pipeline image on Pirus."""
parse_pipeline_help_uninstall = """pirus pipeline uninstall <pipe_id> [--async] [--verbose]
      Uninstall the pipeline. To avoid ambiguity, the id of the pipe must be provided."""
parse_pipeline_help = """Manage pirus pipeline

pirus pipeline list
      Display the list of pipeline installed on the server and their status.

""" + parse_pipeline_help_show + "\n\n" + parse_pipeline_help_check + "\n\n" + parse_pipeline_help_install + "\n\n" + parse_pipeline_help_uninstall






def parse_pipeline(args, help=False, verbose=False, asynch=False):
    print ("manage pipeline command [{}] h:{} v:{} a:{}".format(",".join(args), help, verbose, asynch))
    if len(args) == 0:
        print(parse_pipeline_help)
    elif args[0] == "check":
        print("Not implemented")
    elif args[0] == "install":
        if len(args) > 1:
            p = pirus.pipelines.install_init_image_local(args[1], False, {"type" : "lxd"})
            pirus.pipelines.install(p.id, asynch=asynch)
        else:
            print(parse_pipeline_help_install)
    elif args[0] == "uninstall":
        if len(args) > 1:
            p = Pipeline.from_id(args[1])
            if p:
                p = pirus.pipelines.delete(p.id, asynch=asynch)
                if p:
                    print ("Pipeline {} (id={}) deleted".format(p.name, p.id))
            else:
                print("No pipeline found with the id {}".format(args[1]))
        else:
            print(parse_pipeline_help_uninstall)
    elif args[0] == "list":
        if len(args) > 1 :
            print("Warning : list take only one argument... all other have been ignored.")
        print("\n".join([json.dumps(p.to_json(), sort_keys=True, indent=4) for p in pirus.pipelines.get()]))
    elif args[0] == "show":
        if len(args) > 1 and args[1].isdigit():
            p = Pipeline.from_id(int(args[1]), 1)
            if p:
                print(json.dumps(p.to_json(), sort_keys=True, indent=4))
            else:
                print("No pipeline found with the id {}".format(args[1]))
        else:
            print(parse_pipeline_help_show)
    else:
        print(parse_pipeline_help)





# ===================================================================================================
# JOB Commands
# ===================================================================================================



parse_job_help_show = """pirus job  show <pipe_id>
      Display information about the requested job."""
parse_job_help_new = """pirus job new <job_name> <pipeline_id> [-c|--config <json_config_file>] [-i <inputs_ids> [...]] [-f <local_file> [...]] 
      Start a new job for the corresponding <pipeline_id> with the provided name. Inputs files can be provided with -i and or -f options."""


parse_job_help = """Manage pirus job

pirus job list [filters...] [--help]
      Display the list of job on the server. Some filter options can be provided to filter/sort  the list

pirus job  show <pipe_id>
      Display information about the requested job.

pirus job new <job_name> <pipeline_id> [-c|--config <json_config_file>] [-i <inputs_ids> [...]] [-f <local_file> [...]] 
      Start a new job for the corresponding <pipeline_id> with the provided name. Inputs files can be provided with -i and or -f options.

pirus job pause <job_id>
      Pause the jobn (if supported by the type of pipe's container manager).

pirus job play <job_id>
      Restart a job that have been paused.

pirus job stop <pipe_id>
      Force the job's execution to stop. Job is canceled, its container is deleted.

pirus job terminate <pipe_id>
      Force the finalization of the job. If the job execution is finished, but for some raisons, the container have not been deleted, 
      this action will properly clean the job's container stuff.
      """




def parse_job(args, inputs_ids=[], files=[], form=None, help=False, verbose=False, asynch=False):
    print ("manage job command [{}] h:{} v:{} a:{}".format(",".join(args), help, verbose, asynch))
    if len(args) == 0:
        print(parse_pipeline_help)
    elif args[0] == "list":
        if len(args) > 1 :
            print("Warning : list take only one argument... all other have been ignored.")
        print("\n".join([json.dumps(j.to_json(), sort_keys=True, indent=4) for j in pirus.jobs.get()]))
    elif args[0] == "show":
        if len(args) > 1 and args[1].isdigit():
            j = pirus.jobs.monitoring(int(args[1]))
            if j:
                print(json.dumps(j.to_json(), sort_keys=True, indent=4))
            else:
                print("No job found with the id {}".format(args[1]))
        else:
            print(parse_job_help_show)
    elif args[0] == "new":
        if len(args) > 3:
            print("Warning : list take only one argument... all other have been ignored.")
        if len(args) < 3:
            print(parse_pipeline_help_new)

        j = pirus.jobs.new(int(args[2]), {"name" : args[1]}, inputs_ids, asynch)
        print(json.dumps(j.to_json(), sort_keys=True, indent=4))
    elif args[0] == "uninstall":
        print("Not implemented")
    elif args[0] == "list":
        if len(args) > 1 :
            print("Warning : list take only one argument... all other have been ignored.")
        print("\n".join([json.dumps(p.to_json(), sort_keys=True, indent=4) for p in pirus.pipelines.get()]))
    else:
        print(parse_pipeline_help)

















args = parser.parse_args()

if len(args.subcommand) > 0:
    if args.subcommand[0] == "pipeline":
        parse_pipeline(args.subcommand[1:], args.help, args.verbose, args.async)
    elif args.subcommand[0] == "job":
        parse_job(args.subcommand[1:], args.i, args.f, args.c, args.help, args.verbose, args.async)
    elif args.subcommand[0] == "file":
        print ("manage pipeline command")
    elif args.subcommand[0] == "config":
        print ("Server :\n  Version \t{}\n  Hostname \t{}\n  Hostname pub \t{}\n".format(VERSION, HOSTNAME, HOST_P))
        print ("Database :\n  Host \t\t{}\n  Port \t\t{}\n  User \t\t{} (pwd: \"{}\")\n  Name \t\t{}\n  Pool \t\t{}\n".format(DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PWD, DATABASE_NAME, DATABASE_POOL_SIZE))
        print ("File system :\n  Files \t{}\n  Temp \t\t{}\n  Databases \t{}\n  Pipelines \t{}\n  Jobs \t\t{}\n  Logs \t\t{}".format(FILES_DIR, TEMP_DIR, DATABASES_DIR ,PIPELINES_DIR, JOBS_DIR, LOG_DIR))




if args.version:
    print ("Pirus server : {}".format(VERSION))





