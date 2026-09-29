import sys
import time
sys.path.insert(0, r'c:\Users\billy\Desktop\ana-manus\ANA_MAX')
from tools.advanced_swarm_tool import AdvancedSwarmTool

tool = AdvancedSwarmTool()
print("Spawning...")
res = tool.execute(action='spawn_subagent', name='test_agent', command='timeout /t 2 /nobreak > nul && echo Done')
print(res)

task_id = res.data['task_id']
time.sleep(1)
print("Status 1:", tool.execute(action='check_status', task_id=task_id))
time.sleep(2)
print("Status 2:", tool.execute(action='check_status', task_id=task_id))
