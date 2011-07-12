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
### function: post
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
### function: reservePids
def reservePids(host, port, user, password, namespace, numPids):
	"""Reserve the next block of PIDs"""
	req = templates.RESERVE_PIDS % (unicode(str(numPids)), unicode(namespace))
	p = xml.parsers.expat.ParserCreate()
	sp = SP()
	p.StartElementHandler = sp.start
	p.EndElementHandler = sp.end
	p.CharacterDataHandler = sp.cdata
	try:
		res = post(host,port,'getNextPID',req, user, password)
		p.Parse(res)
	except Exception as postException:
		print 'ERROR: Error posting to API-M getNextPID'
		print 'REASON:', str(postException)
		raise postException
	# end parse
	return sp.pidList

### main
opts, args = getopt.getopt(sys.argv[1:],'o:h:u:p:n:x:v','outdir=host=user=password=namespace=extent=verbose')

filePath = False
outPath = False
fedoraHost = '127.0.0.1:8080'
user = False
password = False
numPids = False
namespace = 'demo'
templateDir = '../template'
for opt, val in opts:
	if (opt == '-o'): outPath = val
	if (opt == '-h'): fedoraHost = val
	if (opt == '-u'): user = val
	if (opt == '-p'): password = val
	if (opt == '-n'): namespace = val
	if (opt == '-x'): numPids = val
	if (opt == '-v'): debug += 1
# endpoint = "http://%s:8080" % (fedoraHost)
doAPIM = (user and password)

# reserve pid block and parse
if (doAPIM):
        if (numPids):
	  pidList = reservePids(fedoraHost, 8443, user, password, namespace, numPids)
        else:
          print 'No -x value to determine numPids'
          pidList = []
        if (outPath):
          # print to file
          for pid in pidList:
            print pid
        else:
          for pid in pidList:
            print pid
          # print all reserved pids
else:
  print 'No input parms!'
# print usage and exit
# reopen input file
###

