import sys, os
# Merge in directorul ANA_MAX indiferent de unde rulezi scriptul
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
from tools.tool_factory import ToolFactoryTool

factory = ToolFactoryTool()
res = factory.execute(
    capability='Citeste toate fisierele .log din Desktop si returneaza o lista cu numele lor si dimensiunea',
    tool_name='desktop_log_reader',
    category='file',
    params='[{"name": "max_files", "desc": "Numarul maxim de fisiere de returnat", "required": false}]'
)
print('STATUS:', res.status)
print('MESSAGE:', res.message)
if res.data:
    print('TOOL_ID:', res.data.get('tool_id'))
    print('FILE:', res.data.get('file'))
    print('REGISTERED LIVE:', res.data.get('registered_live'))
else:
    print('ERROR:', res.error)
