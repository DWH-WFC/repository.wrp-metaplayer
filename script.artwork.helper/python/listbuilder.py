import sys
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
from xbmcaddon import Addon

def handle_pluginlist():
    path = _get_pluginpath(True)
    uselist = None
    if path['path'][0] == 'multiimage':
        if len(path['path']) == 1:
            uselist = stitch_multiimage(path['query'])
        elif path['path'][1] in ('listitem', 'player', 'container'):
            uselist = get_listitem_multiimage(path['query'], path['path'][1])
        elif path['path'][1] == 'smartseries':
            uselist = get_smartseries_multiimage(path['query'])
    _build_list(uselist, path['handle'])

def _get_pluginpath(doublequerysplit=False):
    path = sys.argv[0].split('://')[1].rstrip('/').split('/')[1:] # cuts out addon id
    query_list = sys.argv[2].lstrip('?').split('&&' if doublequerysplit else '&')
    query = {}
    if query_list and query_list[0]:
        for item in query_list:
            key, value = item.split("=", 1)
            if key in query:
                if isinstance(query[key], list):
                    query[key].append(value)
                else:
                    query[key] = [query[key], value]
            else:
                query[key] = value

    return {'handle': int(sys.argv[1]), 'path': path, 'query': query}

def _build_list(items, handle):
    xbmcplugin.setContent(handle, 'files')
    if items:
        xbmcplugin.addDirectoryItems(handle, [_build_item(item) for item in items])
    xbmcplugin.endOfDirectory(handle)

def _build_item(item):
    if item.startswith('image://'):
        item = unquote(item[8:-1])
    result = xbmcgui.ListItem(item)
    result.setMimeType(_get_mimetype(item))
    return (item, result)

mimemap = {'jpg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif'}
def _get_mimetype(url):
    for ext in mimemap:
        if url.endswith(ext):
            return mimemap[ext]
    return 'image/jpeg'

def stitch_multiimage(query):
    if 'image' not in query or not query['image']:
        return []
    if isinstance(query['image'], list):
        return [image for image in query['image'] if image]
    return [query['image']]

def get_listitem_multiimage(query, source='listitem'):
    if not query.get('refresh'):
        return []
    defarttype = 'artist.fanart' if source == 'player' else \
        'tvshow.fanart' if source == 'container' else 'fanart'
    arttypes = [query.get('arttype', defarttype)]
    if query.get('allartists', ('true' if source == 'player' else 'false')) == 'true' \
    and arttypes[0].startswith(('artist.', 'albumartist.')):
        atype = arttypes[0].split('.', 1)[1]
        mtype = 'albumartist.' if arttypes[0].startswith('artist.') else 'artist.'
        arttypes.append(mtype + atype)
        for i in range(1, 5):
            arttypes.append('artist{0}.{1}'.format(i, atype))
            arttypes.append('albumartist{0}.{1}'.format(i, atype))
    infolabel = 'Player.' if source == 'player' else \
        'Container.' if source == 'container' else \
        'ListItem.' if 'containerid' not in query else \
        'Container.ListItem.' if not query['containerid'] else \
        'Container({0}).ListItem.'.format(query['containerid'])
    artlabel = infolabel + 'Art({0}{1})'
    count = 0
    def checktypes():
        for arttype in arttypes:
            result = xbmc.getInfoLabel(artlabel.format(arttype, ''))
            if result: return True
    foundit = checktypes()
    while not foundit and count < 10:
        xbmc.sleep(200)
        foundit = checktypes()
        count += 1

    if not foundit:
        return []
    result = []
    for arttype in arttypes:
        lastempty = False
        for i in range(0, query.get('limit', 100)):
            inforesult = xbmc.getInfoLabel(artlabel.format(arttype, i if i else ''))
            if inforesult:
                result.append(inforesult)
                lastempty = False
            else:
                if lastempty:
                    break
                lastempty = True
    if _find_extrafanart(source, arttypes, result):
        infopath = xbmc.getInfoLabel(infolabel + ('Path' if source == 'listitem' else 'Folderpath'))
        if not infopath.startswith('plugin://'):
            isepisode = xbmc.getCondVisibility('VideoPlayer.Content(episodes)') if source == 'player' \
                else xbmc.getInfoLabel(infolabel + 'DBTYPE') == 'episode'
            episodefanart = arttypes[0] == 'fanart' and isepisode and \
                xbmc.getCondVisibility('!String.IsEqual({0}Art(tvshow.fanart), {0}Art(fanart))'.format(infolabel))
            if not episodefanart:
                infopath += 'extrafanart' if arttypes[0].endswith('fanart') else 'extrathumbs'
                infopath += '\\' if '\\' in infopath else '/'
                if xbmcvfs.exists(infopath):
                    _, files = xbmcvfs.listdir(infopath)
                    for filename in files:
                        result.append(infopath + filename)

    return result

def _find_extrafanart(source, arttypes, result):
    return source != 'container' and len(result) == 1 and Addon().getSetting('classicmulti') == 'true' \
        and len(arttypes) == 1 and arttypes[0] in ('fanart', 'thumb', 'tvshow.fanart')

def get_smartseries_multiimage(query):
    if not query.get('title') and not query.get('refresh'):
        return []
    elif not query.get('refresh'):
        query['refresh'] = query['title']

    if not query.get('arttype'):
        query['arttype'] = 'fanart'
    elif '.'  in query['arttype']:
        query['arttype'] = query['arttype'].rsplit('.', 1)[1]

    count = 0 # Wait for InfoLabel availability
    while not xbmc.getInfoLabel('ListItem.Label') and count < 10:
        xbmc.sleep(200)
        count += 1

    arttype = 'tvshow.' + query['arttype']
    if not xbmc.getCondVisibility('String.IsEmpty(ListItem.Art({0}))'.format(arttype)):
        query['arttype'] = arttype
        return get_listitem_multiimage(query)
    if not xbmc.getCondVisibility('String.IsEmpty(Container.Art({0}))'.format(arttype)):
        query['arttype'] = arttype
        return get_listitem_multiimage(query, 'container')

    return get_listitem_multiimage(query)
