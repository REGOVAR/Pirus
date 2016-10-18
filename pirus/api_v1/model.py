#!env/python3
# coding: utf-8
import ipdb; 


import os
import sys
import time
import logging
import json
import subprocess
import tarfile
import shutil

from mongoengine import *
from bson.objectid import ObjectId


from config import *
from framework import *


class PirusFile(Document):
    file_name    = StringField(required=True)
    file_type    = StringField()
    file_path    = StringField()
    file_size    = StringField() 
    status       = StringField() # DL, TMP, OK
    comments     = StringField()    
    runs         = DynamicField() # dic {key=Run_ID : val="in"|"out"} #empty mean not used
    create_date  = StringField()
    tags         = ListField(StringField())
    md5sum       = StringField()

    def __str__(self):
        return "<InputFile " + self.file_name + " (" + self.file_size + ") : " + self.file_path + ">"

    def export_server_data(self):
        return {
            "file_name"    : self.file_name,
            "file_type"    : self.file_type,
            "file_path"    : self.file_path,
            "file_size"    : self.file_size,
            "status"       : self.status,
            "comments"     : self.comments,
            "runs"         : self.runs,
            "create_date"  : self.create_date,
            "tags"         : self.tags,
            "md5sum"       : self.md5sum,
            "id": str(self.id)
        }

    def export_client_data(self):
        return {
            "file_name"    : self.file_name,
            "file_type"    : self.file_type,
            "file_size"    : self.file_size,
            "status"       : self.status,
            "comments"     : self.comments,
            "runs"         : self.runs,
            "create_date"  : self.create_date,
            "tags"         : self.tags,
            "md5sum"       : self.md5sum,
            "url"          : "http://" + HOSTNAME + "/dl/f/" + str(self.id),
            "id": str(self.id)
        }

    def import_data(self, data):
        try:
            self.file_name     = data['file_name']
            self.file_type     = data["file_type"]
            self.file_path     = data['file_path']
            self.file_size     = data["file_size"]
            self.status        = data["status"]
            self.create_date   = data["create_date"]
            self.md5sum        = data['md5sum']
            if "runs" in data.keys():
                self.runs      = data["runs"]
            if "tags" in data.keys():
                self.tags      = data['tags']
            if "comments" in data.keys():
                self.comments  = data["comments"]
        except KeyError as e:
            raise ValidationError('Invalid input file: missing ' + e.args[0])
        return self

    @staticmethod
    def from_id(ifile_id):
        if not ObjectId.is_valid(ifile_id):
            return None;
        file = PirusFile.objects.get(pk=ifile_id)
        return file





