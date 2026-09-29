import sys
sys.path.insert(0, r"C:\Users\billy\Desktop\ana_dev\ANA_MAX")
from tools.reflex_dispatcher import dispatcher

rule={"id":"smoke_test","remediation":{"enabled":True,"action":"kill_process","dry_run":True}}
data={"pid":999999}

print('Running smoke remediation (dry-run)')
dispatcher._execute_remediation(rule,data)
print('Done')
