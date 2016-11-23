#!env/python3
# coding: utf-8
import os
import sys
import time
import logging
import json
import yaml
import subprocess
import tarfile
import shutil

from mongoengine import *
from bson.objectid import ObjectId


#from config import *
from core.framework import *




# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# DATABASE CONNECTION
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

connect(DATABASE_NAME)







# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# MODEL DEFINITION
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 


class PirusFile(Document):
    public_fields = ["id", "name", "type", "size", "status", "upload_offset", "comments", "runs", "create_date", "tags", "md5sum", "url", "upload_url", "source"]

    name          = StringField(required=True)
    type          = StringField()
    path          = StringField()
    size          = IntField() 
    upload_offset = IntField()
    status        = StringField() # UPLOADING, UPLOADED, PAUSE, ERROR, CHECKED
    comments      = StringField()    
    runs          = ListField(StringField())
    create_date   = StringField()
    tags          = ListField(StringField())
    md5sum        = StringField()
    url           = StringField()
    upload_url    = StringField()
    source        = DynamicField()


    def __str__(self):
        return self.name + " (" + str(self.size) + ") : " + self.path


    def export_server_data(self):
        return {
            "name"          : self.name,
            "type"          : self.type,
            "path"          : self.path,
            "size"          : self.size,
            "upload_offset" : self.upload_offset,
            "status"        : self.status,
            "comments"      : self.comments,
            "runs"          : self.runs,
            "create_date"   : self.create_date,
            "tags"          : self.tags,
            "md5sum"        : self.md5sum,
            "id"            : str(self.id),
            "url"           : self.url,
            "upload_url"    : self.upload_url
        }


    def export_client_data(self, sub_level_loading=0, fields=None):
        result = {}
        if fields is None:
            fields = PirusFile.public_fields

        for k in fields:
            if k == "id":
                result.update({"id" : str(self.id)})
            elif k =="create_date":
                d =  datetime.datetime.fromtimestamp(float(self.create_date))
                result.update({"create_date" : str(d.year) + "/" + str(d.month) + "/" + str(d.day) + " - " + str(d.hour) + ":" + str(d.minute)})
            elif k == "runs":
                if sub_level_loading == 0:
                    result.update({"runs" : [{"id" : str(r.id), "name" : r.name, "url": r.url} for r in Run.from_ids(self.runs)]})
                else:
                    result.update({"runs" : [r.export_client_data(sub_level_loading-1) for r in Run.from_ids(self.runs)]})
            else:
                result.update({k : eval("self."+k)})
        return result


    def import_data(self, data):
        try:
            if "name"          in data.keys(): self.name           = data['name']
            if "type"          in data.keys(): self.type           = data['type']
            if "path"          in data.keys(): self.path           = data['path']
            if "size"          in data.keys(): self.size           = int(data["size"])
            if "upload_offset" in data.keys(): self.upload_offset  = int(data["upload_offset"])
            if "status"        in data.keys(): self.status         = data['status']
            if "create_date"   in data.keys(): self.create_date    = data['create_date']
            if "md5sum"        in data.keys(): self.md5sum         = data["md5sum"]
            if "runs"          in data.keys(): self.runs           = data["runs"]
            if "tags"          in data.keys(): self.tags           = data['tags']
            if "comments"      in data.keys(): self.comments       = data["comments"]
            if "source"        in data.keys(): self.source         = data["source"]
            self.save()
        except KeyError as e:
            raise ValidationError('Invalid input file: missing ' + e.args[0])
        return self


    @staticmethod
    def new_from_tus(filename, file_size):
        pfile   = PirusFile()
        pfile.name = filename
        pfile.type = os.path.splitext(filename)[1][1:].strip().lower()
        pfile.path = os.path.join(TEMP_DIR, str(uuid.uuid4()))
        pfile.size = int(file_size)
        pfile.upload_offset = 0
        pfile.status = "UPLOADING"
        pfile.create_date = str(datetime.datetime.now().timestamp())
        pfile.source =  {"type" : "upload"}
        pfile.save()
        pfile.url = "http://" + HOSTNAME + "/dl/f/" + str(pfile.id)
        pfile.upload_url = "http://" + HOSTNAME + "/file/upload/" + str(pfile.id)
        pfile.save()
        return pfile


    @staticmethod
    def from_id(id):
        if not ObjectId.is_valid(id):
            return None;
        file = PirusFile.objects(pk=id)
        return file[0] if len(file) > 0 else None


    @staticmethod
    def from_ids(ids):
        result = []
        for id in ids:
            f = PirusFile.from_id(id)
            if f is not None:
                result.append(f)
        return result







