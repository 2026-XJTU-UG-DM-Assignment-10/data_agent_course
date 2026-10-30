import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root=process.cwd(), out=path.join(root,'outputs/presentation_build');
const skill='C:/Users/zhouj/.codex/plugins/cache/openai-primary-runtime/presentations/26.1025.11240/skills/presentations';
const runtime='C:/Users/zhouj/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const data=JSON.parse(await fs.readFile(path.join(root,'outputs/final_delivery/report_data.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1280,height:720}});
const font='Microsoft YaHei', ink='#19384D', muted='#526978', accent='#137C84';
await fs.mkdir(out,{recursive:true});
function text(slide, value, x,y,w,h,size=28,color=ink,bold=false){
  const s=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  s.text=value;s.text.style={typeface:font,fontSize:size,color,bold};return s;
}
function base(title, note){
  const s=p.slides.add();s.background.fill='#F7FAFB';
  text(s,title,64,42,1152,70,44,ink,true);
  if(note)text(s,note,64,118,1152,45,23,muted);
  text(s,`${p.slides.items.length} / 7`,1150,670,80,28,18,muted);
  return s;
}
function table(s, values,x,y,w,h,widths){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,values,columnWidths:widths});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?'#E1EEF1':'#F7FAFB';
    cell.text.style={typeface:font,fontSize:25,color:ink,bold:r===0};
  }
  t.borders.assign({fill:'#B8CAD4',width:1,style:'solid'});return t;
}
async function picture(s,name,x,y,w,h){
  const bytes=await fs.readFile(path.join(root,'docs/report_assets',name));
  s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',alt:name,fit:'contain',position:{left:x,top:y,width:w,height:h}});
}
let s=base('数据自动清洗与分类智能体','Adult 课程项目');
text(s,'规则流程与真实数据验证',64,205,1130,90,60,ink,true);
text(s,'7,140 行脏训练数据，处理后保留 7,000 行',64,330,1100,60,32);
text(s,'3,000 行固定测试集，Accuracy 85.23%',64,405,1100,60,32,accent,true);
text(s,'2026-10-30 · 真实模型尚未配置',64,560,1100,50,26,muted);
s.speakerNotes.text='背景1分钟。当前四人初版已合入main，展示数据来自真实rules运行。真实大模型没有配置，不声称模型验收通过。姓名和讲述分工待成员确认。主证据 outputs/'+data.run_id+'/。';
s=base('数据来源与分组划分','固定抽样 10,000 条参考记录，先分组划分再注入问题');
table(s,[['阶段','规模','说明'],['原始 adult.data','32,561','保留原件与哈希'],['参考训练','7,000','14特征签名分组'],['固定测试','3,000','不额外注入问题'],['问题训练','7,140','复制保留来源关联'],['处理后训练','7,000','仅去重删行']],64,194,1152,354,[340,220,592]);
text(s,'参考数据仍可含原生缺失。两个来源 ID 与 income 不作为特征。',64,580,1150,70,27,muted);
s.speakerNotes.text='数据与流程合计1分钟。官方完整Adult为48,842条，本项目仅使用adult.data的32,561条。UCI Adult, Becker & Kohavi (1996), DOI10.24432/C5XW20, CC BY4.0, https://archive.ics.uci.edu/dataset/2/adult。本次data/manifests/preparation_summary.json及正式运行输出。';
s=base('计划与工具的职责边界','规则模式固定策略；模型模式的实际调用仍待配置');
table(s,[['职责','实现','输入与限制'],['检测','A profiler','B的共享规范化视图'],['计划与校验','C agent','仅训练摘要，白名单策略，最多两次请求'],['训练清洗','B cleaner','先去重，仅训练拟合填补，再去重'],['测试转换','B cleaner','只应用训练状态，不删测试行'],['分类与展示','D classifier / UI','14特征，训练拟合编码与标准化']],64,194,1152,354,[220,330,602]);
text(s,'本次选择 median 与 Unknown，理由来自 rules 入口。',64,580,1150,65,28,accent,true);
s.speakerNotes.text='现场演示前说明：实际大模型可以选择mean/median与most_frequent/constant的白名单组合，代码设置mode与步骤并校验。当前理由是规则文本，不是模型自主决策。来源 src/agent.py、src/cleaner.py、src/contracts.py；实际清洗计划 outputs/'+data.run_id+'/cleaning_plan.json。';
s=base('四类质量问题的处理结果','本次正式规则运行，问题可重叠，不能相加当作问题总行数');
table(s,data.quality_table,64,190,1152,354,[650,251,251]);
text(s,'首轮去重 140 行，最终去重 0 行，训练填补 5,780 格',64,580,1150,42,28,accent,true);
text(s,'测试填补 431 格，行数、标签、来源 ID 与顺序保持',64,630,1150,40,25,muted);
s.speakerNotes.text='结果部分。缺失检测5815在去重前，填补5780在去重和非法置空之后，两种统计阶段不同。注入缺失4857、格式1198、异常70行、复制140行为构造审计。不能把构造数、检测数、执行修改数混为一谈。来源本次quality_before/after.json、audit_train/test.json。';
s=base('固定测试集的分类评估','LogisticRegression，StandardScaler 与 OneHotEncoder 只在训练集拟合');
text(s,'85.23%',64,245,520,95,82,accent,true);
text(s,'Accuracy',64,353,500,45,31,muted);
text(s,'0.788846',64,440,500,90,58,ink,true);
text(s,'Macro-F1',64,537,500,50,31,muted);
await picture(s,'confusion_matrix_rules.png',635,185,580,464);
s.speakerNotes.text='结果展示1分钟。测试3000行，<=50K2290、>50K710，矩阵行真实列预测[[2101,189],[254,456]]。Macro-F1等权平均两个标签的F1。没有清洗前提升对照，不声称提升，也没有用测试集调整模型。来源 outputs/'+data.run_id+'/metrics.json 和confusion_matrix.png。';
s=base('实际页面与文件下载','rules 运行 ID '+data.run_id);
await picture(s,'page_results_rules.png',64,195,790,444);
text(s,'13 个导出入口',900,210,310,70,31,accent,true);
text(s,'已下载 CSV、日志、摘要\n与本次输出逐字节一致',900,315,310,110,27);
text(s,'选择器切换不新增运行\n旧结果仍明确标为 rules',900,470,310,110,27,muted);
s.speakerNotes.text='现场演示2分钟：选择正式演示数据，明确rules，开始处理一次，展示质量、策略、指标和下载。真实模型演示需补验后再替换模式。截图为本机人工浏览器检查，不是合成预览。来源 docs/report_assets/page_results_rules.png，outputs/final_delivery/browser_check.json。';
s=base('当前交付与尚缺验收','四人初版已经合入 main，姓名和口头分工待成员确认');
text(s,'A 数据与检测    B 规范化与清洗\nC 计划、客户端、流程与日志\nD 分类、页面、集成与材料',64,205,1150,175,34);
text(s,'当前可核实：正式 rules 流程、人工页面、下载与阶段材料',64,420,1140,72,29,accent,true);
text(s,'待补：真实模型成功链条、另一位成员跨机复现、全员排练\n未知模型用量和费用保留 null，不记作 0 元',64,535,1140,105,27,muted);
s.speakerNotes.text='总结分工1分钟，另备3分钟问答。A原数据说明为集成人补齐待A确认，B正式案例本轮由D从日志提取待B复核。真实模型备份/录屏须在真实成功后制作。本机检出或自动测试不能替代真人跨机与排练。来源docs/contributions.md、docs/acceptance.md、AI账本和summary.json。';
for (const [i,slide] of p.slides.items.entries()){
  const png=await p.export({slide,format:'png',scale:1});
  await fs.writeFile(path.join(out,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(out,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:path.join(root,'docs/presentation.pptx'),
 pythonExecutable:path.join(runtime,'python/python.exe'),
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[2,3,4],
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',
             '--require-native-table-slide','2','--require-native-table-slide','3','--require-native-table-slide','4'],
 fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(out,'validation.json')});
console.log(JSON.stringify(result));
