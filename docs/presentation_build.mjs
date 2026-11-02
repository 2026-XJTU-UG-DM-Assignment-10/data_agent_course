import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';

const root=process.cwd();
const version=process.env.MATERIALS_BUILD_ID ?? 'v1';
if(!/^v\d+$/.test(version))throw new Error('Invalid build version');
const out=path.join(root,'outputs/final_release_20261102/ppt_build');
const source=path.join(root,'docs/report_assets/presentation_template_rules.pptx');
const skill='C:/Users/zhouj/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const runtime='C:/Users/zhouj/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const data=JSON.parse(await fs.readFile(path.join(root,'outputs/final_release_20261102/report_data.json'),'utf8'));
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
edit(0,118,'Adult课程项目  规则与真实DeepSeek流程已验证');
edit(0,205,'训练摘要驱动的清洗决策');
edit(0,330,'7,140 行脏训练数据，处理后保留 6,998 行');
edit(0,405,'3,000 行固定测试集，Accuracy 85.23%');
edit(0,560,'2026-11-02  宋艳婷、杨陈紫逸、胡宇轩、周锦晨',26);
slide(0).speakerNotes.text='35秒。项目面向固定Adult表格，把规范输入、训练摘要决策、工具清洗、分类评估与结果复用组织为完整流程。输入校验、列质量、训练分布解释和历史回放均服务于这些目标。当前主运行'+data.run_id+'来自服务器新服务中的实际LLM点击，处理6998条训练、固定测试3000条。来源docs/report.md与该次run_result.json。';
nativeTable(1,[['阶段','规模','说明'],['原始 adult.data','32,561','保留原件与哈希'],['参考训练','7,000','14特征签名分组'],['固定测试','3,000','不额外注入问题'],['问题训练','7,140','仅在训练侧注入'],['LLM / rules处理后','6,998 / 7,000','LLM填补后再去重2行']]);
slide(1).speakerNotes.text='45秒。来源Becker & Kohavi (1996), Adult, UCI, DOI10.24432/C5XW20, CC BY4.0, https://archive.ics.uci.edu/dataset/2/adult。只用adult.data的32561行，固定seed42抽10000，训练7000/测试3000。训练参考原生重复3行、6997来源组。先来源组划分再注入，标签和来源ID不进特征。测试不删行、不重新拟合。来源data/manifests与docs/data.md。';
edit(2,42,'训练摘要与模型决策');
edit(2,118,'合法训练摘要进入模型，工具执行白名单计划');
nativeTable(2,[['训练字段','实际统计','决策依据'],['capital_gain','偏度 11.4218','中位数0，均值1142.02'],['capital_loss','偏度 4.4913','存在明显右偏'],['fnlwgt','偏度 1.3849','数值列共享稳健填补策略'],['workclass','缺失率 9.89%','本次模型选择观测众数'],['occupation','缺失率 9.47%','类别列共享most_frequent']]);
edit(2,580,'本次策略：median + most_frequent');
slide(2).speakerNotes.text='60秒。训练摘要提供逐列缺失率、合法数值偏度、四分位数和IQR。主运行实际理由引用capital_gain偏度11.4218、capital_loss4.4913、fnlwgt1.3849；类别理由引用workclass约9.89%、occupation约9.47%和native_country约6.99%，选择median与most_frequent。六个数值列共用一种策略，八个类别列共用一种策略。五个决策字段受白名单校验，固定四步本地设置，最多两次请求，无效计划明确失败。测试摘要、指标和注入真值不提供给模型。来源outputs/'+data.run_id+'/cleaning_plan.json、quality_before.json与events.jsonl。';
edit(3,118,'训练侧清洗结果，固定测试集保持3,000行');
nativeTable(3,data.quality_table);
edit(3,580,'首轮去重140行，填补后再去重2行，填补5,780格',29);
edit(3,630,'列级质量与训练填补值可在网页逐项查看',27);
slide(3).speakerNotes.text='50秒。主运行7140到6998，缺失5815、重复140、异常70、格式1218处理后均0。首轮去重140，填补后再去重2；填补5780=5815-105+70。原生缺失853、注入4857、复制带入105共5815格。测试填补431并保留全部3000行。质量问题可重叠，检测计数与执行审计口径分开。质量计数为0不表示语义全部正确。来源该次quality_before/after和audit_train/test。';
edit(4,118,'真实LLM运行 '+data.run_id+'，固定测试3,000行',22);
edit(4,440,'0.787282');
const foot=slide(4).shapes.add({geometry:'textbox',position:{left:64,top:600,width:540,height:60},fill:'none',line:{fill:'none',width:0}});
foot.text='规则对照 Macro-F1 0.788846\n本次未证明模型带来性能提升';
foot.text.style={typeface:font,fontSize:20,color:muted};
const matrix=p.resolve(records.find(r=>r.kind==='image'&&r.slideIndex===4).id);
const matrixBytes=await fs.readFile(path.join(root,'docs/report_assets',data.matrix_asset));
matrix.replace({blob:matrixBytes.buffer.slice(matrixBytes.byteOffset,matrixBytes.byteOffset+matrixBytes.byteLength),contentType:'image/png',fit:'contain',alt:'主运行实际混淆矩阵'});
slide(4).speakerNotes.text='55秒。仅使用LogisticRegression(random_state42,max_iter2000)，编码和标准化只从训练拟合。主运行Accuracy0.8523333333、Macro-F1 0.7872823666，矩阵行真实列预测[[2108,182],[261,449]]。类别<=50K2290、>50K710。规则对照'+data.rules_run_id+'为median/Unknown，训练7000，Accuracy相同、Macro-F1 0.7888456818。不能宣称模型提升或外部泛化。主请求1262/1365token，累计6次真实模型请求5928/5652token，费用未知。来源metrics.json和ai_usage/C/usage.json。';
edit(5,42,'网页处理与结果追溯');
edit(5,118,'公网课堂入口 https://111.230.149.166/',24);
edit(5,210,'预检与新运行',30);
edit(5,315,'查看策略与填补值\n核对列级质量和指标',26);
edit(5,470,'下载CSV与日志\n按原始ID回放结果',26);
const screen=p.resolve(records.find(r=>r.kind==='image'&&r.slideIndex===5).id);
const screenBytes=await fs.readFile(path.join(root,'docs/report_assets',data.page_asset));
screen.replace({blob:screenBytes.buffer.slice(screenBytes.byteOffset,screenBytes.byteOffset+screenBytes.byteLength),contentType:'image/jpeg',fit:'contain',alt:'服务器新服务中的真实LLM分类结果'});
slide(5).speakerNotes.text='120秒网页演示。课前用独立演示账号登录HTTPS网站，密码不放PPT或录屏。使用已准备的正式数据，先预检，再选llm，点击一次开始处理。等待时说明训练摘要、白名单和工具边界。结果出来展示原始run_id、列级质量、训练填补值、模型理由和分类矩阵，下载CSV或events。也可展示固定17字段CSV上传，保留来源字段。预检显示模型请求未调用只指预检阶段，实际请求看本次运行日志与C账本。网络故障时明确使用先前成功历史回放并展示原始时间/模式，不称现场新请求。当前截图来自'+data.run_id+'的真实处理。详细步骤、备用方案与问答见docs/presentation_guide.md。';
edit(6,42,'项目成果与成员工作');
edit(6,118,'系统已完成独立服务器验证并提供公网演示入口');
edit(6,205,'A 宋艳婷：数据准备、来源划分与质量检测\nB 杨陈紫逸：格式规范化、清洗与测试转换\nC 胡宇轩：模型客户端、计划生成、流程与日志\nD 周锦晨：分类与页面、训练摘要与输入校验、集成部署及材料',27);
edit(6,420,'验证：规则与真实LLM完整流程、独立服务器与公网访问',27);
edit(6,535,'交付：报告、源码、数据、日志、AI记录及课堂指南\n课前完成教室网络登录与排练',26);
slide(6).speakerNotes.text='55秒，合计建议7分钟。按实际完成工作介绍四位成员。D还完成历史回放、模型边界校验与逐次记账验证，完整工作见docs/contributions.md。技术验证包括A60断言/B33断言/C16测试/D真实流程与输入边界检查，独立WindowsServer2022/Python3.12.10安装及正式数据重建。公网认证/TLS/WSS14项、服务重启及关闭SSH后的访问通过。系统仍限定Adult结构和全局填补策略，课堂网络与实际排练以真实操作为准。来源docs/report.md、public_gateway_20261102.md及evidence/D。';
for(const [i,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(out,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(out,'edited_inspection.ndjson'),(await p.inspect({kind:'slide,textbox,image,table,notes',maxChars:50000})).ndjson);
const candidate=path.join(out,`candidate-${version}.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(root,`outputs/final_release_20261102/ppt_final_${version}/presentation.pptx`);
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
