#!env/python3
# coding: utf-8

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
    status       = StringField()
    comments     = StringField()
    owner        = StringField()
    create_date  = StringField()
    tags         = ListField(StringField())
    runs_stats   = DynamicField()
    md5sum       = StringField()

    def __str__(self):
        return "<InputFile " + self.file_name + " (" + self.file_size + ") : " + self.path + ">"

    def export_server_data(self):
        return {
            "file_name"    : self.file_name,
            "file_type"    : self.file_type,
            "file_path"    : self.file_path,
            "file_size"    : self.file_size,
            "status"       : self.status,
            "comments"     : self.comments,
            "owner"        : self.owner,
            "create_date"  : self.create_date,
            "tags"         : self.tags,
            "runs_stats"   : self.runs_stats,
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
            "owner"        : self.owner,
            "create_date"  : self.create_date,
            "tags"         : self.tags,
            "runs_stats"   : self.runs_stats,
            "md5sum"       : self.md5sum,
            "id": str(self.id)
        }

    def import_data(self, data):
        try:
            self.file_name    = data['file_name']
            self.file_type    = data["file_type"]
            self.file_path    = data['file_path']
            self.file_size    = data["file_size"]
            self.status       = data["status"]
            self.comments     = data["comments"]
            self.owner        = data["owner"]
            self.create_date  = data["create_date"]
            self.tags         = data['tags']
            self.runs_stats   = data['runs_stats']
            self.md5sum       = data['md5sum']
        except KeyError as e:
            raise ValidationError('Invalid input file: missing ' + e.args[0])
        return self

    @staticmethod
    def from_id(ifile_id):
        if not ObjectId.is_valid(ifile_id):
            return None;
        file = InputFile.objects.get(pk=ifile_id)
        return file
        




