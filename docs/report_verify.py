"""Persist a clearly controlled invalid-plan test against C's real agent."""
from pathlib import Path
import json
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.agent import get_cleaning_plan
from src.schema import LLMReply, PlanValidationError, QualityReport

class InvalidPlanDouble:
    def __init__(self):self.calls=0
    def generate_plan(self,summary,*,feedback=None):
        self.calls+=1
        return LLMReply(text='{"numeric_imputation":"knn"}',provider='CONTROLLED_TEST',model='TEST_DOUBLE_INVALID_PLAN',parameters={})

def main():
    run='20261030T070819Z-7779c942'
    report=QualityReport.model_validate_json((ROOT/'outputs'/run/'quality_before.json').read_text(encoding='utf-8'))
    double=InvalidPlanDouble();events=[];rejected=False
    try:
        get_cleaning_plan(report,mode='llm',llm_client=double,event_sink=lambda name,data:events.append({'name':name,'data':data}))
    except PlanValidationError:
        rejected=True
    assert rejected and double.calls==2
    result={'status':'passed','is_controlled_test':True,'uses_test_doubles':True,'real_llm_checked':False,'checked_at':datetime.now(timezone.utc).isoformat(),'input_report_from_rules_run':run,'fake_client_calls':double.calls,'invalid_plan_rejected':rejected,'events':events,'claim_boundary':'Real C agent rejected a deliberately invalid test-double plan after two attempts. No external model request or runtime accounting entry.'}
    target=ROOT/'outputs/final_delivery/controlled_fault.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('status','is_controlled_test','real_llm_checked','fake_client_calls','invalid_plan_rejected')}))
if __name__=='__main__':main()
