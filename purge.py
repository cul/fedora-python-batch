import sys
unixgroups = (sys.platform != 'win32')
if (unixgroups): from grp import getgrnam
import string
import re
from struct import *
import os
import stat
import codecs
import getopt
import datetime
import httplib
import urllib
import base64
import image
import tempfile
import xml.parsers.expat
import xml.dom.minidom
import xml.sax.saxutils
debug = 0
### useful values
IN_OPT = '-i'
OUT_OPT = '-o'
FEDORA_HOST_OPT = '-f'
APIM = "/fedora/services/management"
MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
### function: loadTemplate
def loadTemplate(fname):
	t = codecs.open(os.path.join(TEMPLATEDIR, fname), 'rU','utf-8')
	r = t.read()
	t.close()
	return r

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
### function: post
def post(host,port,SOAPAction,input,user,password):
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
### function: purgeObject
def purgeObject(host, port, user, password, pid, logMessage, force=False):
	"""Purge an object by PID"""
	if(force): force = "true"
	else: force = "false"
	req=U"""\
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
<purgeObject xmlns="http://www.fedora.info/definitions/1/0/api/">
<pid>%s</pid>
<logMessage>%s</logMessage>
<force>%s</force>
</purgeObject>
</soap:Body>
</soap:Envelope>
""" % (unicode(pid), unicode(logMessage), force)
	p = xml.parsers.expat.ParserCreate()
	sp = SP()
	p.StartElementHandler = sp.start
	p.EndElementHandler = sp.end
	p.CharacterDataHandler = sp.cdata
	try:
		res = post(host,port,'purgeObject',req, user, password)
		p.Parse(res)
	except Exception as postException:
		print 'ERROR: Error posting to API-M purgeObject', pid
		print 'REASON:', str(postException)
		raise postException
	# end parse
	return pid

### main
opts, args = getopt.getopt(sys.argv[1:],'f:d:u:p:h:v','file=dir=user=password=host=verbose')

filePath = False
outPath = False
fedoraHost = '127.0.0.1:8080'
user = False
password = False
headers = True
namespace = 'demo'
for opt, val in opts:
	if (opt == '-f'): filePath = val
	if (opt == '-h'): fedoraHost = val
	if (opt == '-u'): user = val
	if (opt == '-p'): password = val
	if (opt == '-v'): debug += 1
# endpoint = "http://%s:8080" % (fedoraHost)
if not (filePath and user and password):
	print 'usage: generate.py ARGS'
	print 'args:'
	print "\t-f VALUE : path to input file list of pid's"
	print "\t-h VALUE : name of fedora host"
	print "\t-u VALUE : fedora user name"
	print "\t-p VALUE : fedora user password"
	print "\t-v : increase verbosity of output [0 = success/failure message, 1 = step descriptions, 2+ = debugging"
	exit()

now = datetime.datetime.now()
timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

if(debug): sys.stdout.write("Purging object list \n".format(filePath))
#make ingest dir
# reserve pid block and parse
# reopen input file
inputfile = codecs.open(filePath, 'rU','utf-8')
for line in inputfile:
	pid = line.rstrip("\r\n")
	try:
		purgeObject(fedoraHost, 8443, user, password, pid, ("Purge %s from listing %s" % (now, filePath)))
		print 'SUCCESS purging', pid
	except Exception as purgeerror:
		print 'ERROR purging', pid
		print 'REASON:', str(purgeerror)
inputfile.close()
###