class Pipeline(Document):
    name           = StringField(required=True)
    description    = StringField()
    version        = StringField(required=True)
    version_api    = StringField(required=True)
    inputs_allowed = ListField(StringField())
    license        = StringField()
    authors        = ListField(StringField())

    path           = StringField(required=True)
    ipath          = StringField(required=True)
    opath          = StringField(required=True)
    lpath          = StringField(required=True)
    rpath          = StringField(required=True)
    dpath          = StringField(required=True)
    cfile          = StringField(required=True)
    ffile          = StringField(required=True)
    lfile          = StringField()

    def __str__(self):
        return "<Pipeline " + self.path + ">"

    def export_server_data(self):
        return {
            "id"             : str(self.id),
            "name"           : self.name,
            "description"    : self.description,
            "version"        : self.version,
            "version_api"    : self.version_api,
            "inputs_allowed" : self.inputs_allowed,
            "license"        : self.license,
            "authors"        : self.authors,
            "path"           : self.path,
            "ipath"          : self.ipath,
            "opath"          : self.opath,
            "lpath"          : self.lpath,
            "rpath"          : self.rpath,
            "dpath"          : self.dpath,
            "cfile"          : self.cfile,
            "ffile"          : self.ffile,
            "lfile"          : self.lfile
        }

    def export_client_data(self):
        return {
            "id"             : str(self.id),
            "name"           : self.name,
            "description"    : self.description,
            "version"        : self.version,
            "version_api"    : self.version_api,
            "inputs_allowed" : self.inputs_allowed,
            "license"        : self.license,
            "authors"        : self.authors,
            "config_json"    : "http://" + HOSTNAME + "/dl/" + str(self.id) + "/config.json",
            "form_json"      : "http://" + HOSTNAME + "/dl/" + str(self.id) + "/form.json",
            "logo"           : "http://" + HOSTNAME + "/dl/" + str(self.id) + "/" + os.path.basename(self.lfile)
        }

    def import_data(self, data):
        try:
            self.name           = data['name']
            self.version_api    = data["version_api"]
            self.path           = data['path']
            self.ipath          = data['ipath']
            self.opath          = data['opath']
            self.lpath          = data['lpath']
            self.rpath          = data['rpath']
            self.dpath          = data['dpath']
            self.cfile          = data['cfile']
            self.ffile          = data['ffile']
            if "description" in data.keys():
                self.description = data["description"]
            if "version" in data.keys():
                self.version     = data['version']
            if "inputs_allowed" in data.keys():
                self.inputs_allowed = data["inputs_allowed"]
            if "license" in data.keys():
                self.license     = data["license"]
            if "authors" in data.keys():
                self.authors     = data["authors"]
            if "lfile" in data.keys():
                self.lfile       = data['lfile']
        except KeyError as e:
            raise ValidationError('Invalid pipeline: missing ' + e.args[0])
        return self

    # def get_form(self):
    #     form = None
    #     if os.path.isfile(self.ffile):
    #         with open(self.ffile, 'r') as content_file:
    #             form = content_file.read()
    #     return form

    # def get_config(self):
    #     conf = None
    #     if os.path.isfile(self.cfile):
    #         with open(self.cfile, 'r') as content_file:
    #             conf = content_file.read()
    #     return conf

    # def get_logo(self):
    #     logo = None
    #     if os.path.isfile(self.lfile):
    #         with open(self.lfile, 'r') as content_file:
    #             logo = content_file.read()
    #     return logo

    @staticmethod
    def from_id(pipe_id):
        if not ObjectId.is_valid(pipe_id):
            return None;
        pipe = Pipeline.objects.get(pk=pipe_id)
        return pipe

    @staticmethod
    def install(ppackage_name, ppackage_path, ppackage_file):
        ppackage_file = os.path.join(ppackage_path, "PirusPipeline.tar.gz")
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
        manifest_file = os.path.join(ppackage_path, "rootfs/pipeline/manifest.json")
        if not os.path.exists(manifest_file):
            # TODO : manage error + remove package file
            plog.info('E:    [FAILLED] Manifest.json file extraction.')
            raise PirusException("XXXX", "No manifest file found.")
        manifest_data = None
        try :
            with open(manifest_file) as f:
                manifest_data = json.load(f)
        except :
            # TODO : manage error
            raise PirusException("XXXX", "Bad pirus pipeline format : Manifest file corrupted.")
        plog.info('I:    [OK     ] Manifest.json file extraction.')

        # 3- Check that mandatory fields exists
        missing = ""
        for k in MANIFEST_MANDATORY.keys():
            if k not in manifest_data.keys():
                missing += k + ", "
        if missing != "":
            missing = missing[:-2]
            plog.info('E:    [FAILLED] Checking validity of manifest.json file. (missing : ' + missing + ")")
            raise PirusException("XXXX", "Bad pirus pipeline format : Mandory fields missing in the manifest.json file (missing : " + missing + ")")
        plog.info('I:    [OK     ] Checking validity of manifest.json file.')

        # 4- Extract pirus technicals files from the package
        cfile_src = os.path.join(ppackage_path, "rootfs", manifest_data['config.json'][1:] if manifest_data['config.json'][0]=="/" else manifest_data['config.json'] )
        cfile_dst = os.path.join(ppackage_path, "config.json")
        shutil.copyfile(cfile_src, cfile_dst)
        ffile_src = os.path.join(ppackage_path, "rootfs",manifest_data['form.json'][1:] if manifest_data['form.json'][0]=="/" else manifest_data['form.json'])
        ffile_dst = os.path.join(ppackage_path, "form.json")
        shutil.copyfile(ffile_src, ffile_dst)
        lfile_dst = ""
        if "logo" in manifest_data.keys():
            lfile_src = os.path.join(ppackage_path, "rootfs",manifest_data['logo'][1:] if manifest_data['logo'][0]=="/" else manifest_data['logo'])
            lfile_dst = os.path.join(ppackage_path, os.path.basename(manifest_data['logo']))
            shutil.copyfile(lfile_src, lfile_dst)
        else:
            lfile_dst = os.path.join(ppackage_path, "logo.png")
            shutil.copyfile(os.path.join(TEMPLATE_DIR, "logo.png", lfile_dst))

        # 5- Save pipeline into database
        manifest_data.update({
            "path"  : ppackage_path,
            "ipath" : manifest_data["inputs"],
            "opath" : manifest_data["outputs"],
            "lpath" : manifest_data["logs"],
            "rpath" : manifest_data["run"],
            "dpath" : manifest_data["databases"],
            "cfile" : cfile_dst,
            "ffile" : ffile_dst,
            "lfile" : lfile_dst
            })

        pipeline = Pipeline()
        try:
            pipeline.import_data(manifest_data)
            pipeline.save()
        except Exception as err:
            # TODO : manage error
            print(err)
            plog.info('E:    [FAILLED] Save pipeline information in database.')
            raise PirusException("XXXX", "Failed to save pipeling info into the database.")
        plog.info('I:    [OK     ] Save pipeline information in database.')

        # 6- Install lxd container
        cmd = ["lxc", "image", "import", ppackage_file, "--alias", "pirus-pipe-" + ppackage_name]
        try:
            subprocess.call(cmd)
            # TODO : retrieve stdout and stderr, and check if no stderr.
        except Exception as err:
            # TODO : manage error
            print(err)
            plog.info('E:    [FAILLED] Installation of the lxd image. ($: ' + " ".join(cmd) + ")")
            raise PirusException("XXXX", "Bad pirus pipeline format : Failed to install pipeline lxd image.")
        plog.info('I:    [OK     ] Installation of the lxd image.')

        # 7- Clean directory
        try:
            keep = [ppackage_file, cfile_dst, ffile_dst, lfile_dst]
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
    pipe_name = StringField(requiered=True)
    celery_id = StringField(required=True)
    username  = StringField()
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
            "pipe_name" : self.pipe_name,
            "celery_id" : self.celery_id,
            "username"  : self.username,
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
            "pipe_name" : self.pipe_name,
            "celery_id" : self.celery_id,
            "username"  : self.username,
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
            self.pipe_name = data['pipe_name']
            self.celery_id = data['celery_id']
            self.username  = data['username']
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