#!env/python3
# coding: utf-8
import ipdb




import base64
import os
import uuid


from aiohttp import web, MultiDict
from mongoengine import *
from config import *
from framework import *
from api_v1.model import *



TUS_API_VERSION = "1.0.0"
TUS_API_VERSION_SUPPORTED = "1.0.0"
TUS_MAX_SIZE = 6250000000 # 50 Go
TUS_EXTENSION = ['creation', 'termination', 'file-check']


class TusManager:

    def __init__(self, app=None, upload_url='/file-upload', upload_folder='uploads/', overwrite=True, upload_finish_cb=None):
        pass



    def get_file_data(self, request):
        id = request.match_info.get('file_id', -1)
        if id == -1:
            return self.build_response(code=404)
        pirus_file = PirusFile.from_id(id)
        if pirus_file == None:
            return self.build_response(code=404)
        return pirus_file



    def build_response(self, code, headers={}, body=""):
        h = {'Tus-Resumable' : TUS_API_VERSION,  'Tus-Version' : TUS_API_VERSION_SUPPORTED}
        h.update(headers)
        return web.Response(body=body.encode(), status=code, headers=h)



    # HEAD request done by client to retrieve the offset where the upload of the file shall be resume
    def resume(self, request):
        pfile = self.get_file_data(request)
        return self.build_response(code=200, headers={ 'Upload-Offset' : str(pfile.upload_offset), 'Cache-Control' : 'no-store' })


    # PATCH request done by client to upload a chunk a of file.
    async def patch(self, request):
        pfile = self.get_file_data(request)
        data = await request.content.read()
        upload_file_path = pfile.path
        filename = pfile.name
        if filename is None or os.path.lexists( upload_file_path ) is False:
            # logger.info( "PATCH sent for resource_id that does not exist. {}".format( pfile.id))
            return self.build_response(code=410)
        file_offset = int(request.headers.get("Upload-Offset", 0))
        chunk_size = int(request.headers.get("Content-Length", 0))
        if file_offset != pfile.upload_offset: # check to make sure we're in sync
            return self.build_response(code=409) # HTTP 409 Conflict
        try:
            f = open( upload_file_path, "bw+")
        except IOError:
            return self.build_response(code=500, body="Unable to write file chunk on the the server :(")
        finally:
            f.seek( file_offset )
            f.write(data)
            f.close()
        pfile.upload_offset += chunk_size # self.redis_connection.incrby( "file-uploads/{}/offset".format( resource_id ), chunk_size)
        pfile.size = pfile.upload_offset
        pfile.save()
        # file transfer complete, rename from resource id to actual filename
        if pfile.size_total == pfile.upload_offset: 
            pfile.status = "DOWNLOADED"
            pfile.path = os.path.join(FILES_DIR, str(uuid.uuid4()))
            os.rename(upload_file_path, pfile.path)
            pfile.save()
        headers = { 'Upload-Offset' : str(pfile.upload_offset), 'Tus-Temp-Filename' : str(pfile.id) }
        return self.build_response(code=200, headers=headers)

    # OPTIONS request done by client to know how the server is convigured
    def options(self, request):
        return self.build_response(code=204, headers={ 'Tus-Extension' : ",".join(TUS_EXTENSION), 'Tus-Max-Size' : str(TUS_MAX_SIZE) })

    # GET request done by client to check if a file already exists in database or not
    # def exists(self, request):
    #     metadata = {}
    #     for kv in request.headers.get("Upload-Metadata", None).split(","):
    #         key, value = kv.split(" ")
    #         metadata[key] = base64.b64decode(value)

    #     if metadata.get("filename", None) is None:
    #         return self.build_response(code=404, body="metadata filename is not set")

    #     filename_name, extension = os.path.splitext( metadata.get("filename").decode())
    #     h={}
    #     if filename_name.upper() in [os.path.splitext(f)[0].upper() for f in os.listdir( os.path.dirname( self.upload_folder ))]:
    #         h.update({'Tus-File-Name' : metadata.get("filename").decode(), 'Tus-File-Exists' : True})
    #     else:
    #         h.update({'Tus-File-Exists' : False})
    #     return self.build_response(code=200, headers=h)


    # POST request done by client to start a new resumable upload
    def creation(self, request):
        if request.headers.get("Tus-Resumable", None) is None:
            return self.build_response(code=500, body="Received File upload for unsupported file transfer protocol")

        # process upload metadata
        metadata = {}
        for kv in request.headers.get("Upload-Metadata", None).split(","):
            key, value = kv.split(" ")
            metadata[key] = base64.b64decode(value)

        # if os.path.lexists( os.path.join( self.upload_folder, metadata.get("filename").decode() )) and self.file_overwrite is False:
        #     return self.build_response(code=409) # HTTP 409 Conflict

        # Retrieve data about the file
        filename  = metadata.get("filename").decode()
        path      = os.path.join(TEMP_DIR, str(uuid.uuid4()))
        file_size = int(request.headers.get("Upload-Length", "0"))
        comments  = None
        tags      = None
        # if "comments" in data.keys():
        #     comments = data['comments'].strip()
        # if "tags" in data.keys():
        #     tmps = data['tags'].split(',')
        #     tags = []
        #     for i in tmps:
        #         i2 = i.strip()
        #         if i2 != "":
        #             tags.append(i2)
        # Create file entry in database
        pirusfile   = PirusFile()
        pirusfile.import_data({
                "name"         : filename,
                "type"         : os.path.splitext(filename)[1][1:].strip().lower(),
                "path"         : path,
                "size"         : 0,
                "size_total"   : file_size,
                "offset"       : 0,
                "status"       : "DOWNLOADING",
                "create_date"  : str(datetime.datetime.now().timestamp()),
                "md5sum"       : None,
                # "tags"         : tags,
                # "comments"     : comments
            })
        pirusfile.save()

        # create empty file that allocated the needed disk space
        try:
            f = open( path, "wb")
            f.seek( file_size - 1)
            f.write("\0".encode())
            f.close()
        except IOError as e:
            return self.build_response(code=500, body="Unable to create file: {}".format(e))

        return self.build_response(code=201, headers={'Location' : pirusfile.upload_url(), 'Tus-Temp-Filename' : str(pirusfile.id)})



    # DELETE request done by client to delete a file
    def delete_file(self, request):
        pfile = self.get_file_data(request)
        os.unlink(pfile.path)
        PirusFile.remove(pfile.id)
        return self.build_response(code=204)



tus_manager = TusManager()