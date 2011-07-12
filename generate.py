from struct import *
import base64
import hashlib
import codecs
import datetime
import getopt
import httplib
import lib/image/image
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
"jp2":"image/jp2",
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
"jp2":"StillImage",
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
### class IndexInfo
class IndexInfo:
	def __init__(self):
		self.seqIx = -1
		self.targetIx = -1
		self.modelIx = -1
		self.sourceIx = -1
		self.templateIx = -1
		self.formatIx = -1
		self.idIx = -1
		self.pidIx = -1
		self.actionIx = -1
		self.licenseIx = -1;
		self.numRows = 0
		self.numPids = 0
		self.now = datetime.datetime.now()
		self.timestamp = self.now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
	def configure(self,headers):
		self.headers = headers
		self.seqIx = headers.index('sequence')
		self.targetIx = headers.index('target')
		self.modelIx = headers.index('rdf:type')
		self.sourceIx = headers.index('dc:source')
		self.templateIx = headers.index('template_type')
		self.formatIx = headers.index('dc_format')
		self.idIx = headers.index('dc:identifier')
		self.pidIx = headers.index('pid')
		self.actionIx = headers.index('action')
		self.licenseIx = headers.index('license')
    	
	def map(self,values):
		result = {}
		if len(values) != len(headers):
			print 'WARNING: Value and header arrays are mismatched!'
		for i in range(len(self.headers)):
			result[self.headers[i]] = values[i]
		return result
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
	def __init__(self,pid,fieldMap):
		self.pid = pid
		self.fieldMap = fieldMap
		self.props = {'pid' : pid,
					  'src' : fieldMap['source'],
					  'timestamp':fieldMap['timestamp'],
					  'mimetype':'',
					  'license':'license:cc-by-nd'}
		if (fieldMap.has_key('license') and fieldMap['license'] != ''):
			self.props['license'] = fieldMap['license']
		if (fieldMap.has_key('dc:identifier') and fieldMap['dc:identifier'] != ''):
			self.props['dc_identifier'] = fieldMap['identifier']
		else: self.props['dc_identifier'] = pid
		if (fieldMap.has_key('dc:title') and fieldMap['dc:title'] != ''):
			self.props['dc:title'] = fieldMap['dc:title']
		else: self.props['dc:title'] = pid
		
class IngestJob(Job):
	def __init__(self,pid,fieldMap,outDir,template):
		Job.__init__(self,pid,fieldMap)
		self.outDir = outDir
		self.template = template

	def execute(self,host,port,user,password):
		self.generateXml()
		if (user and password):
			self.ingest(host,port,user,password)
		else:
			print 'Review output mode; not posting'
		return
	def generateXml(self):
		raise "IngestJob should not be used; try a subclass"
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
		dirname = os.path.dirname(self.fpath)
		try:
			os.remove(self.fpath)
			if(debug): print 'DELETED:', self.fpath
			# delete directory if empty
			if len(os.listdir(dirname)) == 0:
				os.rmdir(dirname)
				if(debug): print 'DELETED:', dirname
		except Exception as cleanupException:
			print 'ERROR: Error cleaning up ingest files in', dirname
			print 'REASON:', str(cleanupException)
			return
	def write(self,filedata):
		fileName = self.pid.replace(':','_') + '.xml'
		if (not os.path.exists(self.outDir)):
			os.makedirs(self.outDir)
		self.fpath = os.path.join(self.outDir,fileName)
		outFile = codecs.open(self.fpath,'w','utf-8')
		if (unixgroups):
			os.fchmod(outFile.fileno(),MODE)
			os.fchown(outFile.fileno(),-1,getgrnam('ldpddev')[2])
		outFile.write(filedata)
		outFile.flush()
		outFile.close()
		
class MetadataIngestJob(IngestJob):
	def generateXml(self):
		rels = ''
		if (self.fieldMap['target'] != ''):
			targets = self.fieldMap['target'].split(';')
			for target in targets:
				rels += "<cul:metadataFor rdf:resource=\"info:fedora/%s\"/>" % (target)
			self.props['rels'] = rels
		return self.write(serializeMODSMetadata(self.pid,rels,self.fieldMap))