class Pipeline(Document):
    # Static
    public_fields    = ["name", "description", "version", "pirus_api", "license", "developers", "size", "upload_offset", "status", "id", "icon_url", "form_url", "url", "upload_url"]
    # Metadata
    name             = StringField(required=True)
    description      = StringField()
    version          = StringField()
    pirus_api        = StringField(required=True)
    license          = StringField()
    developers       = ListField(StringField())
    icon_url         = StringField()
    form_url         = StringField()
    upload_url       = StringField()
    url              = StringField()
    # Upload data
    size             = IntField(required=True)
    upload_offset    = IntField(required=True)
    status           = StringField(required=True) # UPLOADING, PAUSE, ERROR, INSTALLING, READY
    # Internal data (run deployment)
    pipeline_file    = StringField(required=True)
    root_path        = StringField()
    lxd_alias        = StringField()
    lxd_inputs_path  = StringField()
    lxd_outputs_path = StringField()
    lxd_logs_path    = StringField()
    lxd_db_path      = StringField()
    lxd_run_cmd      = StringField()
    form_file        = StringField()
    icon_file        = StringField()

    def __str__(self):
        return self.pipeline_file


    def export_server_data(self):
        return {
            "id"               : str(self.id),
            "name"             : self.name,
            "description"      : self.description,
            "version"          : self.version,
            "pirus_api"        : self.pirus_api,
            "license"          : self.license,
            "developers"       : self.developers,
            "size"             : self.size,
            "upload_offset"    : self.upload_offset,
            "status"           : self.status,
            "pipeline_file"    : self.pipeline_file,
            "root_path"        : self.root_path,
            "lxd_alias"        : self.lxd_alias,
            "lxd_inputs_path"  : self.lxd_inputs_path,
            "lxd_outputs_path" : self.lxd_outputs_path,
            "lxd_logs_path"    : self.lxd_logs_path,
            "lxd_db_path"      : self.lxd_db_path,
            "lxd_run_cmd"      : self.lxd_run_cmd,
            "form_file"        : self.form_file,
            "icon_file"        : self.icon_file,
            "url"              : self.url,
            "upload_url"       : self.upload_url
        }


    def export_client_data(self, sub_level_loading=0, fields=None):
        result = {}
        if fields is None:
            fields = Pipeline.public_fields

        for k in fields:
            if k == "id":
                result.update({"id" : str(self.id)})
            else:
                result.update({k : eval("self."+k)})
        # Sublevel loading ? (Children of Pipeline are Run that are using it)
        if sub_level_loading > 0:
            result.update({"runs" : [r.export_client_data(sub_level_loading-1) for r in Run.objects(pipeline_id=self.id)]}) 
        return result


    def import_data(self, data):
        try:
            # Required fields
            if "name"             in data.keys(): self.name             = data['name']
            if "pirus_api"        in data.keys(): self.pirus_api        = data["pirus_api"]
            if "size"             in data.keys(): self.size             = int(data["size"])
            if "upload_offset"    in data.keys(): self.upload_offset    = int(data["upload_offset"])
            if "status"           in data.keys(): self.status           = data["status"]
            if "pipeline_file"    in data.keys(): self.pipeline_file    = data["pipeline_file"]
            if "description"      in data.keys(): self.description      = data["description"]
            if "version"          in data.keys(): self.version          = data['version']
            if "license"          in data.keys(): self.license          = data["license"]
            if "developers"       in data.keys(): self.developers       = data["developers"]
            if "root_path"        in data.keys(): self.root_path        = data['root_path']
            if "lxd_alias"        in data.keys(): self.lxd_alias        = data['lxd_alias']
            if "lxd_inputs_path"  in data.keys(): self.lxd_inputs_path  = data['lxd_inputs_path']
            if "lxd_outputs_path" in data.keys(): self.lxd_outputs_path = data['lxd_outputs_path']
            if "lxd_logs_path"    in data.keys(): self.lxd_logs_path    = data['lxd_logs_path']
            if "lxd_db_path"      in data.keys(): self.lxd_db_path      = data['lxd_db_path']
            if "lxd_run_cmd"      in data.keys(): self.lxd_run_cmd      = data['lxd_run_cmd']
            
            if "form_file"  in data.keys():
                self.form_file = data['form_file']
                self.form_url = "http://" + HOSTNAME + "/pipeline/" + str(self.id) + "/form.json"
            if "icon_file" in data.keys():
                self.icon_file = data['icon_file']
                self.icon_url = "http://" + HOSTNAME + "/pipeline/" + str(self.id) + "/" + os.path.basename(self.icon_file)
        except KeyError as e:
            raise ValidationError('Invalid pipeline: missing ' + e.args[0])
        return self


    @staticmethod
    def new_from_tus(filename, file_size):
        pipe   = Pipeline()
        pipe.import_data({
                "name"          : filename,
                "pirus_api"     : "Unknow",
                "pipeline_file" : os.path.join(TEMP_DIR, str(uuid.uuid4())),
                "size"          : file_size,
                "upload_offset" : 0,
                "status"        : "WAITING"
            })  
        pipe.save()
        pipe.url = "http://" + HOSTNAME + "/pipeline/" + str(pipe.id)
        pipe.upload_url = "http://" + HOSTNAME + "/pipeline/upload/" + str(pipe.id)
        pipe.save()
        return pipe


    @staticmethod
    def from_id(pipe_id):
        if not ObjectId.is_valid(pipe_id):
            return None;
        pipe = Pipeline.objects(pk=pipe_id)
        return pipe[0] if len(pipe) > 0 else None

        
    @staticmethod
    def from_ids(ids):
        result = []
        for id in ids:
            p = Pipeline.from_id(id)
            if p is not None:
                result.append(p)
        return result
















