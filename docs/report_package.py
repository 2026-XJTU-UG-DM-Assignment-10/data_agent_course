"""Create and extract-verify the rules-stage delivery; never claim final LLM acceptance."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
RUN_ID='20261030T070819Z-7779c942'
OUT=ROOT/'outputs/final_delivery'
def sha(data): return hashlib.sha256(data).hexdigest()
def build():
    selected={}
    def add(source,name):
        source=Path(source)
        if not source.is_file():raise FileNotFoundError(source)
        if source.suffix in ('.pyc','.pyo') or source.name.startswith('.env') and source.name!='.env.example':
            raise ValueError('Private/configuration file cannot be packaged')
        data=source.read_bytes()
        if source.suffix.lower() in ('.md','.py','.json','.jsonl','.txt','.mjs','.example'):
            if re.search(rb'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b',data):
                raise ValueError('Possible credential in '+str(source))
        selected[name]=data
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    for name in set(names)-{''}:
        if name.startswith(('.git/','.venv/','outputs/')):continue
        add(ROOT/name,'project/'+name)
    for part in ('raw','reference','dirty','manifests'):
        for file in (ROOT/'data'/part).iterdir():
            if file.name!='.gitkeep' and file.is_file():add(file,'project/data/'+part+'/'+file.name)
    for file in (ROOT/'outputs'/RUN_ID).iterdir():
        if file.is_file():add(file,'project/outputs/'+RUN_ID+'/'+file.name)
    # C's actual offline fault evidence, explicitly separate from model requests.
    for file in (ROOT/'outputs/member_C').rglob('*'):
        if file.is_file() and file.suffix in ('.json','.jsonl','.md','.txt'):
            add(file,'project/'+file.relative_to(ROOT).as_posix())
    for file in (ROOT/'ai_usage').rglob('*'):
        if file.is_file() and file.suffix in ('.md','.json'):add(file,'AI使用记录/'+file.relative_to(ROOT/'ai_usage').as_posix())
    for name in ('summary.json','summary.md'):
        add(ROOT/'outputs/ai_usage'/name,'AI使用记录/'+name)
    evidence_files=[OUT/'browser_check.json',OUT/'rules.json',OUT/'controlled_fault.json',OUT/'llm_not_configured.json',ROOT/'outputs/integration/integration_rules.json',ROOT/'outputs/presentation_build/validation.json',ROOT/'outputs/workflow_qa/latest.json',ROOT/'outputs/manifest_repro/before.json',ROOT/'outputs/manifest_repro/after.json']
    for file in evidence_files:add(file,'本轮验证/'+file.parent.name+'_'+file.name)
    manifest={'status':'rules_stage_only','revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'primary_run_id':RUN_ID,'mode':'rules','missing':['real_llm_success_and_backup','human_cross_machine_reproduction','human_rehearsal','member_names_and_oral_roles'],'files':[{'path':name,'bytes':len(data),'sha256':sha(data)} for name,data in sorted(selected.items())]}
    selected['交付清单.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    selected['请先阅读.txt']=('规则阶段交付，非课程全部验收通过。真实模型未配置；跨机真人复现、全员排练及姓名确认待补。\n进入project目录，按README准备Python环境；本包已含正式数据和一次真实rules成功输出。\n报告和PPT主运行：'+RUN_ID+'\n').encode('utf-8')
    target=OUT/'data_agent_course_rules_stage_20261030.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in selected.items():archive.writestr(name,data)
    extract=OUT/'unpacked_rules_stage'
    extract.mkdir(exist_ok=True)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            dest=(extract/name).resolve();assert dest.is_relative_to(extract.resolve())
        archive.extractall(extract)
    assert all(sha((extract/f['path']).read_bytes())==f['sha256'] for f in manifest['files'])
    from pypdf import PdfReader
    assert len(PdfReader(extract/'project/docs/report.pdf').pages)==6
    with zipfile.ZipFile(extract/'project/docs/presentation.pptx') as archive:
        slides=[n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        assert len(slides)==7
        for name in slides:ET.fromstring(archive.read(name))
    report={'status':'passed','scope':'rules-stage packaging only','file_count':len(selected),'bytes':target.stat().st_size,'zip_sha256':sha(target.read_bytes()),'pdf_pages':6,'slides':7,'all_extracted_hashes_match':True,'missing':manifest['missing'],'native_powerpoint_test':'not_run'}
    (OUT/'package_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
if __name__=='__main__':build()