class AggregatorIngestJob(IngestJob):
	def generateXml(self):
		titleAttr = xml.sax.saxutils.quoteattr(self.props['dc_title'])
		titleAttr = titleAttr[1:-1]
		self.props['titleAttr'] = titleAttr
		rels = ''
		if (self.fieldMap['target'] != ''):
			targets = self.fieldMap['target'].split(';')
			for target in targets:
				rels += "<cul:memberOf rdf:resource=\"info:fedora/%s\"/>" % (target)
		self.props['rels'] = rels
		return self.write(self.template.format(self.props))
class ResourceIngestJob(IngestJob):
	def generateXml(self):
		titleAttr = xml.sax.saxutils.quoteattr(self.props['dc_title'])
		titleAttr = titleAttr[1:-1]
		self.props['titleAttr'] = titleAttr
		rels = ''
		if (self.fieldMap['target'] != ''):
			targets = self.fieldMap['target'].split(';')
			for target in targets:
				rels += "<cul:memberOf rdf:resource=\"info:fedora/%s\"/>" % (target)
		self.props['rels'] = rels

		ext = self.props['src'][self.props['src'].rfind('.')+1:]
		ext = ext.lower()
		if (ext in MT):
			self.props['mimetype'] = MT[ext]
			self.props['dc_type'] = DCTYPE[ext]
		else:
			self.props['mimetype'] = 'application/octet-stream'
			self.props['dc_type'] = 'InteractiveResource'
		if (self.props['dc_source'].find('http:') != 0 and not self.props['dc_source'].startswith('file:')):
			self.props['dc_source'] = 'file:' + self.props['dc_source']
		return self.write(self.template.format(self.props))
class ImageResourceIngestJob(IngestJob):
	def generateXml(self):
		titleAttr = xml.sax.saxutils.quoteattr(self.props['dc_title'])
		titleAttr = titleAttr[1:-1]
		self.props['titleAttr'] = titleAttr
		rels = ''
		if (self.fieldMap['target'] != ''):
			targets = self.fieldMap['target'].split(';')
			for target in targets:
				rels += "<cul:memberOf rdf:resource=\"info:fedora/%s\"/>" % (target)
		imgProps = image.identify(self.props['src'])
		self.props['dc_type'] = 'StillImage'
		self.props['mimetype'] = imgProps['mime']
		for iprop in imgProps['properties']:
			rels += iprop
		self.props['rels'] = rels
		if (self.props['src'].find('http:') != 0):
			self.props['src'] = 'file:' + self.props['src']
		return self.write(templates.IR_TEMPLATE.format(self.props))
### class: UpdateJob
class UpdateJob(Job):
	def execute(self,host,port,user,password):
			raise 'UpdateJob not implemented for direct use; try a subclass'
class UpdateMetadataJob(UpdateJob):
	def execute(self,host,port,user,password):
		fpath = self.fieldMap['source']
		if(debug): print 'ingesting', fpath
		mods = codecs.open(self.fieldMap['source'],'rU',encoding='utf-8')
		props = parseMODSforDC(mods)
		data = props['metadata'].encode('utf-8')
		dsContent = base64.encodestring(data)
		# dsContent = dsContent.encode('utf-8')
		req = templates.MODIFY_MODS.format({'pid':self.pid,'dsContent':dsContent,'timestamp':self.fieldMap['timestamp']})
		try:
			res = post(host, port, 'modifyDatastreamByValue', req, user, password)
			print 'SUCCESS: updated MODS', self.pid, self.fieldMap['source']
		except Exception as postException:
			print 'ERROR: Error posting MODS to API-M modifyDatastreamByValue', fpath
			print 'REASON:', str(postException)
			return
		data = templates.METADATA_DC.format(props).encode('utf-8')
		dsContent = base64.encodestring(data)
		# dsContent = dsContent.encode('utf-8')
		req = templates.MODIFY_DC.format({'pid':self.pid,'dsContent':dsContent,'timestamp':self.fieldMap['timestamp']})
		if (not user and not password):
			print "Review output mode: Not posting"
			return
		else:
			try:
				res = post(host, port, 'modifyDatastreamByValue', req, user, password)
				print 'SUCCESS: updated DC', self.pid, self.fieldMap['source']
			except Exception as postException:
				print 'ERROR: Error posting DC to API-M modifyDatastreamByValue', self.fieldMap['source']
				print 'REASON:', str(postException)
				return
		return
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

