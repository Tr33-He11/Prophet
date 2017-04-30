import shutil
import os
import fileutil
import socket
import color
import re

DEBUG=False

HOST_INFO_STRING = """
{0}

{1}
{2}
"""

#colors
port_color=color.cyan
host_color=color.red
script_color=color.yellow
important_color=color.red
interesting_color=color.magenta
info_color = color.blue



def getInfoObj(host, detailed = True):
	info = {}
	path = fileutil.getPortPath(host, None)
	#get sysinfo
	info["name"] = host
	info["system_info"] = fileutil.read(os.path.join(path,'system_info.txt'))
	info["ports"] = []

	
	res = getScanResults(path)
	info["scan_results"] = res

	#get ports(if host), recurse if requested
	for filename in os.listdir(path):
		filepath = os.path.join(path, filename)
		if os.path.isdir(filepath):
			portObj = getPortInfoObj(filepath, detailed)
			if portObj: info["ports"].append(portObj)

	return info

def getPortInfoObj(portpath, detailed = True):
	portObj = {}
	portObj["name"] = portpath.split('/')[-1]

	portObj["service_info"] = fileutil.readAsJSON(os.path.join(portpath,'service_info.json'))
	if detailed:

		results = getScanResults(portpath)

		portObj["scan_results"] = results
	else:
		portObj["scan_results"] = {}

	return portObj

def getScanResults(path):
	scan_results = []

	for scanFileName in os.listdir(path):
		scanFilePath = os.path.join(path, scanFileName)
		if os.path.isfile(scanFilePath) and scanFilePath.endswith(".scan.txt"):
			scanObj = {}
			scanObj["name"] = scanFilePath.split('/')[-1][:-9]
			scanObj["text"] = fileutil.read(scanFilePath)

			
			scan_results.append(scanObj)
	return scan_results

def getHosts():
	hosts = []

	path = fileutil.getPortPath(None, None)
	p = os.listdir(path)

	#sort ip addresses
	p = sorted(p,key=lambda item: socket.inet_aton(item))

	for filename in p:
		hosts.append(filename.split('/')[-1])

	return hosts

def listHosts():
	info = ""

	return host_color + '\n'.join(getHosts()) + color.neutral

def getInfoString(host, port=None, script_filter=None):
	if not host: return listHosts()

	detail_port = not port is None
	#display host details only if not infoing port or infoing everything
	detail_host = True
	if not port is None:
		detail_host = (port == 'all') or not script_filter is None
		
	info = getInfoObj(host, detail_port)

	return parseHostString(info, port, detail_host, script_filter)


def getRegex(string):
	r=None
	if not string is None:
		r = re.compile(string, re.IGNORECASE)
	else:
		r = re.compile('.*')
	return r

def parseHostString(hostObj, port=None, detail_host=True,script_filter=None):
	infostring = ""
	host = hostObj["name"]
	script_filter_regex = getRegex(script_filter)

	for portObj in sorted(hostObj["ports"], key=lambda x: int(x["name"].split(".")[1])):
		#port filter
		if port is None or port == 'all' or port in portObj["name"]:	
			infostring += parsePortObj(portObj, script_filter)

	infostring += port_color + "_"*40 + color.neutral + '\n'

	scanstring = ""
	#host level scripts
	if detail_host:
		for script in hostObj["scan_results"]:
			if script_filter_regex.match(script["name"]):
				scanstring += getScanString(script["name"],script["text"])
		scanstring += hostObj["system_info"]

	#reformat infostring to host template
	host_header = host_color + '_'*15 + host + '_'*15 + color.neutral
	infostring = HOST_INFO_STRING.format(host_header, infostring, scanstring)

	return infostring


def parsePortObj(portObj, script_filter=None):
	script_filter_regex = getRegex(script_filter)
	port_header = port_color + (portObj["name"].upper() + ("_" * 40))[:40] + "\n" + color.neutral

	if DEBUG: print 'parsePortObj: ' + str(portObj["service_info"])
	scanstring = port_header

	for key in portObj["service_info"]:
		scanstring += color.string(info_color, "{0}: {1}\n".format(key.replace('_',' '),portObj["service_info"][key]))

	for script in portObj["scan_results"]:	
		if script_filter_regex.match(script["name"]):
			scanstring += getScanString(script["name"],script["text"])

	return scanstring

def getScanString(name, text):
	#highlight vulns
	vuln_token='//<vuln_aveqvd>//'
	vuln_regex = re.compile('vulnerable', re.IGNORECASE)
	text = re.sub(vuln_regex,vuln_token, text)
	notvuln_regex = re.compile('not '+vuln_token, re.IGNORECASE)
	text = re.sub(notvuln_regex, color.string(interesting_color, 'NOT VULNERABLE'), text)
	text = re.sub(vuln_token, color.string(important_color, 'VULNERABLE'), text)

	#important things I want to know
	interesting_things = ['Script execution failed (use -d to debug)','Forbidden']
	for thing in interesting_things:
		regex = re.compile(re.escape(thing), re.IGNORECASE)
		regex.sub(thing, color.string(interesting_color, thing.upper()))

	important_things = ['Success']
	for thing in important_things:
		regex = re.compile(re.escape(thing), re.IGNORECASE)
		regex.sub(thing, color.string(important_color, thing.upper()))


	return "\n{2}{0}{3}\n______________\n{1}\n_________\n".format(name,text, script_color, color.neutral)

