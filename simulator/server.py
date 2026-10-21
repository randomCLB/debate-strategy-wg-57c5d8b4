from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit
from pathlib import Path
import json,argparse,uuid
import engine
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,body,kind='application/json; charset=utf-8'):
  data=json.dumps(body,ensure_ascii=False).encode() if kind.startswith('application/json') else body
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(data)
 def allowed(self):
  host=self.headers.get('Host','')
  return host in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}') and self.headers.get('Origin',f'http://{host}')==f'http://{host}'
 def do_GET(self):
  if not self.allowed():return self.send(403,{'error':'仅接受本机同源请求'})
  p=urlsplit(self.path).path
  try:
   if p in ('/','/app.js','/style.css'):
    file=engine.APP/({'/':'index.html'}.get(p,p[1:]));kind='text/html' if p=='/' else 'text/javascript' if p.endswith('js') else 'text/css';return self.send(200,file.read_bytes(),kind+'; charset=utf-8')
   if p=='/api/status':return self.send(200,{'model':'GPT-6 Sol','reasoning':'high','model_runtime':'现有ChatGPT订阅 · 服务端','search':'公开检索 + 正文读取','runtime_available':engine.PYTHON.exists()})
   if p=='/api/debates':
    with engine.connect() as c:rows=[json.loads(r[0]) for r in c.execute('select doc from debates order by rowid desc limit 30')]
    return self.send(200,[{'id':r['id'],'topic':r['input']['topic'],'status':r['status'],'updated':r['updated']} for r in rows])
   if p.startswith('/api/debates/'):return self.send(200,engine.get(p.split('/')[3]))
   return self.send(404,{'error':'页面不存在'})
  except ValueError as e:return self.send(404,{'error':str(e)})
 def do_POST(self):
  if not self.allowed():return self.send(403,{'error':'仅接受本机同源请求'})
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n<2 or n>50000 or 'application/json' not in self.headers.get('Content-Type',''):raise ValueError('需要JSON请求，内容不超过50KB')
   data=json.loads(self.rfile.read(n))
   if not isinstance(data,dict):raise ValueError('参数必须是对象')
   p=urlsplit(self.path).path;key=str(data.get('request_id') or uuid.uuid4().hex)
   if len(key)>100:raise ValueError('请求编号过长')
   if p=='/api/debates':sid=engine.create(data,key);return self.send(202,{'id':sid})
   parts=p.strip('/').split('/')
   if len(parts)==4 and parts[:2]==['api','debates']:
    sid,action=parts[2:]
    if action=='stop':engine.stop(sid)
    else:engine.start_action(sid,action,str(data.get('text','')),key)
    return self.send(202,{'id':sid})
   return self.send(404,{'error':'操作不存在'})
  except (ValueError,KeyError,TypeError) as e:return self.send(400,{'error':str(e)})
  except Exception:return self.send(500,{'error':'服务未完成本次操作，现有记录保留'})
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8876);args=parser.parse_args();engine.init()
 import signal
 def shutdown(signum,frame):
  for sid in list(engine.PROCESSES):engine.stop(sid)
  raise SystemExit(0)
 signal.signal(signal.SIGTERM,shutdown)
 s=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);print(f'辩论模拟器 http://127.0.0.1:{s.server_port}',flush=True);s.serve_forever()