def countPids(inpath, headers):
	if(debug): print 'analyzing column headers and counting objects'
	f = open(inpath, 'r')
	result = IndexInfo()
	pidCtr = 0
	if headers:
		rowCtr = -1
		result.seqIx = -1
		result.targetIx = -1
		result.modelIx = -1
		result.sourceIx = -1
		result.templateIx = -1
		result.formatIx = -1
		result.idIx = -1
		result.pidIx = -1
		result.actionIx = -1
		result.licenseIx = -1
	else:
		rowCtr = 0
		result.seqIx = 0
		result.targetIx = 1
		result.modelIx = 2
		result.sourceIx = 3
		result.templateIx = 4
		result.formatIx = 5
		result.idIx = 6
		result.pidIx = 7
		result.actionIx = 8
		result.licenseIx = 9
	for line in f:
		rowCtr += 1
		if (rowCtr == 0):
			headerFields = line.lower().rstrip("\r\n").split("\t")
			result.seqIx = headerFields.index('sequence')
			result.targetIx = headerFields.index('target')
			result.modelIx = headerFields.index('model_type')
			result.sourceIx = headerFields.index('source')
			result.templateIx = headerFields.index('template_type')
			result.formatIx = headerFields.index('dc_format')
			result.idIx = headerFields.index('id')
			result.pidIx = headerFields.index('pid')
			result.actionIx = headerFields.index('action')
			result.licenseIx = headerFields.index('license')
			continue
		fields = line.split("\t")
		if not (len(fields) > result.pidIx and fields[result.pidIx] != ''):
			pidCtr += 1
	f.close()
	result.numRows = rowCtr
	result.numPids = pidCtr
	return result
## function: parseMODSforDC
def parseMODSforDC(infile):
	if (not infile):
		mprops = {}
		mprops['identifier'] = ''
		mprops['title'] = 'metadata stub'
		mprops['titleAttr'] = 'metadata stub'
		mprops['metadata'] = '<mods xmlns="http://www.loc.gov/mods/v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-2.xsd"></mods>'
		mprops['src'] = ''
		mprops['mimetype'] = ''
		return mprops

	try:
		fdata = infile.read()
		dom1 = xml.dom.minidom.parseString(fdata.encode('utf-8'))
		dom1.normalize()
      	# get title from MODS dom: /mods/titleInfo/title/text()
		title = dom1.getElementsByTagNameNS(MODS_NS,'mods').item(0).getElementsByTagNameNS(MODS_NS,'titleInfo').item(0)
		title = title.getElementsByTagNameNS(MODS_NS,'title').item(0)
		title = title.childNodes[0].data
      	# get ID from MODS dom
		mods = dom1.getElementsByTagNameNS(MODS_NS,'mods').item(0)
		mid = ''
      	# try /mods/recordInfo/recordIdentifier/text()
		if(mid == ''):
			midnodes = mods.getElementsByTagNameNS(MODS_NS,'recordInfo')
			if(midnodes.length > 0):
				midnodes = midnodes.item(0).getElementsByTagNameNS(MODS_NS,'recordIdentifier')
				if(midnodes.length > 0): mid = midnodes.item(0).childNodes[0].data
      	# if not found, try /mods/identifier/text()
			if(mid == ''):
				midnodes = mods.getElementsByTagNameNS(MODS_NS,'identifier')
				if(midnodes.length > 0): mid = midnodes.item(0).childNodes[0].data
		mprops = {}
		mprops['identifier'] = mid
		mprops['title'] = title
		titleAttr = xml.sax.saxutils.quoteattr(title)
		titleAttr = titleAttr[1:-1].replace('"','&quot;')
		mprops['titleAttr'] = titleAttr
		metadata = mods.toxml()
		mprops['src'] = infile.name
		mprops['metadata'] = metadata
		dom1.unlink()
	except Exception as parseerror:
		print "ERROR: metadata parsing error: ", infile.name
 		print "REASON:", str(parseerror)
		mprops = {}
		mprops['identifier'] = ''
		mprops['title'] = 'metadata stub'
		mprops['titleAttr'] = 'metadata stub'
		mprops['metadata'] = '<mods xmlns="http://www.loc.gov/mods/v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-2.xsd"></mods>'
		if (infile.name): mprops['src'] = infile.name
		else: mprops['src'] = 'unknown/missing'
	finally:
		if (infile):
			infile.close()
	return mprops
