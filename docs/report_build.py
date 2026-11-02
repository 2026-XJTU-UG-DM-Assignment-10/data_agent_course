"""Build the six-page course report from saved production evidence."""
from pathlib import Path
import csv, html, json, shutil
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[1]
DOCS, ASSETS = ROOT/'docs', ROOT/'docs/report_assets'
OUT = ROOT/'outputs/final_release_20261102'
OUT.mkdir(parents=True, exist_ok=True)
RUN_ID, RULES_ID = '20261102T100936Z-a2090032', '20261102T084136Z-d398f7b5'
def locate(run_id):
    paths = [ROOT/'outputs'/run_id, ROOT/'outputs/smoke_runs'/run_id,
        ROOT/'outputs/real_llm_check'/run_id,
        ROOT/'outputs/public_gateway_20261102/downloaded_evidence/data_agent_course/outputs'/run_id,
        ROOT/'outputs/server_reproduction_20261102/downloaded_evidence/data_agent_course/outputs/smoke_runs'/run_id]
    return next(p for p in paths if (p/'run_result.json').is_file())
RUN, RULES = locate(RUN_ID), locate(RULES_ID)
def read(name, folder=RUN):
    return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
metrics, before, after, audit, test_audit, plan = [read(n) for n in
    ('metrics','quality_before','quality_after','audit_train','audit_test','cleaning_plan')]
rules_metrics = read('metrics', RULES)
assert read('run_result')['status']=='succeeded' and plan['categorical_imputation']=='most_frequent'
assert after['row_count']==6998 and metrics['confusion_matrix']==[[2108,182],[261,449]]
shutil.copyfile(RUN/'confusion_matrix.png', ASSETS/'confusion_matrix_current.png')
runtime = [r for r in json.loads((ROOT/'ai_usage/C/usage.json').read_text(encoding='utf-8'))['records'] if r['scope']=='project_runtime']
assert len(runtime)==6 and len({r['source_id'] for r in runtime})==6
primary = next(r for r in runtime if r['source_id']==RUN_ID+':1')
tokens_in, tokens_out = sum(r['input_tokens'] for r in runtime), sum(r['output_tokens'] for r in runtime)
with (ROOT/'data/manifests/injection_manifest.csv').open(encoding='utf-8',newline='') as stream:
    injected=list(csv.DictReader(stream))
with (RUN/'train_processed.csv').open(encoding='utf-8',newline='') as stream:
    cleaned={r['_source_id']:r for r in csv.DictReader(stream)}
case_rows=[]
for kind,label in [('missing','缺失'),('duplicate','重复'),('outlier','异常'),('format','格式')]:
    row=next(r for r in injected if r['problem_type']==kind)
    case_rows.append([label,row['_source_id']+'/'+row['field'],repr(row['new_value']),cleaned[row['_source_id']].get(row['field'],'保留一条关联记录')])
quality_rows=[['检测指标（训练集）','处理前','处理后'],
    ['记录数',str(before['row_count']),str(after['row_count'])],
    ['缺失单元格',str(sum(before['missing_by_column'].values())),str(sum(after['missing_by_column'].values()))],
    ['多余重复行',str(before['duplicate_rows']),str(after['duplicate_rows'])],
    ['范围异常单元格',str(before['outlier_cells']),str(after['outlier_cells'])],
    ['格式问题单元格',str(before['format_issue_cells']),str(after['format_issue_cells'])]]

