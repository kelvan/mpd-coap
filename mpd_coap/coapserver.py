import os
import asyncio
import json
from configparser import ConfigParser

import aiocoap.resource as resource
import aiocoap
import mpd


CONFIGPATH = 'mpd.conf'
config = ConfigParser()


def get_client():
    client = mpd.MPDClient()
    server_conf = config['SERVER']
    client.connect(server_conf['host'], server_conf['port'])
    return client


def load_config():
    if os.path.exists(CONFIGPATH):
        with open(CONFIGPATH) as cfgfile:
            config.read_file(cfgfile)
    else:
        config['SERVER'] = {'host': 'localhost', 'port': 6600}
        with open(CONFIGPATH, 'w') as cfgfile:
            config.write(cfgfile)


class ConfigResource(resource.Resource):
    @asyncio.coroutine
    def render_get(self, request):
        payload = json.dumps(dict(config['SERVER']))
        return aiocoap.Message(
            code=aiocoap.CONTENT, payload=payload.encode('ascii')
        )

    @asyncio.coroutine
    def render_post(self, request):
        new_cfg = json.loads(request.payload.decode('ascii'))
        for key, value in new_cfg.items():
            config['SERVER'][key] = value

        with open(CONFIGPATH, 'w') as f:
            config.write(f)
        return aiocoap.Message(
            code=aiocoap.CONTENT, payload='saved'.encode('ascii')
        )


class CommandResource(resource.Resource):
    @asyncio.coroutine
    def render_post(self, request):
        client = get_client()

        command = request.payload.decode('ascii').strip()
        if hasattr(client, command):
            payload = getattr(client, command)() or ''
            return aiocoap.Message(
                code=aiocoap.CONTENT, payload=payload.encode('UTF-8')
            )

        return aiocoap.Message(
            code=aiocoap.NOT_FOUND,
            payload='Command not found'.encode('ascii')
        )


def main():
    load_config()
    root = resource.Site()
    # add .well-known/core
    wkc = resource.WKCResource(root.get_resources_as_linkheader)
    root.add_resource(('.well-known', 'core'), wkc)
    root.add_resource(('mpd', 'config'), ConfigResource())
    root.add_resource(('mpd', 'command'), CommandResource())

    asyncio.async(aiocoap.Context.create_server_context(root))
    asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    main()
