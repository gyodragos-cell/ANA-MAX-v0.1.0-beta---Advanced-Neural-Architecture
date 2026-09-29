import json, requests

r = requests.post('http://127.0.0.1:8766/mcp', json={'jsonrpc':'2.0','id':1,'method':'tools/list'})
data = r.json()
tools = data.get('result', {}).get('tools', [])

print(f'Total Tools: {len(tools)}')

print('\n=== Continual Learning ===')
cl = [t for t in tools if 'continual' in t.get('name','')]
print(f'Continual Learning Tool: {len(cl)}')
if cl:
    print([t.get('name') for t in cl])

print('\n=== Vision/Telepathy Tools ===')
vt = [t for t in tools if any(n in t.get('name','') for n in ['vision', 'telepathy', 'desktop', 'capture', 'uia'])]
print(f'Vision Tools: {len(vt)}')
print([t.get('name') for t in vt])

print('\n=== System Intelligence Tools ===')
si = [t for t in tools if any(n in t.get('name','') for n in ['dll', 'memory_patching', 'process_security', 'network_protocol'])]
print(f'System Intelligence Tools: {len(si)}')
print([t.get('name') for t in si])
