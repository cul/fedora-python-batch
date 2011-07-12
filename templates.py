import sys
import os
import codecs
### function: loadTemplate
def loadTemplate(fname):
	t = codecs.open(os.path.join(TEMPLATEDIR, fname), 'rU','utf-8')
	r = t.read()
	t.close()
	return r
### template strings
TEMPLATEDIR = os.path.join('..','..','resources','templates')
CA_TEMPLATE = loadTemplate('ContentAggregatorTemplate.xml')
IA_TEMPLATE = loadTemplate('StaticImageAggregatorTemplate.xml')
MM_TEMPLATE = loadTemplate('MODSMetadataTemplate.xml')
IR_TEMPLATE = loadTemplate('ImageResourceTemplate.xml')
R_TEMPLATE = loadTemplate('ResourceTemplate.xml')
#BA_TEMPLATE = loadTemplate('BagAggregatorTemplate.xml')

RESERVE_PIDS=U"""\
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
<getNextPID xmlns="http://www.fedora.info/definitions/1/0/api/">
<numPIDs>%s</numPIDs>
<pidNamespace>%s</pidNamespace>
</getNextPID>
</soap:Body>
</soap:Envelope>
"""

INGEST_OBJECT_XML = U"""\
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
<ingest xmlns="http://www.fedora.info/definitions/1/0/api/">
<objectXML xmlns="http://www.fedora.info/definitions/1/0/api/">%s</objectXML>
<format xmlns="http://www.fedora.info/definitions/1/0/api/">info:fedora/fedora-system:FOXML-1.1</format>
<logMessage xmlns="http://www.fedora.info/definitions/1/0/api/">Batch Load</logMessage>
</ingest>
</soap:Body>
</soap:Envelope>
"""

MODIFY_MODS = U"""\
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
<modifyDatastreamByValue xmlns="http://www.fedora.info/definitions/1/0/api/">
<pid>{0[pid]}</pid>
<dsID>CONTENT</dsID>
<altIDs></altIDs>
<dsLabel>MODS Desciptive Metadata</dsLabel>
<MIMEType>text/xml</MIMEType>
<formatURI>http://www.loc.gov/mods/v3</formatURI>
<dsContent xsi:type="xsd:base64Binary">{0[dsContent]}</dsContent>
<checksumType>DISABLED</checksumType>
<checksum>none</checksum>
<logMessage>Batch update</logMessage>
<force xsi:type="xsd:boolean">false</force>
</modifyDatastreamByValue>
</soap:Body>
</soap:Envelope>
"""

MODIFY_DC = U"""\
<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
<modifyDatastreamByValue xmlns="http://www.fedora.info/definitions/1/0/api/">
<pid>{0[pid]}</pid>
<dsID>DC</dsID>
<altIDs></altIDs>
<dsLabel>Dublin Core Metadata</dsLabel>
<MIMEType>text/xml</MIMEType>
<formatURI>http://www.openarchives.org/OAI/2.0/oai_dc/</formatURI>
<dsContent xsi:type="xsd:base64Binary">{0[dsContent]}</dsContent>
<checksumType>DISABLED</checksumType>
<checksum>none</checksum>
<logMessage>Batch update</logMessage>
<force xsi:type="xsd:boolean">false</force>
</modifyDatastreamByValue>
</soap:Body>
</soap:Envelope>
"""

METADATA_DC = U"""\
<oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" >
<dc:title>{0[title]}</dc:title>
<dc:creator>BATCH</dc:creator>
<dc:type>Text</dc:type>
<dc:format>text/xml</dc:format>
<dc:publisher>Columbia University Libraries</dc:publisher>
<dc:identifier>{0[identifier]}</dc:identifier>
<dc:source>{0[src]}</dc:source>
</oai_dc:dc>
"""