## function: serializeMODSMetadata
def serializeMODSMetadata(pid, rels, inpath):
	now = datetime.datetime.now()
	timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
	if not inpath:
		sys.stdout.write("ERROR: No metadata path to serialize for {0} {1}\n".format(pid,timestamp))
		return		
	if not pid:
		sys.stdout.write("ERROR: No pid associated with metadata {0} {1}\n".format(pid,timestamp))
		return		
	
	mtitle = pid
#	outpath = pid.replace(':','_') + '.xml'
	infile = False
	if (inpath[0:7] == 'http://'):
		(tname, thdrs) = urllib.urlretrieve(inpath)
		infile = codecs.open(tname,'rU',encoding='utf-8',errors='strict')
	else:
		if (os.path.exists(inpath)):
			infile = codecs.open(inpath,'rU',encoding='utf-8')
			if (debug):print "parsing ", infile.name, " for ", inpath

	mprops = parseMODSforDC(infile)
	mprops['pid'] = pid
	mprops['rels'] = rels
	mprops['timestamp'] = timestamp
	if (not infile):
		mprops['title'] = 'Load Error ' + inpath
		mprops['titleAttr'] = mprops['title']
	return templates.MM_TEMPLATE.format(mprops)
### main
opts, args = getopt.getopt(sys.argv[1:],'o:f:d:u:p:h:H:n:v','outdir=file=dir=user=password=host=headers=namespace=verbose')

filePath = False
outPath = False
fedoraHost = '127.0.0.1:8080'
user = False
password = False
headers = True
namespace = 'demo'
templateDir = '../template'
for opt, val in opts:
	if (opt == '-f'): filePath = val
	if (opt == '-o'): outPath = val
	if (opt == '-H' and val == 'false'): headers = False
	if (opt == '-h'): fedoraHost = val
	if (opt == '-u'): user = val
	if (opt == '-p'): password = val
	if (opt == '-n'): namespace = val
	if (opt == '-v'): debug += 1
# endpoint = "http://%s:8080" % (fedoraHost)
doAPIM = (user and password)
if not (filePath and outPath):
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
indexInfo = countPids(filePath,headers)
print ("seqIx=%s targetIx=%s, modelIx=%s, sourceIx=%s, templateIx=%s, formatIx=%s, idIx=%s, pidIx=%s, actionIx=%s, numRows=%s, numPids=%s" % (indexInfo.seqIx, indexInfo.targetIx, indexInfo.modelIx, indexInfo.sourceIx, indexInfo.templateIx, indexInfo.formatIx, indexInfo.idIx, indexInfo.pidIx, indexInfo.actionIx, indexInfo.numRows, indexInfo.numPids))
# YYYY-MM-DD[T]HH[:]MM[:]SS[.]mmm[Z]

if (doAPIM):
	subdirName = indexInfo.now.strftime("ingest-%Y%m%d%H%M%S%f")
else:
	subdirName = indexInfo.now.strftime("review-%Y%m%d%H%M%S%f")
if(debug): sys.stdout.write("{0} data rows{1}\n".format(indexInfo.numRows,indexInfo.timestamp))
if (not os.path.exists(outPath) ): raise InputError('output path %s does not exist'%(outPath))
#make ingest dir
outDir = os.path.join(outPath,subdirName)
os.mkdir(outDir)
# reserve pid block and parse
if (doAPIM):
	pidList = reservePids(fedoraHost, 8443, user, password, namespace, indexInfo.numPids)
