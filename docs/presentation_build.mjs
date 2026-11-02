import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';

const root=process.cwd();
const version=process.env.MATERIALS_BUILD_ID ?? 'v1';
if(!/^v\d+$/.test(version))throw new Error('Invalid build version');
const out=path.join(root,'outputs/materials_20261102/ppt_build');
const source=path.join(root,'docs/report_assets/presentation_template_rules.pptx');
const skill='C:/Users/zhouj/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const runtime='C:/Users/zhouj/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const data=JSON.parse(await fs.readFile(path.join(root,'outputs/materials_20261102/report_data.json'),'utf8'));
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const inspected=await p.inspect({kind:'slide,textbox,image,table',maxChars:50000});
const records=inspected.ndjson.trim().split(/\r?\n/).map(JSON.parse);
await fs.mkdir(out,{recursive:true});
await fs.writeFile(path.join(out,'source_inspection.ndjson'),inspected.ndjson);
const font='Microsoft YaHei', ink='#19384D', muted='#526978';
function edit(index, top, value, size){
 const rec=records.find(r=>r.kind==='textbox'&&r.slideIndex===index&&Math.abs(r.position.top-top)<1);
 if(!rec)throw new Error(`Missing textbox ${index}/${top}`);
 const shape=p.resolve(rec.id);shape.text=value;
 shape.text.style={...rec.style,...(size?{fontSize:size}:{}),typeface:font};
 return shape;
}
function slide(index){return p.resolve(records.find(r=>r.kind==='slide'&&r.slideIndex===index).id);}
function nativeTable(index,values){
 const rec=records.find(r=>r.kind==='table'&&r.slideIndex===index);
 if(rec.rows!==values.length||rec.cols!==values[0].length)throw new Error('Table dimensions changed');
 const table=p.resolve(rec.id);
 for(let r=0;r<values.length;r++)for(let c=0;c<values[r].length;c++){
  const cell=table.getCell(r,c);cell.value=values[r][c];
  cell.text.style={typeface:font,fontSize:25,color:ink,bold:r===0};
 }
}
edit(0,118,'Adult课程项目 · DeepSeek真实LLM验收通过');
edit(0,205,'真实模型计划与数据自适应');
edit(0,560,'2026-11-02  |  宋艳婷 · 杨陈紫逸 · 胡宇轩 · 周锦晨',26);
slide(0).speakerNotes.text='背景约40秒。四模块已合入main，当前rules与真实LLM集成均通过。主要实测为'+data.run_id+'，DeepSeek官方Chat Completions接口、deepseek-flash。运行和AI账本可核对；本次材料制作未新增API请求。姓名来自组员确认，具体讲述安排待四人确认。';
nativeTable(1,[['阶段','规模','说明'],['原始 adult.data','32,561','保留原件与哈希'],['参考训练','7,000','14特征签名分组'],['固定测试','3,000','不额外注入问题'],['问题训练','7,140','仅在训练侧注入'],['LLM/规则处理后','7,000','仅去重删行']]);
slide(1).speakerNotes.text='数据约50秒。来源：Becker & Kohavi (1996), Adult, UCI, DOI10.24432/C5XW20, CC BY4.0, https://archive.ics.uci.edu/dataset/2/adult。只用adult.data的32561行，完整发布集48842不能混称。参考10000，训练7000/测试3000，训练参考原生重复3行、6997组。先按来源组划分再注入，来源组不交叉，标签和ID不进特征。证据docs/data.md、data/manifests及本次quality报告。';
edit(2,42,'真实模型的决策依据');
edit(2,118,'仅训练统计进入模型；白名单计划由Python工具执行');
nativeTable(2,[['训练字段','实际统计','决策依据'],['capital_gain','偏度 11.4218','中位数0，均值1142.02'],['capital_loss','偏度 4.4913','存在明显右偏'],['fnlwgt','偏度 1.3849','数值列统一采用稳健策略'],['workclass','缺失率 9.89%','保留缺失为独立类别'],['occupation','缺失率 9.47%','避免直接强加众数']]);
edit(2,580,'真实选择：median + Unknown；理由引用了训练统计。');
slide(2).speakerNotes.text='方法约70秒。真实模型原始理由引用capital_gain偏度11.4218、capital_loss4.4913、fnlwgt1.3849；类别理由引用workclass0.0989、occupation0.0947、native_country0.0699缺失率。策略仍是全部数值共享mean/median之一、全部类别共享众数/Unknown之一，不支持逐列混合策略。固定四步本地注入、五字段白名单、最多两次请求，非法计划修正一次，失败明确停止不静默降级。检测A复用B规范化，B只从训练拟合，D分类，C统一pipeline。来源outputs/smoke_runs/'+data.run_id+'/cleaning_plan.json、quality_before.json和events.jsonl。';
edit(3,118,'真实LLM运行的前后统计；四类问题可重叠');
nativeTable(3,data.quality_table);
slide(3).speakerNotes.text='质量结果约60秒。真实LLM运行：7140到7000；缺失5815、重复140、异常70、格式1218到0。首轮去重140，最终0；填补5780=5815-105+70，格式1218=1198+复制20。原生缺失853+注入4857+复制105=5815。测试填补431，保留3000行。上述是不同统计阶段与单位，不相加为问题行数。证据本次quality_before/after、audit_train/test及manifest。';
edit(4,118,'真实LLM运行 '+data.run_id+' · 固定测试3000行',22);
const foot=slide(4).shapes.add({geometry:'textbox',position:{left:64,top:600,width:530,height:50},fill:'none',line:{fill:'none',width:0}});
foot.text='两模式本次策略、成绩相同；未验证提升';foot.text.style={typeface:font,fontSize:22,color:muted};
const matrix=p.resolve(records.find(r=>r.kind==='image'&&r.slideIndex===4).id);
const matrixBytes=await fs.readFile(path.join(root,'docs/report_assets/confusion_matrix_llm.png'));
matrix.replace({blob:matrixBytes.buffer.slice(matrixBytes.byteOffset,matrixBytes.byteOffset+matrixBytes.byteLength),contentType:'image/png',fit:'contain',alt:'实际LLM运行混淆矩阵'});
slide(4).speakerNotes.text='分类约50秒。仅LogisticRegression(random_state=42,max_iter=2000)，训练拟合StandardScaler/OneHotEncoder，测试只转换。Accuracy0.8523333333，Macro-F1 0.7888456818，矩阵行真实列预测[[2101,189],[254,456]]。<=50K2290，>50K710。规则对照'+data.rules_run_id+'同选median/Unknown、同成绩。没有证明模型提升或外部泛化。主请求1262/1723token；累计4次真实请求3404/2869token，费用未知。证据metrics.json与C账本。';
edit(5,42,'四项功能与真实成功运行回放');
edit(5,118,'历史回放：'+data.run_id+'（llm；未发起新请求）',22);
edit(5,210,'上传 · 列级质量',30);
edit(5,315,'训练分布与策略理由\n查看实际填补值',27);
edit(5,470,'成功历史回放\n保留原始ID与模式\n回放不新增模型请求',27);
const screen=p.resolve(records.find(r=>r.kind==='image'&&r.slideIndex===5).id);
const screenBytes=await fs.readFile(path.join(root,'docs/report_assets/page_llm_history.jpg'));
screen.replace({blob:screenBytes.buffer.slice(screenBytes.byteOffset,screenBytes.byteOffset+screenBytes.byteLength),contentType:'image/jpeg',fit:'contain',alt:'已验证LLM历史回放，原始ID与模式可见'});
slide(5).speakerNotes.text='演示约110秒。已配置时选择llm，点击一次创建新运行；当前截图是明确标识的真实LLM成功历史回放，不装作本次新调用。也可预检/上传固定17字段CSV，展示列级缺失率、偏度/四分位数与实际填补值及13导出项。UTF8/BOM、GB18030、常见分隔符兼容；来源交叉/字段/标签错误提前拒绝。回放校验完整日志与相对路径，优先正式规模且标明小样本；预检/回放不调模型。已实际浏览器验证正式本地/双CSV上传rules，LLM页面为历史回放。来源evidence/D/adaptive_features_20261102.json与page_llm_history.jpg；尚未录屏。';
edit(6,118,'姓名已确认；D代完成的增量单列，口头分工待确认');
edit(6,205,'A 宋艳婷：数据与检测    B 杨陈紫逸：规范化与清洗\nC 胡宇轩：原计划、客户端、流程与日志\nD 周锦晨：分类、页面、集成与材料\nD另完成：C增量、真实验证与四项新功能',30);
edit(6,420,'已验证：rules / LLM完整流程、上传、可视化与回放',29);
edit(6,535,'待完成：真人跨机复现、全员排练、演示录屏\n真实请求4次，token已记录；费用未知，保留null',27);
slide(6).speakerNotes.text='总结约40秒，合计建议7分钟，另备3分钟问答；此为建议安排而非排练记录。A宋艳婷，B杨陈紫逸，C胡宇轩，D周锦晨；不推断比例，D代完成A/C增量与本人工作单独记载，B案例文字待确认。当前A60断言/B33断言/C16测试/D新16类拒绝及AppTest通过，rules/真实LLM主门禁通过。真人跨机、全员排练和录屏仍待，不能由AI操作代替。来源docs/contributions.md、docs/acceptance.md、ai_usage及本次报告。';
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(out,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(out,'edited_inspection.ndjson'),(await p.inspect({kind:'slide,textbox,image,table,notes',maxChars:50000})).ndjson);
const candidate=path.join(out,`candidate-${version}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(root,`outputs/materials_20261102/ppt_final_${version}/presentation.pptx`);
await fs.mkdir(path.dirname(finalPath),{recursive:true});
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
 pythonExecutable:path.join(runtime,'python/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[2,3,4],
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','2','--require-native-table-slide','3','--require-native-table-slide','4'],
 fontPolicy:{basis:'reference',families:[font],referencePath:source,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')},
 verifyArtifactToolImport:true,receiptPath:path.join(out,`validation-${version}.json`)});
console.log(JSON.stringify(result));
await fs.copyFile(finalPath,path.join(root,'docs/presentation.pptx'));