class Run(Document):
    public_fields = ["id", "pipeline_id", "name", "config", "start", "end", "status", "inputs", "outputs", "progress", "url"]

    pipeline_id = ObjectIdField(required=True) # id of the pipe used for this run
    lxd_container  = StringField()
    lxd_image  = StringField(required=True)
    name       = StringField(requiered=True)  # 
    config     = DynamicField(required=True)
    start      = StringField(required=True)
    end        = StringField()
    status     = StringField()  # WAITING, PAUSE, INITIALIZING, RUNNING, FINISHING, ERROR, DONE, CANCELED
    inputs     = ListField(StringField())
    outputs    = ListField(StringField())
    progress   = DynamicField(required=True)

    url        = StringField()
    notify_url = StringField()

    def __str__(self):
        return str(self.id)


    def export_server_data(self):
        return {
            "id"        : str(self.id),
            "pipeline_id"   : str(self.pipeline_id),
            "lxd_container" : self.lxd_container,
            "lxd_image" : self.lxd_image,
            "name"      : self.name,
            "config"    : self.config,
            "start"     : self.start,
            "end"       : self.end,
            "status"    : self.status,
            "inputs"    : self.inputs,
            "outputs"   : self.outputs,
            "progress"  : self.progress,
            "url"       : self.url,
            "notify_url": self.notify_url
        }


    def export_client_data(self, sub_level_loading=0, fields=None):
        result = {}
        if fields is None:
            fields = Run.public_fields

        for k in fields:
            if k == "id":
                result.update({"id" : str(self.id)})
            elif k == "pipeline_id":
                result.update({"pipeline_id" : str(self.pipeline_id)})
            elif k == "config":
                result.update({"config" : json.loads(self.config)})
            elif k == "inputs":
                if sub_level_loading == 0:
                    result.update({"inputs" : [{"id" : str(f.id), "name" : f.name, "url": f.url} for f in PirusFile.from_ids(self.inputs)]})
                else:
                    result.update({"inputs" : [f.export_client_data(sub_level_loading-1) for f in PirusFile.from_ids(self.inputs)]})
            elif k == "outputs":
                if sub_level_loading == 0:
                    result.update({"outputs" : [{"id" : str(f.id), "name" : f.name, "url": f.url} for f in PirusFile.from_ids(self.outputs)]})
                else:
                    result.update({"outputs" : [f.export_client_data(sub_level_loading-1) for f in PirusFile.from_ids(self.outputs)]})
            else:
                result.update({k : eval("self."+k)})
        return result


    def import_data(self, data):
        try:
            self.pipeline_id   = data['pipeline_id']
            self.lxd_image = data['lxd_image']
            self.name      = data['name']
            self.config    = data['config']
            self.start     = data['start']
            self.status    = data['status']
            self.progress  = data['progress']
            if "lxd_container" in data:
                self.lxd_container = data['lxd_container']
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
        run = Run.objects(pk=run_id)
        return run[0] if len(run) > 0 else None



    @staticmethod
    def from_ids(ids):
        result = []
        for id in ids:
            r = Run.from_id(id)
            if r is not None:
                result.append(r)
        return result




