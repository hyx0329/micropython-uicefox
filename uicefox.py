import uasyncio as asyncio
import uasyncio.core as uasynccore
from uasyncio.stream import Stream
import usocket as socket


USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0"
# USER_AGENT = "curl/7.82.0"


async def open_connection(host, port, ssl=False):
	from uerrno import EINPROGRESS, ENOTCONN
	ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]  # TODO this is blocking!
	s = socket.socket(ai[0], ai[1], ai[2])
	s.setblocking(False)
	try:
		s.connect(ai[-1])
	except OSError as er:
		if er.errno != EINPROGRESS:
			raise er
	if ssl:
		import ussl
		while True:
			try:
				s = ussl.wrap_socket(s)
				break
			except OSError as er:
				if er.errno != ENOTCONN:
					raise er
				await asyncio.sleep_ms(20)
	ss = Stream(s)
	yield uasynccore._io_queue.queue_write(s)
	return ss, ss


class Response:
	status = -1
	headers = None
	content_length = 0

	def __init__(self, reader):
		self._reader = reader
	
	async def read(self, size=None):
		# must limit or ECONNRESET
		if size:
			size = min(self.content_length, size)
		else:
			size = self.content_length
		self.content_length -= size
		return await self._reader.read(size)
	
	async def readline(self):
		return await self._reader.readline()
	
	async def readinto(self, buf):
		await self._reader.readinto(buf)
	
	async def close(self):
		await self._reader.wait_closed()
		# await self._reader.close()
	
	def __repr__(self):
		return "<%s %d %s>" % (self.__name__, self.status, self.headers)


class ChunkedResponse(Response):
	chunk_size = 0

	async def read(self, size=4 * 1024):
		if self.chunk_size == 0:
			l = await self._reader.readline()
			l = l.split(b';', 1)[0]
			self.chunk_size = int(l, 16)
			if self.chunk_size == 0:
				# EOF
				sep = await self._reader.read(2)
				assert sep == b'\r\n'
				return b''
		data = await self._reader.read(min(size, self.chunk_size))
		self.chunk_size -= len(data)
		if self.chunk_size == 0:
			sep = await self._reader.read(2)
			assert sep == b'\r\n'
		return data
	

async def request_raw(method, url, data=None, json=None, headers=None, data_producer=None, data_length=None, ua=None):
	try:
		proto, _, host, path = url.split("/", 3)
	except ValueError:
		proto, _, host = url.split("/", 2)
		path = ""
	if proto == "http:":
		port = 80
	elif proto == "https:":
		port = 443
	else:
		assert False

	if ':' in host:
		host, port = host.split(":", 1)
		port = int(port)
	# NOTE: in uasyncio, reader and writer are the same
	rd, wrt = await open_connection(host, port, proto != "http:")
	query = "%s /%s HTTP/1.1\r\nHost: %s\r\nUser-Agent: %s\r\nAccept: */*\r\nConnection: close\r\n\r\n" % (
		method,path,host,
		ua if ua else USER_AGENT
	)
	buf = memoryview(query.encode('utf-8'))
	wrt.write(buf)
	await wrt.drain()
	if headers:
		for k in headers:
			wrt.write(memoryview(k.encode('utf-8')))
			wrt.write(memoryview(b": "))
			wrt.write(memoryview(headers[k]))
			wrt.write(memoryview(b"\r\n"))
			await s.drain()
	if json:
		assert data is None
		import ujson
		wrt.write(memoryview(b"Content-Type: application/json\r\n"))
		data = ujson.dumps(json).encode('utf-8')
	if data_producer:
		assert data is None
		assert data_length is not None
		raise NotImplementedError()
	if data:
		wrt.write(memoryview(b"Content-Length: %d\r\n" % len(data)))
	wrt.write(b"\r\n")
	await wrt.drain()
	if data:
		wrt.write(data)
		await wrt.drain()
	if data_producer:
		pass
	return rd


async def request(method, url, *args, redir_limit=2, **kwargs):
	redir_cnt = 0
	redir_url = None
	# process headers and redirs
	while True:
		reader = await request_raw(method,url,*args,**kwargs)
		headers = []
		sline = await reader.readline()
		status = int(sline.split(None,2)[1])
		chunked = False
		while True:
			line = await reader.readline()
			if not line or line == b"\r\n": #EOF
				break
			headers.append(line)
			if line.startswith(b"Transfer-Encoding:"):
				if b"chunked" in line:
					chunked = True
			elif line.startswith(b"Location:"):
				url = line.rstrip().split(None,1)[1].decode('utf-8')
			elif line.startswith(b'Content-Length:'):
				content_length = int(
					line.rstrip().split(None,1)[1].decode('utf-8')
				)
		
		if 301 <= status <= 303:
			redir_cnt += 1
			if redir_cnt > redir_limit:
				break # need to preserve last reader
			await reader.wait_closed()
			continue
		break
	if chunked:
		resp = ChunkedResponse(reader)
	else:
		resp = Response(reader)
	resp.status = status
	resp.headers = headers
	resp.content_length = content_length
	return resp
		

def head(url, **kw):
	return request("HEAD", url, **kw)

def get(url, **kw):
	return request("GET", url, **kw)

def post(url, **kw):
	return request("POST", url, **kw)

def put(url, **kw):
	return request("PUT", url, **kw)

def patch(url, **kw):
	return request("PATCH", url, **kw)

def delete(url, **kw):
	return request("DELETE", url, **kw)