pages=[
('基于大模型的数据自动清洗与分类智能体',[
 ('subtitle','课程项目报告 · 正式交付版 · 2026-11-02'),
 ('p','成员：宋艳婷（A）、杨陈紫逸（B）、胡宇轩（C）、周锦晨（D）。本项目面向固定Adult表格，构建从CSV输入、质量检测、训练摘要决策到工具清洗、分类评估和网页导出的完整流程。规则与真实DeepSeek流程已通过验证，并在独立云服务器运行。'),
 ('h','项目目标与达成结果'),
 ('table',[['目标','达成结果'],
  ['规范数据输入','支持固定17字段CSV上传、编码与分隔符兼容，预检字段、标签及来源隔离后再执行。'],
  ['依据训练分布制定计划','汇总缺失率、偏度、四分位数和IQR，让模型在白名单中选择填补策略并说明依据。'],
  ['清洗与评估可核查','处理四类质量问题，展示逐列质量和实际填补值，导出审计、分类指标及混淆矩阵。'],
  ['结果可展示、可复用','网页执行与完整历史回放共用生产流程，保留原始ID和模式，支持下载与公网HTTPS演示。']]),
 ('h','当前实测结果'),
 ('p','主运行'+RUN_ID+'（llm）：7,140条脏训练处理后保留6,998条，固定测试3,000条。模型选择median与most_frequent，四类训练质量问题归零。Accuracy为85.23%，Macro-F1为0.787282。'),
 ('p','规则对照'+RULES_ID+'：训练保留7,000条，Accuracy同为85.23%，Macro-F1为0.788846。两种模式采用不同类别填补策略，结果分别记录。'),
 ('p','工程验证已覆盖独立环境安装、正式数据重建、真实模型调用、后台服务重启与公网认证访问。课堂入口：https://111.230.149.166/，独立演示口令由展示者私下提供。')]),
('数据来源、构造与质量检测',[
 ('p','数据来自UCI Adult，许可CC BY 4.0。[1] 完整发布集为48,842行，本项目使用adult.data的32,561行，以seed=42抽取10,000条参考记录。参考数据保留原生缺失，不作为完整真值。'),
 ('table',[['阶段','记录数','处理与用途'],['原始adult.data','32,561','保留原件、来源与SHA-256'],['参考训练/测试','7,000 / 3,000','按14特征签名分组后划分'],['注入后训练','7,140','仅训练侧注入，复制保留来源'],['本次LLM处理后','6,998 / 3,000','训练去重，测试保持全部行']]),
 ('p','同一_group_id不跨训练和测试。income、_source_id、_group_id不作为特征。训练参考含3行原生完全重复，7,000行对应6,997个来源组。'),
 ('table',quality_rows),
 ('p','缺失检测5,815格由原生853格、注入4,857格和复制带入105格组成；格式问题1,218格包含注入1,198格和复制带入20格。四类计数可重叠，不相加作为问题总行数。manifest仅用于离线审计。'),
 ('p','本次执行先去重140行，非法置空70格，填补5,780格，填补后再去重2行。测试填补431格，保留3,000行的标签、来源ID与顺序。原始文件SHA-256：5b00264637dbfec36bdeaab5676b0b309ff9eb788d63554ca0a249491c86603d。')]),
('训练摘要决策与工具清洗',[
 ('table',[['环节','实现方式'],['统计摘要','共用规范化视图，统计逐列缺失率及合法数值分布，保持原始输入不变。'],['模型决策','只向模型提供训练摘要，选择数值/类别填补策略并返回理由。'],['本地校验','五个白名单决策字段，固定步骤由本地设置，最多两次请求，无效计划明确失败。'],['执行与测试转换','训练侧去重、非法置空、拟合填补状态并复查重复，测试仅应用训练状态。']]),
 ('p','本次模型选择median：capital_gain偏度11.4218，均值1,142.0185而中位数为0；capital_loss偏度4.4913，fnlwgt偏度1.3849。数值摘要还提供四分位数和IQR，当前全部数值列共享一种策略。'),
 ('p','类别选择most_frequent：模型引用workclass缺失率9.89%、occupation为9.47%、native_country为6.99%，认为缺失比例适中，选择观测众数。规则模式固定使用Unknown。两种选择均受白名单约束，不把模型理由作为最优性的证明。'),
 ('h','处理后CSV中的四类案例'),
 ('table',[['类型','来源与字段','实际输入','处理后'],*case_rows]),
 ('p','案例逐项对照注入清单与本次输出CSV核对。合法数值摘要排除缺失、解析失败和越界值，少于3个观测时偏度为空。模型不读取测试摘要、测试指标或注入真值，也不执行生成代码。')]),
('网页处理与结果追溯',[
 ('p','网页与CLI调用同一生产pipeline。界面依次组织输入校验、模型策略、清洗质量、实际训练状态与分类结果，列级图表和历史结果用于解释、检查与复用这条完整流程。'),
 ('table',[['使用环节','页面行为'],['输入与预检','选择正式数据或上传同结构CSV，支持UTF-8/BOM、GB18030与常见分隔符。'],['执行与解释','选择rules或llm，点击开始处理创建运行，展示训练分布、策略理由、列级质量及填补值。'],['评估与导出','展示Accuracy、Macro-F1及矩阵，提供13项审计、数据、日志与图像下载。'],['历史复用','校验成功目录、完整文件和路径，保留原始run_id与模式，回放不新增模型请求。']]),
 ('image',('public_gateway_20261102/page_service_metrics.jpg',470,264)),
 ('caption','图1 服务器后台服务中真实LLM运行的分类结果，显示85.23% Accuracy、78.73% Macro-F1及实际矩阵。'),
 ('p','应用预检每份文件限制20MB，固定14特征、标签与两个来源字段共17列。重复表头、缺/多字段、坏行、非法标签、来源交叉和训练数值列无合法观测均在模型请求前拒绝。'),
 ('p','仅点击开始处理创建新运行，预检、重绘和回放不新增请求。小样本可用于功能自测，页面明确标注训练不足5,000行，不冒充正式规模。')]),
('分类评估与实际调用记录',[
 ('p','分类使用14个特征：6个数值字段经StandardScaler处理，8个类别字段经OneHotEncoder(handle_unknown="ignore")处理，再训练LogisticRegression(random_state=42,max_iter=2000)。填补、编码和标准化均只从训练集拟合。'),
 ('table',[['模式与训练规模','数值/类别策略','Accuracy / Macro-F1'],['rules，7,000行','median / Unknown','85.23% / 0.788846'],['真实llm，6,998行','median / most_frequent','85.23% / 0.787282']]),
 ('image',('confusion_matrix_current.png',320,256)),
 ('caption','图2 本次真实LLM混淆矩阵，行是真实类别，列是预测类别。'),
 ('p','测试3,000行，<=50K为2,290行，>50K为710行；矩阵为[[2108,182],[261,449]]。Macro-F1为两个标签F1的等权平均。本次模型方案的Macro-F1略低于规则对照，不能据此宣称性能提升或跨数据集泛化。'),
 ('p',f'主运行实际请求1次，输入{primary["input_tokens"]:,}、输出{primary["output_tokens"]:,} token。项目累计{len(runtime)}次真实模型请求，输入{tokens_in:,}、输出{tokens_out:,} token。temperature=0为实际参数，费用未知，保留unknown/null。'),
 ('small','模型请求与开发辅助分账。开发内部调用/token、未核实模型或参数和费用保留null，不按零计算；受控测试不计为真实服务调用。下表模型名称沿用各人账本，完整记录见包内AI使用记录目录。'),
 ('table_compact',[['成员','模型及可获知参数','提示词位置','已知次数 / 费用'],['A','未核实；参数未知','ai_usage/A/prompts/','开发未知 / 未知'],['B','GPT-6；参数未知','ai_usage/B/prompts/','开发未知 / 未知'],['C','开发GPT-6；运行deepseek-flash，temperature=0','ai_usage/C/prompts/','运行6次；开发未知 / 未知'],['D','未核实；参数未知','ai_usage/D/prompts/','开发未知 / 未知']])]),
('工程验证、成员工作与交付',[
 ('table',[['成员','完成的主要工作'],['A 宋艳婷','正式数据准备、来源记录、分组划分、问题注入与质量检测。'],['B 杨陈紫逸','共享格式规范化、训练清洗、测试转换与清洗审计。'],['C 胡宇轩','模型客户端、计划生成、总流程与运行日志。'],['D 周锦晨','分类器、网页与CLI、输入预检与历史回放、训练摘要增强、模型边界校验、端到端集成、服务器部署和交付材料。']]),
 ('h','已完成的验证'),
 ('p','共享契约1.0保持冻结。A60项断言、B33项断言、C16项测试及D输入拒绝、来源隔离、真实流程、历史回放和AppTest已通过，rules与真实LLM完整集成通过。独立Windows Server 2022/Python3.12.10完成环境安装与正式数据重建。'),
 ('p','公网HTTPS配置独立演示认证，后端仅监听回环。两项Windows服务重启通过，关闭SSH后14项公网认证/TLS/WSS检查和实际PNG下载仍通过；模型配置用Windows DPAPI加密并限制ACL。[2]'),
 ('h','复现与交付'),
 ('p','交付包包含PDF/Markdown报告、可编辑PPT、完整源码与Git历史包、依赖版本、正式数据和清单、真实运行与验收证据、四人AI账本及汇总，以及PPT制作和课堂展示指南。按包内说明安装依赖、准备数据并运行CLI、网页或集成检查，不含登录口令、API key和证书私钥。'),
 ('h','使用范围与剩余事项'),
 ('p','系统限定Adult结构与全局填补策略，尚未评价复杂语义冲突、公平性和外部泛化。课堂网络、手机实机、整机重启、原生PowerPoint打开、排练和录屏仍需实际确认。'),
 ('small','[1] Becker, B. & Kohavi, R. (1996). Adult [Dataset]. UCI Machine Learning Repository. DOI:10.24432/C5XW20，https://archive.ics.uci.edu/dataset/2/adult，CC BY 4.0。'),
 ('small','[2] 本仓库源码、evidence/D/public_gateway_20261102.json、server_reproduction_20261102.json及C业务账本。主运行'+RUN_ID+'；规则对照'+RULES_ID+'。')])]

pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simhei.ttf'))
style=ParagraphStyle('body',fontName='CN',fontSize=10.1,leading=16.8,spaceAfter=9,wordWrap='CJK',textColor=colors.HexColor('#223447'))
heading=ParagraphStyle('heading',parent=style,fontSize=12.6,leading=20,spaceBefore=10,spaceAfter=8,textColor=colors.HexColor('#123D5A'))
title=ParagraphStyle('title',parent=style,fontSize=20,leading=29,spaceAfter=15,textColor=colors.HexColor('#123D5A'))
small=ParagraphStyle('small',parent=style,fontSize=8.5,leading=13,spaceAfter=7)
cell=ParagraphStyle('cell',parent=style,fontSize=9.1,leading=14.2,spaceAfter=0)
def paragraph(text,text_style=style):return Paragraph(html.escape(str(text)),text_style)
story=[]
markdown=['# 基于大模型的数据自动清洗与分类智能体\n\n课程项目报告 · 正式交付版 · 2026-11-02\n']
for index,(name,blocks) in enumerate(pages):
    if index:story.append(PageBreak());markdown.append('\n<!-- pagebreak -->\n')
    story.append(paragraph(name,title));markdown.append('## '+name+'\n')
    for kind,value in blocks:
        if kind in ('table','table_compact'):
            columns=len(value[0]);widths=[92,383] if columns==2 else [122,133,220] if columns==3 else [40,177,135,123]
            cs = ParagraphStyle('compact',parent=cell,fontSize=8.4,leading=12) if kind=='table_compact' else cell
            pad=3 if kind=='table_compact' else 6
            table=Table([[paragraph(c,cs) for c in row] for row in value],colWidths=widths,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E5EFF4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#7893A4')),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#7893A4')),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad)]))
            story.extend([table,Spacer(1,11)])
            markdown.append('| '+' | '.join(value[0])+' |\n| '+' | '.join(['---']*columns)+' |\n'+'\n'.join('| '+' | '.join(str(c).replace('|','/') for c in row)+' |' for row in value[1:])+'\n')
        elif kind=='image':
            file,width,height=value;story.extend([Image(str(ASSETS/file),width=width,height=height),Spacer(1,7)])
            markdown.append('!['+file+'](report_assets/'+file+')\n')
        else:
            story.append(paragraph(value,heading if kind=='h' else small if kind in ('small','caption','subtitle') else style))
            markdown.append(('### ' if kind=='h' else '')+value+'\n')
def footer(canvas,document):
    canvas.setFont('CN',8);canvas.setFillColor(colors.HexColor('#667E8C'))
    canvas.drawString(54,28,'Adult 数据处理智能体  /  课程项目报告  /  2026-11-02')
    canvas.drawRightString(A4[0]-54,28,str(document.page))
SimpleDocTemplate(str(DOCS/'report.pdf'),pagesize=A4,rightMargin=54,leftMargin=54,topMargin=46,bottomMargin=48,title='数据处理智能体课程项目报告',author='宋艳婷；杨陈紫逸；胡宇轩；周锦晨').build(story,onFirstPage=footer,onLaterPages=footer)
(DOCS/'report.md').write_text('\n'.join(markdown),encoding='utf-8')
(OUT/'report_data.json').write_text(json.dumps({'run_id':RUN_ID,'run_folder':RUN.relative_to(ROOT).as_posix(),'rules_run_id':RULES_ID,'rules_folder':RULES.relative_to(ROOT).as_posix(),'metrics':metrics,'rules_metrics':rules_metrics,'quality_table':quality_rows,'case_table':case_rows,'plan':plan,'matrix_asset':'confusion_matrix_current.png','page_asset':'public_gateway_20261102/page_service_metrics.jpg','runtime_requests':len(runtime),'input_tokens':tokens_in,'output_tokens':tokens_out,'primary_input_tokens':primary['input_tokens'],'primary_output_tokens':primary['output_tokens']},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Created report.md/report.pdf from actual run '+RUN_ID)
