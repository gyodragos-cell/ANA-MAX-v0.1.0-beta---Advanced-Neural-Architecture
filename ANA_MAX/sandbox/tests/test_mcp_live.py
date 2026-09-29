import sys, json, subprocess

mcp_path = r'C:\Users\billy\Desktop\ana-manus\mcp\os27_mcp_server.py'
python_exe = r'C:\Users\billy\Desktop\ana-manus\ANA_MAX\venv\Scripts\python.exe'

def send_request(method, params=None):
    req = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params:
        req['params'] = params
    
    p = subprocess.Popen([python_exe, mcp_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    out, err = p.communicate(json.dumps(req) + '\n')
    
    try:
        for line in out.splitlines():
            if line.startswith('{'):
                return json.loads(line)
        return {'error': 'No JSON found', 'raw_out': out, 'raw_err': err}
    except Exception as e:
        return {'error': str(e), 'raw_out': out, 'raw_err': err}

print('--- TEST 1: os27_dashboard_feeder_snapshot ---')
res1 = send_request('tools/call', {'name': 'os27_dashboard_feeder_snapshot', 'arguments': {}})
if 'result' in res1 and not res1['result'].get('isError'):
    content = res1['result']['content'][0]['text']
    data = json.loads(content)
    print('Dashboard Status: SUCCESS')
    print('Total Tools in Registry:', len(data.get('dashboard', {})))
    broken = data.get('broken_tools', [])
    print('Broken Tools:', len(broken))
    if broken:
        print(' - Broken tools list:', broken)
else:
    print('Dashboard Error:', res1)

print('\n--- TEST 2: os27_tool_brain_smoke_test (ContextEngineTool) ---')
res2 = send_request('tools/call', {'name': 'os27_tool_brain_smoke_test', 'arguments': {'tool_name': 'ContextEngineTool'}})
if 'result' in res2 and not res2['result'].get('isError'):
    content = res2['result']['content'][0]['text']
    print('Smoke Test Status: SUCCESS')
    print('Result:', content)
else:
    print('Smoke Test Error:', res2)

print('\n--- TEST 3: SystemIntegrityCheckTool (AI Core Scan) ---')
res3 = send_request('tools/call', {'name': 'os27_system_integrity_hyper_scan', 'arguments': {}})
if 'result' in res3 and not res3['result'].get('isError'):
    content = res3['result']['content'][0]['text']
    print('System Integrity Scan: SUCCESS')
    # Limit print length so it doesn't flood the output
    print('Preview:', content[:300], '...')
else:
    print('System Integrity Scan Error:', res3)