class Pipeline(Document):
    name           = StringField(required=True)
    lxd_alias      = StringField()
    description    = StringField()
    version        = StringField(required=True)
    pirus_api      = StringField(required=True)
    license        = StringField()
    developers     = ListField(StringField())

    path           = StringField(required=True)
    ipath          = StringField(required=True)
    opath          = StringField(required=True)
    lpath          = StringField(required=True)
    run            = StringField(required=True)
    dpath          = StringField(required=True)
    ffile          = StringField(required=True)
    lfile          = StringField()

    def __str__(self):
        return "<Pipeline " + self.path + ">"

    def export_server_data(self):
        return {
            "id"             : str(self.id),
            "name"           : self.name,
            "lxd_alias"      : self.lxd_alias,
            "description"    : self.description,
            "version"        : self.version,
            "pirus_api"      : self.pirus_api,
            "license"        : self.license,
            "developers"     : self.developers,
            "path"           : self.path,
            "ipath"          : self.ipath,
            "opath"          : self.opath,
            "lpath"          : self.lpath,
            "run"            : self.run,
            "dpath"          : self.dpath,
            "ffile"          : self.ffile,
            "lfile"          : self.lfile
        }

    def export_client_data(self):
        return {
            "id"             : str(self.id),
            "name"           : self.name,
            "description"    : self.description,
            "version"        : self.version,
            "pirus_api"      : self.pirus_api,
            "license"        : self.license,
            "developers"     : self.developers,
            "form_url"       : "http://" + HOSTNAME + "/pipeline/" + str(self.id) + "/form.json",
            "icon"           : "http://" + HOSTNAME + "/pipeline/" + str(self.id) + "/" + os.path.basename(self.lfile)
        }

    def import_data(self, data):
        try:
            self.name           = data['name']
            self.pirus_api      = data["pirus_api"]
            self.path           = data['path']
            self.ipath          = data['ipath']
            self.opath          = data['opath']
            self.lpath          = data['lpath']
            self.dpath          = data['dpath']
            self.run            = data['run']
            self.ffile          = data['ffile']
            if "lxd_alias" in data.keys():
                self.lxd_alias = data["lxd_alias"]
            if "description" in data.keys():
                self.description = data["description"]
            if "version" in data.keys():
                self.version     = data['version']
            if "license" in data.keys():
                self.license     = data["license"]
            if "developers" in data.keys():
                self.developers  = data["developers"]
            if "lfile" in data.keys():
                self.lfile       = data['lfile']
        except KeyError as e:
            raise ValidationError('Invalid pipeline: missing ' + e.args[0])
        return self




    @staticmethod
    def from_id(pipe_id):
        if not ObjectId.is_valid(pipe_id):
            return None;
        pipe = Pipeline.objects.get(pk=pipe_id)
        return pipe

    @staticmethod
    def install(ppackage_name, ppackage_path, ppackage_file):
        plog.info('I: Installation of the pipeline package : ' + ppackage_path)
        # 1- Extract pipeline package
        try:
            tar = tarfile.open(ppackage_file)
            tar.extractall(path=ppackage_path)
            tar.close()
        except:
            # TODO : manage error + remove package file
            plog.info('E:    [FAILLED] Extraction of PirusPipeline.tar.gz.')
            raise PirusException("XXXX", "Unable to extract package. Corrupted file or wrong format.")
        plog.info('I:    [OK     ] Extraction of PirusPipeline.tar.gz.')

        # 2- Check module
        metadata_file = os.path.join(ppackage_path, "metadata.yaml")
        if not os.path.exists(metadata_file):
            # TODO : manage error + remove package file
            plog.info('E:    [FAILLED] Manifest.json file extraction.')
            raise PirusException("XXXX", "No manifest file found.")
        metadata = None
        try :
            with open(metadata_file) as f:
                metadata = json.load(f)
            metadata = metadata["pirus"]
        except :
            # TODO : manage error
            raise PirusException("XXXX", "Bad pirus pipeline format : Manifest file corrupted.")
        plog.info('I:    [OK     ] Manifest.json file extraction.')

        # 3- Check that mandatory fields exists
        missing = ""
        for k in MANIFEST_MANDATORY.keys():
            if k not in metadata.keys():
                missing += k + ", "
        if missing != "":
            missing = missing[:-2]
            plog.info('E:    [FAILLED] Checking validity of manifest.json file. (missing : ' + missing + ")")
            raise PirusException("XXXX", "Bad pirus pipeline format : Mandory fields missing in the manifest.json file (missing : " + missing + ")")
        plog.info('I:    [OK     ] Checking validity of manifest.json file.')

        # 4- Extract pirus technicals files from the package
        ffile_src = os.path.join(ppackage_path, "rootfs",metadata['form'][1:] if metadata['form'][0]=="/" else metadata['form'])
        ffile_dst = os.path.join(ppackage_path, "form.json")
        shutil.copyfile(ffile_src, ffile_dst)
        lfile_dst = ""
        if "icon" in metadata.keys():
            lfile_src = os.path.join(ppackage_path, "rootfs",metadata['icon'][1:] if metadata['icon'][0]=="/" else metadata['icon'])
            lfile_dst = os.path.join(ppackage_path, os.path.basename(metadata['icon']))
            shutil.copyfile(lfile_src, lfile_dst)
        else:
            lfile_dst = os.path.join(ppackage_path, "logo.png")
            shutil.copyfile(os.path.join(TEMPLATE_DIR, "logo.png", lfile_dst))

        # 5- Save pipeline into database
        metadata.update({
            "path"      : ppackage_path,
            "ipath"     : metadata["inputs"],
            "opath"     : metadata["outputs"],
            "lpath"     : metadata["logs"],
            "run"       : metadata["run"],
            "dpath"     : metadata["databases"],
            "ffile"     : ffile_dst,
            "lfile"     : lfile_dst,
            "lxd_alias" : "pirus-pipe-" + ppackage_name
        })

        pipeline = Pipeline()
        try:
            pipeline.import_data(metadata)
            pipeline.save()
        except Exception as err:
            # TODO : manage error
            print(err)
            plog.info('E:    [FAILLED] Save pipeline information in database.')
            raise PirusException("XXXX", "Failed to save pipeling info into the database.")
        plog.info('I:    [OK     ] Save pipeline information in database with id='+ str(pipeline.id))

        # 6- Install lxd container
        cmd = ["lxc", "image", "import", ppackage_file, "--alias", pipeline.lxd_alias]
        try:
            out_tmp = '/tmp/' + ppackage_name + '-out'
            err_tmp = '/tmp/' + ppackage_name + '-err'
            subprocess.call(cmd, stdout=open(out_tmp, "w"), stderr=open(err_tmp, "w"))

        except Exception as err:
            # TODO : manage error
            print(err)
            plog.info('E:    [FAILLED] Installation of the lxd image. ($: ' + " ".join(cmd) + ")")
            raise PirusException("XXXX", "Failed to install pipeline lxd image.")


        err = open(err_tmp, "r").read()
        if err != "":
            # TODO : manage error
            plog.info('E:    [FAILLED] Lxd image. ($: ' + " ".join(cmd) + ")")
            plog.info('--------------------------')
            plog.info(err)
            plog.info('--------------------------')
            pipeline.delete()
            shutil.rmtree(ppackage_path)
            raise PirusException("XXXX", "Failed to install pipeline lxd image (" + err + ")")
        else:
            plog.info('I:    [OK     ] Installation of the lxd image.')

        # 7- Clean directory
        try:
            keep = [ppackage_file, ffile_dst, lfile_dst]
            for f in os.listdir(ppackage_path):
                fullpath = os.path.join(ppackage_path, f)
                if fullpath not in keep:
                    if os.path.isfile(fullpath):
                        os.remove(fullpath)
                    else:
                        shutil.rmtree(fullpath)
        except Exception as err:
            # TODO : manage error, notify only admins
            print(err)
            plog.info('E:    [FAILLED] Cleaning repository.')
        plog.info('I:    [OK     ] Cleaning repository.')
        plog.info('I:    All fine. Pipeline is ready !')
        return pipeline
        
















