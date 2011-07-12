from struct import *
import base64
import hashlib
import codecs
import datetime
import getopt
import httplib
import image
import os
import re
import stat
import string
import sys
import tempfile
import templates
import urllib
import xml.dom.minidom
import xml.parsers.expat
import xml.sax
import xml.sax.saxutils
unixgroups = (sys.platform != 'win32')
if (unixgroups): from grp import getgrnam
global serializeMODSMetadata, parseMODSforDC, APIM, MODE, debug
debug = 0
### useful values
IN_OPT = '-i'
OUT_OPT = '-o'
FEDORA_HOST_OPT = '-f'
MT = {
"pdf":"application/pdf",
"doc":"application/msword",
"rtf":"application/rtf",
"txt":"text/plain",
"xml":"text/xml",
"html":"text/html",
"htm":"text/html",
"gif":"image/gif",
"jpeg":"image/jpeg",
"jpg":"image/jpeg",
"tiff":"image/tiff",
"tif":"image/tiff",
"png":"image/png",
"bmp":"image/bmp",
}
DCTYPE = {
"pdf":"Text",
"doc":"Text",
"rtf":"Text",
"txt":"Text",
"xml":"Text",
"html":"Text",
"htm":"Text",
"gif":"StillImage",
"jpeg":"StillImage",
"jpg":"StillImage",
"tiff":"StillImage",
"tif":"StillImage",
"png":"StillImage",
"bmp":"StillImage",
}
APIM = "/fedora/services/management"
MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
SAX_PARSER = xml.sax.make_parser()
MODS_NS = "http://www.loc.gov/mods/v3"

### class: SP
class SP:
	isPid = False
	pidList = []
	buffer = None
	def start(self,name, attrs):
		if (name == 'pid'):
			self.isPid = True
			self.buffer = ''
	def end(self,name):
		if (name == 'pid'):
			self.pidList.append(self.buffer)
			# sys.stdout.write("%s\n" % (self.buffer))
			self.buffer = None
			self.isPid = False
	def cdata(self,data):
		if(self.isPid): self.buffer = self.buffer + data
### class: InputError
class InputError(Exception):
	"""Generic exception class"""
### class: IngestJob
class Job:
	def __init__(self):
          pass
class IngestJob(Job):
	def __init__(self,fpath):
		Job.__init__(self)
		self.fpath = fpath
	def execute(self,host,port,user,password):
		if (user and password):
			self.ingest(host,port,user,password)
		else:
			print 'Review mode; not posting'
		return
	def ingest(self,host, port, user, password):
		"""ingest a foxml file"""
		if(debug): print 'ingesting', self.fpath
		fdata = codecs.open(self.fpath,'rU',encoding='utf-8').read()
		req = templates.INGEST_OBJECT_XML % base64.encodestring(fdata.encode('utf-8'))
		try:
			res = post(host, port, 'ingest', req, user, password)
			print 'SUCCESS: Ingested', self.fpath
		except Exception as postException:
			print 'ERROR: Error posting to API-M ingest', self.fpath
			print 'REASON:', str(postException)
			return
			# delete input file
		
def post(host, port, SOAPAction, input, user, password):
	"""Handles making the SOAP request"""
	creds = user + ':' + password
	creds = base64.b64encode(creds)
	creds = 'Basic ' + creds
	connection = httplib.HTTPSConnection(host,port)
	myheaders={
		'Host':host,
		'Content-Type':"text/xml; charset=\"UTF-8\"",
		'Content-Length':len(input),
		'SOAPAction':'"%s"' % SOAPAction,
		'Authorization':creds,
	}
	if debug > 1:
		print input.encode('utf-8')
	connection.request ('POST', APIM, body=input.encode('utf-8'),headers=myheaders)
	response = connection.getresponse()
	responsedata = response.read()
	if response.status!=200:
		if debug > 1: print responsedata
		raise ValueError('Error connecting: %s, %s' % (response.status, response.reason))
	return responsedata

### main
opts, args = getopt.getopt(sys.argv[1:],'o:f:d:u:p:h:v','outdir=file=dir=user=password=host=verbose')

filePath = False
outPath = False
fedoraHost = '127.0.0.1:8080'
user = False
password = False
templateDir = '../template'
for opt, val in opts:
	if (opt == '-f'): filePath = val
	if (opt == '-o'): outPath = val
	if (opt == '-h'): fedoraHost = val
	if (opt == '-u'): user = val
	if (opt == '-p'): password = val
	if (opt == '-v'): debug += 1
# endpoint = "http://%s:8080" % (fedoraHost)
doAPIM = (user and password)
if not (filePath):
	print 'usage: generate.py ARGS'
	print 'args:'
	print "\t-f VALUE : path to tab-delimited input file"
	print "\t-h VALUE : name of fedora host"
	print "\t-n VALUE : namespace for generated PIDs"
	print "\t-o VALUE : path to top-level output directory"
	print "\t-p VALUE : fedora user password"
	print "\t-u VALUE : fedora user name"
	print "\t-v : increase verbosity of output [0 = success/failure message, 1 = step descriptions, 2+ = debugging"
	exit()

if (doAPIM):
  try:
    IngestJob(filePath).execute(fedoraHost, 8443, user, password)
  except Exception as ingesterror:
    print 'ERROR: Error processing'
    print 'REASON:', str(ingesterror)
###

