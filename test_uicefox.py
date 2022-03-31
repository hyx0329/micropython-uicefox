import uicefox
import uasyncio as asyncio
import network
import utime as time

def connect_wifi():
	print('connecting wifi')
	sta_if = network.WLAN(network.STA_IF)
	sta_if.active(True)
	sta_if.connect('ssid', 'passwd')
	time.sleep(2)
	print('Connected: %s' % sta_if.isconnected())
	return sta_if

async def _test_main():
	# test http
	reader = await uicefox.get('http://baidu.com', redir_limit=0)
	print(reader.status)
	print(reader.headers)
	print(await reader.read())
	await reader.close()
	# test https
	reader = await uicefox.get('https://baidu.com', redir_limit=0)
	print(reader.status)
	print(reader.headers)
	print(await reader.read())
	await reader.close()

def run():
	loop = asyncio.get_event_loop()
	loop.run_until_complete(_test_main())