class Run(Document):
    pipe_id   = ObjectIdField(required=True)
    celery_id = StringField(required=True)
    name      = StringField(requiered=True)
    config    = DynamicField(required=True)
    start     = StringField(required=True)
    end       = StringField()
    status    = StringField()
    inputs    = ListField(StringField())
    outputs   = StringField()
    progress  = DynamicField(required=True)

    def __str__(self):
        return "<Run " + str(self.id) + ">"

    def export_server_data(self):
        return {
            "id"        : str(self.id),
            "pipe_id"   : str(self.pipe_id),
            "celery_id" : self.celery_id,
            "name"      : self.name,
            "config"    : self.config,
            "start"     : self.start,
            "end"       : self.end,
            "status"    : self.status,
            "inputs"    : self.inputs,
            "outputs"   : self.outputs,
            "progress"  : self.progress
        }

    def export_client_data(self):
        return {
            "id"        : str(self.id),
            "pipe_id"   : str(self.pipe_id),
            "celery_id" : self.celery_id,
            "name"      : self.name,
            "config"    : self.config,
            "start"     : self.start,
            "end"       : self.end,
            "status"    : self.status,
            "inputs"    : self.inputs,
            "outputs"   : self.outputs,
            "progress"  : self.progress
        }

    def import_data(self, data):
        try:
            self.pipe_id   = data['pipe_id']
            self.celery_id = data['celery_id']
            self.name      = data['name']
            self.config    = data['config']
            self.start     = data['start']
            self.status    = data['status']
            self.progress  = data['progress']
            if "end" in data:
                self.end = data['end']
            if "inputs" in data:
                self.inputs = data["inputs"]
            if "outputs" in data:
                self.outputs = data["outputs"]
        except KeyError as e:
            raise ValidationError('Invalid plugin: missing ' + e.args[0])
        return self 

    @staticmethod
    def from_id(run_id):
        if not ObjectId.is_valid(run_id):
            return None;
        run = Run.objects.get(pk=run_id)
        return run

    @staticmethod
    def from_celery_id(run_id):
        run = Run.objects.get(celery_id=run_id)
        return run