else:
	pidList = []
	for num in range(0,indexInfo.numPids):
		pidList.append( "localsequence:" + str(num))
# reopen input file
inputfile = codecs.open(filePath, 'rU','utf-8')
ctr = 1 if headers else 0
pidMap = {}
# outfiles = []
jobqueue = []
for line in inputfile:
	if ctr > 0:
		ctr = ctr - 1
		continue
        # parse line
	fields = line.rstrip("\r\n").split("\t")
	if (fields[indexInfo.pidIx] != ''):
		pid = fields[indexInfo.pidIx]
	else:
		# pop pid
		pid = pidList.pop()
	fileName = pid.replace(':','_') + '.xml'
	seq = str(fields[indexInfo.seqIx])
	pidMap[seq] = pid
	title = pid
	if (indexInfo.sourceIx > -1) and (indexInfo.sourceIx < len(fields)):
		src = fields[indexInfo.sourceIx]
	else:
		src = ''
		sys.stdout.write("WARN: no source value at index {0} of {1}\n".format(indexInfo.sourceIx,filePath))
		fctr = 0		
		for field in fields:
			print fctr, field
			fctr += 1
	if (indexInfo.actionIx > -1) and (indexInfo.actionIx < len(fields)):
		action = fields[indexInfo.actionIx]
		if (action == 'update'):
			if (fields[indexInfo.modelIx] == 'Metadata'):
				jobqueue.append(UpdateMetadataJob(pid,indexInfo.map(fields)))
			else:
				sys.stdout.write("WARN: No update job implemented for " + fields[indexInfo.modelIx])
			continue		
	# build RELS
	rels = ''
	if (fields[indexInfo.targetIx] != ''):
		newVal = ''
		targets = fields[indexInfo.targetIx].split(';')
		for target in targets:
			if (len(newVal) != 0): newVal = newVal + ';'
			if (re.match('^[0-9]+$',target)): newVal = newVal + pidMap[target]
			else: newVal = newVal + target
		fields[indexInfo.targetIx] = newVal
	# write substituted file
	data = None
	# pid:,timestamp:,src:,rels:,mimetype:,title:
	titleAttr = xml.sax.saxutils.quoteattr(title)
	titleAttr = titleAttr[1:-1]
	if (fields[indexInfo.modelIx] == 'Aggregator'):
		if (fields[indexInfo.templateIx] == 'StaticImage'):
			jobqueue.append(AggregatorIngestJob(pid,indexInfo.map(fields),outDir,templates.IA_TEMPLATE))
		elif (fields[indexInfo.templateIx] == 'Content'):
			jobqueue.append(AggregatorIngestJob(pid,indexInfo.map(fields),outDir,templates.CA_TEMPLATE))
	elif (fields[indexInfo.modelIx] == 'Resource'):
		if (fields[indexInfo.templateIx] == ''):		
			jobqueue.append(ResourceIngestJob(pid,indexInfo.map(fields),outDir,templates.R_TEMPLATE))
		elif (fields[indexInfo.templateIx] == 'Image'):
			jobqueue.append(ImageResourceIngestJob(pid,indexInfo.map(fields),outDir,templates.R_TEMPLATE))
	elif (fields[indexInfo.modelIx] == 'Metadata'):
		jobqueue.append(MetadataIngestJob(pid,indexInfo.map(fields),outDir,None))
	else:
		sys.stdout.write("{0} failed at template substitution, model was  '{1}'\n".format(fields[indexInfo.seqIx],fields[indexInfo.modelIx]))
		continue
inputfile.close()
if (doAPIM): pass
for job in jobqueue:
	try:
		job.execute(fedoraHost, 8443, user, password)
	except Exception as ingesterror:
		print 'ERROR: Error processing', job.pid, job.fieldMap['template']
		print 'REASON:', str(ingesterror)
###
