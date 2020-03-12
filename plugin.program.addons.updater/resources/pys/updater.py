#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys,os,re,shutil,urllib
import xbmc,xbmcgui,xbmcaddon,xbmcplugin
from io import BytesIO

def fix_encoding(path):
	if sys.platform.startswith('win'):return unicode(path,'utf-8')
	else:return unicode(path,'utf-8').encode('ISO-8859-1')

addon_ =  xbmcaddon.Addon()
addon_path_ = fix_encoding(addon_.getAddonInfo('path'))
special_path_addons_ = fix_encoding(xbmc.translatePath('special://home/addons'))

sys.path.append(os.path.join(addon_path_,'resources','libs'))
import fixetzip as zipfile
import requests

def add_dir(title,url,img,mode):
    u=sys.argv[0]+'?title=' + urllib.quote_plus(title) + '&url=' + urllib.quote_plus(url) + '&img=' + urllib.quote_plus(img) + '&mode=' + str(mode)
    lis=xbmcgui.ListItem(title,iconImage='DefaultFolder.png',thumbnailImage=img)
    lis.setInfo(type='Video',infoLabels={'Title':title} )
    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=lis,isFolder=True)

def load_zip_content(url,timeout=15):

	headers_dict = {
		'User-Agent':'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
		'Accept-Language':'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
		'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
		'Connection':'keep-alive',
		'Upgrade-Insecure-Requests':'1'}

	try:

		ses= requests.Session()
		content_bytes_len = int(0)
		req = ses.get(url,stream=False,allow_redirects=False,timeout=timeout,headers=headers_dict)

		if req.status_code in [301,302,307]:

			url = req.headers.get('Location')
			req = ses.get(url,stream=True,allow_redirects=True,timeout=timeout,headers=headers_dict)

			content_bytes_len = int(req.headers.get('content-length',0))
			if content_bytes_len == 0:content_bytes_len = len(ses.get(url,stream=False,allow_redirects=True,timeout=timeout,headers=headers_dict).content)

		if req.status_code == 200:

			dp = xbmcgui.DialogProgress()
			dp.create('[COLOR blue]DOWNLOAD ZIP CONTENT[/COLOR]','Loading data !','Please wait ...')
			dp.update(0)

			chunk_len= int(0)
			bytes = BytesIO()

			while True:

				chunk = req.raw.read(1024*8)
				if not chunk:break

				chunk_len += len(chunk)
				bytes.write(chunk)

				try:
					percent = min(chunk_len * 100 / content_bytes_len ,100)
					dp.update(percent)
				except:pass

				if dp.iscanceled():
					ses.close()
					dp.close()
					sys.exit(0)

			ses.close()
			dp.close()
			return bytes

	except Exception as exc:
		xbmcgui.Dialog().ok('[COLOR red]DOWNLOAD ZIP CONTENT ERROR[/COLOR]',str(exc))
		sys.exit(0)

def extract_zip(bytes,extract_path,zip_pwd=None):

	try:

		dp = xbmcgui.DialogProgress()
		dp.create('[COLOR blue]EXTRACT ZIP CONTENT[/COLOR]','Unpacking data !','Please wait ...')
		dp.update(0)

		zip = zipfile.ZipFile(bytes,mode='r',compression=zipfile.ZIP_STORED,allowZip64=True)

		count = int(0)
		namelist = zip.namelist()
		list_len = len(namelist)

		content_addon_xml_info =''
		content_name = namelist[0]
		if content_name.endswith('/') or content_name.endswith('\\'):content_name = content_name[:-1]

		if os.path.exists(os.path.join(extract_path,content_name)):
			shutil.rmtree(os.path.join(extract_path,content_name),ignore_errors=True)

		for name in namelist:

			if 'addon.xml' in name:
				with zip.open(name) as fi:
					content_addon_xml_info = re.findall('addon id="(.*?)"[\s\S]*?version="(.*?)"',fi.read())[0]

			count += 1
			try:
				percent = min(count * 100 / list_len ,100)
				dp.update(percent)
			except:pass

			zip.extract(name,path=extract_path,pwd=zip_pwd)

			if dp.iscanceled():
				zip.close()
				dp.close()
				sys.exit(0)

		zip.close()
		dp.close()

		return [content_name,content_addon_xml_info]

	except Exception as exc:
		xbmcgui.Dialog().ok('[COLOR red]EXTRACT ZIP CONTENT ERROR[/COLOR]',str(exc))
		sys.exit(0)


def update_data(special_path_addons,content_name,content_addon_xml_info):

	try:

		addon_id = content_addon_xml_info[0]
		addon_version = content_addon_xml_info[1]

		if ((os.path.exists(os.path.join(special_path_addons,addon_id))) and not (content_name == addon_id)):
			shutil.rmtree(os.path.join(special_path_addons,addon_id),ignore_errors=True)

		if((os.path.exists(os.path.join(special_path_addons,content_name))) and not (content_name == addon_id)):
			os.rename(os.path.join(special_path_addons,content_name),os.path.join(special_path_addons,addon_id))

		xbmcgui.Dialog().ok('[COLOR blue]WRITE NEW DATA[/COLOR]','ADDON ID : ' + addon_id + '\nVERSION    : ' + addon_version)

	except Exception as exc:
		xbmcgui.Dialog().ok('[COLOR red]WRITE NEW DATA ERROR[/COLOR]',str(exc))
		sys.exit(0)


def get_params():

	param=[]
	paramstring=sys.argv[2]

	if len(paramstring)>=2:
		params=sys.argv[2]
		cleanedparams=params.replace('?','')

		if (params[len(params)-1]=='/'):
			params=params[0:len(params)-2]
		pairsofparams=cleanedparams.split('&')

		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')

			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]

		return param
	
params=get_params()

title=None
url=None
img=None
mode=None

try:title=urllib.unquote_plus(params['title'])
except:pass
try:url=urllib.unquote_plus(params['url'])
except:pass
try:img=urllib.unquote_plus(params['img'])
except:pass
try:mode=int(urllib.unquote_plus(params['mode']))
except:pass

if mode == None:

	with open(os.path.join(addon_path_,'data.txt')) as fi:
		for data in fi:
			if data.count('*') == 2:

				title = data.split('*')[0].strip()
				url = data.split('*')[1].strip()
				img = data.split('*')[2].strip()
				img = os.path.join(addon_path_,'resources','images',img)

				if len(title) > 0 and len(url) > 0:
					add_dir(title,url,img,1)

elif mode == 1:

	bytes = load_zip_content(url)
	xbmc.sleep(500)
	content_name,content_addon_xml_info = extract_zip(bytes,special_path_addons_)
	xbmc.sleep(500)
	update_data(special_path_addons_,content_name,content_addon_xml_info)
	sys.exit(0)

xbmcplugin.endOfDirectory(handle=int(sys.argv[1]),succeeded=True,updateListing=False,cacheToDisc=False)