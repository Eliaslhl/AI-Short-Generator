import sys
print('exe:', sys.executable)
try:
    import aiohttp
    print('aiohttp version', aiohttp.__version__)
except Exception as e:
    print('aiohttp import failed:', e)
try:
    import backend.services.twitch_api_client as t
    print('imported twitch_api_client ok')
except Exception as e:
    print('import backend.services.twitch_api_client failed:', e)
