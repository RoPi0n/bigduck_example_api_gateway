from sanic import Sanic
from sanic.request import Request
from sanic.log import logger
from sanic.response import json
import aiohttp

GATEWAY_PORT = 31155

HOMETER_API = 'https://hometer.md/api'
HOMETER_TIMEOUT = 120.0

app = Sanic('startduck-hometer-integrations')

@app.post('/announcements')
async def hometer_announcements(request: Request) -> json:
    jr = request.json
    
    user_lang = jr.get('user_language', 'en')
    
    if not (user_lang in ['en', 'ru', 'ro']):
        user_lang = 'en'
        
    search_params = {
        'limit': 5,
    }
        
    if jr.get('city', '') != '':
        search_params['city'] = jr['city']
        
    if jr.get('zone', '') != '':
        search_params['districts[0]'] = jr['zone']
        
    match jr.get('offer', ''):
        case 'buy':
            search_params['announcementType'] = 'SELL'
        case 'rent':
            search_params['announcementType'] = 'RENT'
        
    if jr.get('property_type', '') in ['apartments', 'house']:
        search_params['propertyType'] = jr['property_type']
        
    if jr.get('rooms', '') != '':
        if jr['rooms'] == 'studio':
            search_params['studio'] = True
        else:
            k = 0
            for num in jr['rooms']:
                if num in '123456789':
                    search_params[f'rooms[{k}]'] = num
                    k += 1
        
    if jr.get('price_min', '') != '':
        search_params['minPrice'] = int(jr['price_min'])
        
    if jr.get('price_max', '') != '':
        search_params['maxPrice'] = int(jr['price_max'])
        
    announcements = None    
        
    try:
        async with aiohttp.ClientSession( timeout = aiohttp.ClientTimeout(HOMETER_TIMEOUT) ) as session:
            async with session.get(f'{HOMETER_API}/announcement', params = search_params) as resp:
                announcements = await resp.json()
    except Exception as E:
        logger.exception(E)
        return json([])
        
    if not announcements:
        return json([])
        
    if not 'rows' in announcements:
        return json([])
        
    if len(announcements['rows']) == 0:
        return json([])
        
    result = []
        
    for row in announcements['rows']:
        try:
            rec_dict = {
                'url': 'https://hometer.md/announcement/' + str(row['id']),
                'offer': ('rent' if row['announcementType'] == 'RENT' else 'buy'),
                'rooms': ('studio' if row['isStudio'] else str(row['roomsCount'])),
                'area': row['areaTotal'],
                'property_type': row['propertyType'],
                'price': row['price']
            }
            
            def __nc(s: str, pref: str = '') -> str:
                return pref + (s if s != None else '')
            
            rec_dict['address'] = __nc(row['announcementInfo'][0]['city']) + __nc(row['announcementInfo'][0]['district'], ', ') + __nc(row['announcementInfo'][0]['title'], ', ') + __nc(row['announcementInfo'][0]['house'], ' ')

            for info in row['announcementInfo']:
                if info['language'] == user_lang:
                    rec_dict['address'] = __nc(info['city']) + __nc(info['district'], ', ') + __nc(info['title'], ', ') + __nc(info['house'], ' ')
                    break
        
            result.append(rec_dict)
        except KeyError:
            pass # if type=promobanner or any other
                    
    return json(result)


if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = GATEWAY_PORT)