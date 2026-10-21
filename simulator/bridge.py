"""Private server-side adapter. Credentials stay in the existing Hermes store."""
import sys,json,contextlib,sqlite3,time,os
from pathlib import Path
ROOT=Path.home()/'.hermes/hermes-agent'
sys.path.insert(0,str(ROOT))
import hermes_bootstrap

def main(p):
 if p['op']=='search':
  from tools.web_tools import web_search_tool
  return json.loads(web_search_tool(p['query'],limit=4))
 if p['op']=='extract':
  import asyncio
  from tools.web_tools import web_extract_tool
  return json.loads(asyncio.run(web_extract_tool(p['urls'],char_limit=6500)))
 from hermes_cli.plugins import discover_plugins,_delivery_manager
 from hermes_cli.execution_policy import ExecutionPolicyDenied
 discover_plugins()
 from hermes_cli.config import load_config_readonly
 if not load_config_readonly().get('execution_policy',{}).get('enabled'):raise RuntimeError('Model request admission is unavailable')
 def admit(event,**fields):
  if event!='model_request':return
  with sqlite3.connect(p['db'],timeout=20) as c:
   c.execute('BEGIN IMMEDIATE')
   row=c.execute('select doc from debates where id=?',(p['sid'],)).fetchone();d=json.loads(row[0])
   if d['status']!='running' or d['action_id']!=p['action_id']:raise ExecutionPolicyDenied('演练已停止；没有发送新请求',reason='simulation_stopped')
   n=c.execute('select count(*) from requests where action_id=?',(p['action_id'],)).fetchone()[0]
   phase=c.execute('select count(*) from requests where action_id=? and stage=?',(p['action_id'],p['stage'])).fetchone()[0]
   if n>=320 or time.time()-d['action_started']>=7200 or phase>=2:raise ExecutionPolicyDenied('本轮本地执行上限已到，现有记录保留',reason='budget_exhausted')
   c.execute('insert into requests(sid,action_id,stage,model,pid,created) values(?,?,?,?,?,?)',(p['sid'],p['action_id'],p['stage'],fields.get('model'),os.getpid(),time.time()))
  client=fields.get('client')
  if client is not None and hasattr(client,'max_retries'):client.max_retries=0
 _delivery_manager()._middleware.setdefault('execution_policy',[]).append(admit)
 from run_agent import AIAgent
 a=AIAgent(model='gpt-6-sol',provider='openai-codex',api_mode='codex_responses',max_iterations=1,enabled_toolsets=[],skip_memory=True,skip_background_review=True,skip_context_files=True,load_soul_identity=False,quiet_mode=True,session_id='debate-'+p['sid']+'-'+p['stage'],max_tokens=p.get('max_tokens',5000),reasoning_config={'enabled':True,'effort':'high'},cwd=str(Path(__file__).parent),ephemeral_system_prompt=p['system'])
 a._persist_disabled=True
 if a.tools:raise RuntimeError('Unexpected model tools')
 result=a.run_conversation(p['prompt'])
 if result.get('failed') or result.get('local_stop') or not result.get('final_response'):raise RuntimeError('MODEL_RESPONSE_UNAVAILABLE')
 return {'text':result['final_response'],'model':'gpt-6-sol','effort':'high','api_calls':result.get('api_calls'),'usage':{k:result.get(k) for k in ['prompt_tokens','completion_tokens','total_tokens']}}

if __name__=='__main__':
 try:
  payload=json.load(sys.stdin)
  with contextlib.redirect_stdout(sys.stderr):answer=main(payload)
  print(json.dumps({'ok':True,'result':answer},ensure_ascii=False))
 except Exception as exc:
  # HTTP exceptions can embed authentication material. Never expose their text.
  print(json.dumps({'ok':False,'error_type':type(exc).__name__,'error':'服务调用未完成；已有内容已保存。可在本场记录中继续。'},ensure_ascii=False))
  sys.exit(1)
