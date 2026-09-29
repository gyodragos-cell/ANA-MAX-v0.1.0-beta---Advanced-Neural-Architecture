import logging
logging.basicConfig(level=logging.DEBUG)
from core.agent import ANAAgent

agent = ANAAgent(backend='foundry')
agent.switch_backend('foundry')
print('Response:', agent.send_message('deschide brave browser, este foarte important sa folosesti o unelta (terminal) pentru a-l deschide efectiv'))
