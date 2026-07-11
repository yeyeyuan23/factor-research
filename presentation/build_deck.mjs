import fs from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "/private/tmp/pb_roe_ppt/output";
const W = 1280, H = 720;
const C = {
  ink: "#101828", muted: "#667085", faint: "#98A2B3", line: "#D0D5DD",
  paper: "#FCFCFD", panel: "#F2F4F7", blue: "#175CD3", cyan: "#2E90FA",
  navy: "#0B1F3A", orange: "#F79009", red: "#D92D20", green: "#039855",
  greenBg: "#ECFDF3", blueBg: "#EFF8FF", orangeBg: "#FFFAEB", redBg: "#FEF3F2",
  white: "#FFFFFF"
};
const FONT = "PingFang SC";

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

function box(slide, x, y, w, h, fill = "none", line = "none", radius = false) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1.2 },
    ...(radius ? { borderRadius: "rounded-xl" } : {})
  });
}

function txt(slide, text, x, y, w, h, size = 24, color = C.ink, opts = {}) {
  const s = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  s.text = text;
  s.text.style = {
    fontSize: size,
    typeface: FONT,
    color,
    bold: !!opts.bold,
    alignment: opts.align || "left",
    verticalAlignment: opts.valign || "top",
    autoFit: opts.autoFit || "shrinkText",
    ...(opts.italic ? { italic: true } : {}),
  };
  return s;
}

function line(slide, x1, y1, x2, y2, color = C.line, width = 1.5) {
  return slide.shapes.add({
    geometry: "straightConnector1",
    position: { left: x1, top: y1, width: x2 - x1, height: y2 - y1 },
    fill: "none",
    line: { style: "solid", fill: color, width }
  });
}

function circle(slide, x, y, d, fill, label, labelColor = C.white, fontSize = 18) {
  slide.shapes.add({ geometry: "ellipse", position: { left: x, top: y, width: d, height: d }, fill,
    line: { style: "solid", fill, width: 0 } });
  txt(slide, label, x, y + 1, d, d - 2, fontSize, labelColor, { bold: true, align: "center", valign: "middle" });
}

function base(p, num, section) {
  const s = p.slides.add();
  s.background.fill = C.paper;
  txt(s, section.toUpperCase(), 42, 28, 360, 24, 13, C.blue, { bold: true });
  txt(s, String(num).padStart(2, "0"), 1190, 666, 44, 20, 12, C.faint, { align: "right" });
  line(s, 42, 650, 1238, 650, C.line, 1);
  return s;
}

function title(s, text, sub = "") {
  txt(s, text, 42, 67, 1160, 58, 38, C.ink, { bold: true });
  if (sub) txt(s, sub, 42, 128, 1120, 32, 18, C.muted);
}

function note(s, arr) {
  s.speakerNotes.textFrame.setText(arr);
  s.speakerNotes.setVisible(true);
}

const p = Presentation.create({ slideSize: { width: W, height: H } });

// 1 — Cover, adapted from Codex Grid slide 01.
{
  const s = p.slides.add(); s.background.fill = C.paper;
  box(s, 0, 0, 18, H, C.blue);
  txt(s, "SUMMER RESEARCH PROJECT · 2026", 54, 48, 520, 24, 14, C.blue, { bold: true });
  txt(s, "PB–ROE\n还有效吗？", 54, 180, 790, 210, 64, C.ink, { bold: true });
  txt(s, "从 2011 年策略复现，到严格时点一致的现代检验", 58, 432, 700, 48, 25, C.muted);
  line(s, 58, 518, 1140, 518, C.line, 1.5);
  txt(s, "历史成分股  ·  公告日 PIT  ·  Walk-forward  ·  组合约束", 58, 548, 900, 35, 18, C.ink, { bold: true });
  txt(s, "10 分钟答辩版", 1010, 606, 170, 32, 16, C.blue, { bold: true, align: "right" });
  circle(s, 1035, 170, 120, C.navy, "PB", C.white, 32);
  circle(s, 1095, 255, 120, C.cyan, "ROE", C.white, 25);
  note(s, [
    "开场：这不是一个简单的‘价值因子还能不能赚钱’问题。",
    "我的问题是：把 2011 年 PB–ROE 策略放进今天更严格的时点一致框架后，结论还能保留多少？",
    "全程围绕三件事：原文复现、偏差修复、现代化比较。"
  ]);
}

// 2 — Original paper result and tension.
{
  const s = base(p, 2, "01 · 原文结论");
  title(s, "原文报告了 40%+ 年化，但真正的问题不是“照抄公式”", "同一篇论文还发现：单独低 PB 并不呈现稳定单调性");
  box(s, 42, 188, 690, 410, C.white, C.line, true);
  s.charts.add("bar", {
    position: { left: 78, top: 220, width: 620, height: 330 },
    categories: ["沪深300", "PB–ROE50", "行业等权 PB–ROE"],
    series: [{ name: "年化收益率（原文）", values: [23.84, 40.33, 41.85], fill: C.cyan }],
    hasLegend: false,
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.0%" },
    chartFill: C.white, chartLine: { style: "solid", width: 0, fill: C.white },
    plotAreaFill: { type: "none" }, plotAreaLine: { style: "solid", width: 0, fill: C.white },
    xAxis: { visible: true, deleted: false, textStyle: { typeface: FONT, fontSize: "14px", color: C.ink }, line: { style: "solid", width: 1, fill: C.line } },
    yAxis: { visible: true, deleted: false, min: 0, max: 50, majorUnit: 10,
      textStyle: { typeface: FONT, fontSize: "12px", color: C.muted },
      majorGridlines: { style: "solid", width: 1, fill: "#EAECF0" }, line: { style: "solid", width: 0, fill: C.white } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 75 }
  });
  txt(s, "论文给出的吸引力", 784, 207, 390, 32, 22, C.muted, { bold: true });
  txt(s, "639%", 784, 246, 350, 92, 58, C.blue, { bold: true });
  txt(s, "PB–ROE50 累计收益（2005–2011）", 784, 334, 390, 50, 18, C.ink);
  box(s, 784, 410, 402, 120, C.orangeBg, "#FEC84B", true);
  txt(s, "复现张力", 808, 430, 140, 26, 17, C.orange, { bold: true });
  txt(s, "高收益来自因子本身，还是来自样本与时点定义？", 808, 466, 350, 45, 23, C.ink, { bold: true });
  txt(s, "来源：华泰联合证券《数量化选股策略之三：PB-ROE策略》（2011）。百分比为原文报告，不是本项目实证结果。", 42, 612, 1120, 22, 11, C.faint);
  note(s, [
    "原文中，PB–ROE50 年化 40.33%，行业等权版本 41.85%，都明显高于沪深300。",
    "但论文同时指出，单独低 PB 分组不是越低越好。这提示 PB 与 ROE 的交互可能比单因子更重要。",
    "因此项目目标不是复制一个漂亮数字，而是判断这个数字在更严格定义下是否仍成立。"
  ]);
}

// 3 — Exact reproduction protocol.
{
  const s = base(p, 3, "02 · 复现对象");
  title(s, "先把“原策略”锁死：规则、日期和成本都可追溯", "纸面规则层与改进层完全分离，避免边跑边改口径");
  const xs = [70, 355, 640, 925];
  const heads = ["股票池", "信号", "调仓", "持有与成本"];
  const bodies = [
    "历史时点沪深300\n不是今天的成分股",
    "score = pct(ROE)\n+ 1 − pct(PB)",
    "4/30 · 8/31 · 10/31\n非交易日向前取",
    "等权 Top 10/20/50\n首期 0.6%，换仓 1.3%"
  ];
  line(s, 120, 320, 1065, 320, C.line, 3);
  for (let i=0;i<4;i++) {
    circle(s, xs[i]+80, 292, 56, i===1 ? C.cyan : C.navy, String(i+1), C.white, 20);
    txt(s, heads[i], xs[i], 205, 216, 35, 20, C.blue, { bold: true, align: "center" });
    txt(s, bodies[i], xs[i], 375, 216, 95, 20, C.ink, { bold: true, align: "center", valign: "middle" });
  }
  box(s, 182, 520, 916, 72, C.blueBg, "#B2DDFF", true);
  txt(s, "复现成功 ≠ 收益数字完全相同；成功首先意味着输入、排序、成交和成本口径都能被审计。", 212, 537, 856, 40, 22, C.navy, { bold: true, align: "center", valign: "middle" });
  note(s, [
    "这一页说明我具体复现什么。",
    "股票池必须是历史时点的沪深300；信号是 ROE 分位加一减 PB 分位；一年三次调仓；持仓等权并计入原文成本。",
    "关键是把规则冻结。否则只要结果不好，就不断改日期或口径，复现就失去可证伪性。"
  ]);
}

// 4 — Bias map.
{
  const s = base(p, 4, "03 · 关键偏差");
  title(s, "四类偏差足以把一个普通因子“做成”高收益", "这些不是实现细节，而是研究结论的一部分");
  const cards = [
    [42, 190, "01", "幸存者偏差", "用当前成分股回看历史，会提前知道谁最终留在指数。", C.redBg, C.red],
    [650, 190, "02", "公告日泄露", "按报告期而不是公告日取 ROE，会在市场看到前使用财务数据。", C.orangeBg, C.orange],
    [42, 405, "03", "成交假设", "收盘生成信号又用同一收盘成交，可能引入不可执行收益。", C.blueBg, C.blue],
    [650, 405, "04", "行业暴露", "低 PB + 高 ROE 可能集中于少数行业，收益并非纯选股。", C.greenBg, C.green]
  ];
  for (const [x,y,n,h,b,bg,accent] of cards) {
    box(s, x, y, 566, 170, bg, accent, true);
    circle(s, x+24, y+22, 48, accent, n, C.white, 15);
    txt(s, h, x+92, y+24, 430, 34, 23, C.ink, { bold: true });
    txt(s, b, x+92, y+73, 430, 70, 18, C.muted);
  }
  note(s, [
    "我把主要风险归纳成四类。",
    "其中最严重的是历史成分股和公告日：前者决定你当时是否真的能选这只股票，后者决定你当时是否真的知道这个 ROE。",
    "成交和行业暴露会继续影响收益归因，所以后面的现代检验必须显式处理。"
  ]);
}

// 5 — Dual track design.
{
  const s = base(p, 5, "04 · 研究设计");
  title(s, "双轨设计：分别回答“能否复现”与“今天是否仍有效”");
  box(s, 42, 184, 560, 410, C.white, C.line, true);
  box(s, 636, 184, 602, 410, C.navy, C.navy, true);
  txt(s, "A · PAPER TRACK", 72, 216, 240, 24, 14, C.blue, { bold: true });
  txt(s, "纸面复现", 72, 258, 360, 48, 34, C.ink, { bold: true });
  txt(s, "一年 3 次调仓\n原文 Top-N 与成本\n尽量保持原始规则", 72, 330, 430, 130, 22, C.muted);
  box(s, 72, 500, 458, 58, C.panel, C.line, true);
  txt(s, "回答：原报告的结论有多可复现？", 92, 515, 418, 30, 18, C.ink, { bold: true });
  txt(s, "B · MODERN TRACK", 670, 216, 260, 24, 14, "#84CAFF", { bold: true });
  txt(s, "现代检验", 670, 258, 360, 48, 34, C.white, { bold: true });
  txt(s, "月度 Walk-forward\n严格公告日 PIT\n成本、换手与行业约束", 670, 330, 480, 130, 22, "#D1E9FF");
  box(s, 670, 500, 500, 58, "#173B67", "#2E90FA", true);
  txt(s, "回答：因子在可执行条件下是否仍有效？", 690, 515, 460, 30, 18, C.white, { bold: true });
  note(s, [
    "项目采用双轨制。左边只做忠实复现，不把现代方法偷偷混进去。",
    "右边才是改进：月度 walk-forward、严格公告日 PIT、统一成本和风险约束。",
    "这样，即使两个轨道给出不同结论，也能解释差异来自哪里。"
  ]);
}

// 6 — Data audit.
{
  const s = base(p, 6, "05 · 数据审计");
  title(s, "真实数据先暴露了一个边界：免费源无法完整覆盖原文起点", "当前结论来自 5 股真实链路抽样，只证明可得性与管线，不代表策略收益");
  txt(s, "ROE 公告日可得性抽样", 42, 190, 400, 30, 20, C.ink, { bold: true });
  const years = ["2005", "2006", "2007", "2008", "2009", "2010"];
  const vals = [0,0,100,100,100,100];
  for (let i=0;i<years.length;i++) {
    const x=55+i*112;
    box(s, x, 472-2.2*vals[i], 66, 2.2*vals[i], vals[i] ? C.cyan : C.line, "none", true);
    txt(s, vals[i]+"%", x-8, 434-2.2*vals[i], 82, 26, 16, vals[i]?C.blue:C.faint, { bold:true, align:"center" });
    txt(s, years[i], x-8, 490, 82, 24, 15, C.muted, { align:"center" });
  }
  line(s, 42, 472, 715, 472, C.line, 1.5);
  box(s, 768, 190, 470, 126, C.redBg, "#FDA29B", true);
  txt(s, "原文窗口", 792, 210, 140, 24, 15, C.red, { bold:true });
  txt(s, "2005–2011", 792, 242, 380, 46, 32, C.ink, { bold:true });
  txt(s, "2005 历史成分股为空；2006 抽样 ROE 公告日缺失", 792, 286, 410, 24, 15, C.muted);
  box(s, 768, 338, 470, 154, C.greenBg, "#6CE9A6", true);
  txt(s, "严格免费数据窗口", 792, 360, 220, 24, 15, C.green, { bold:true });
  txt(s, "2007–2011", 792, 395, 380, 46, 32, C.ink, { bold:true });
  txt(s, "12 个信号期；PB/ROE 抽样覆盖率 100%", 792, 445, 410, 26, 17, C.muted);
  box(s, 768, 515, 470, 62, C.blueBg, "#84CAFF", true);
  txt(s, "决策：不填补、不回看；把数据边界写进结论。", 790, 531, 426, 32, 18, C.navy, { bold:true, align:"center" });
  txt(s, "来源：BaoStock 真实数据链路抽样及项目审计日志（2026-07-12）。", 42, 612, 900, 20, 11, C.faint);
  note(s, [
    "真实下载后，数据本身先给出了边界。",
    "免费数据源在 2005 年没有返回历史沪深300成分；5股抽样中，2006 年 ROE 公告日也缺失；从 2007 年开始抽样覆盖完整。",
    "所以免费数据严格复现窗口改为 2007–2011。这里不做插值，更不会用后来值回填。"
  ]);
}

// 7 — Evaluation framework.
{
  const s = base(p, 7, "06 · 评价框架");
  title(s, "不再用一条净值曲线裁决因子：证据分成四层", "所有模型共享同一套 walk-forward 与成本口径");
  const data = [
    ["1", "预测性", "Rank IC · ICIR\nNewey–West t 值", C.blueBg, C.blue],
    ["2", "单调性", "分位数组合\n多空价差", C.greenBg, C.green],
    ["3", "可交易性", "换手率 · 成本后收益\n容量代理", C.orangeBg, C.orange],
    ["4", "风险归因", "行业暴露 · 市值暴露\n回撤与稳定性", C.redBg, C.red]
  ];
  for (let i=0;i<4;i++) {
    const row=Math.floor(i/2), col=i%2, x=42+col*608, y=186+row*208;
    const [n,h,b,bg,ac]=data[i];
    box(s,x,y,566,170,bg,ac,true); circle(s,x+26,y+26,52,ac,n,C.white,18);
    txt(s,h,x+100,y+27,380,34,23,C.ink,{bold:true});
    txt(s,b,x+100,y+78,410,66,19,C.muted);
  }
  box(s, 350, 595, 580, 38, C.navy, C.navy, true);
  txt(s, "一个结论至少要同时通过：统计显著 + 经济显著 + 可执行", 365, 602, 550, 24, 16, C.white, { bold:true, align:"center" });
  note(s, [
    "现代评价不是只看累计收益。",
    "第一层看横截面预测力；第二层看分组是否单调；第三层看换手和成本；第四层看收益是否只是行业或市值暴露。",
    "只有统计、经济和可执行三类证据同时支持，才把它称为有效因子。"
  ]);
}

// 8 — Model comparison.
{
  const s = base(p, 8, "07 · 模型设计");
  title(s, "模型不是越多越好：一个线性基准 + 一个树模型足够回答问题", "LightGBM 是唯一树模型；不再重复加入功能相近的第二棵树");
  const xs=[42,436,830];
  const names=["等权打分", "ElasticNet", "LightGBM"];
  const roles=["复现基线", "线性可解释基线", "非线性交互检验"];
  const desc=["PB 与 ROE 等权\n验证原始经济直觉", "自动收缩冗余因子\n系数方向可解释", "捕捉阈值与交互\n例如低 PB × 高 ROE"];
  const colors=[C.muted,C.blue,C.orange];
  for(let i=0;i<3;i++){
    box(s,xs[i],205,350,315,C.white,C.line,true);
    txt(s,"0"+(i+1),xs[i]+24,230,50,28,15,colors[i],{bold:true});
    txt(s,names[i],xs[i]+24,274,300,46,30,C.ink,{bold:true});
    txt(s,roles[i],xs[i]+24,329,300,28,17,colors[i],{bold:true});
    line(s,xs[i]+24,376,xs[i]+326,376,C.line,1);
    txt(s,desc[i],xs[i]+24,402,302,75,19,C.muted);
  }
  line(s,392,365,426,365,C.line,2); line(s,786,365,820,365,C.line,2);
  box(s, 214, 553, 852, 56, C.panel, C.line, true);
  txt(s, "公平比较：相同特征时点 · 相同训练窗口 · 相同预测月份 · 相同成本与组合约束", 236, 568, 808, 28, 18, C.ink, { bold:true, align:"center" });
  note(s, [
    "模型部分刻意保持克制。",
    "先用原始等权分数，再用 ElasticNet 检验线性可解释关系，最后只保留一个树模型 LightGBM 检验非线性和交互。",
    "不需要两个功能相近的树模型。公平性来自共享同一训练窗口、预测月份和交易成本。"
  ]);
}

// 9 — Portfolio and engineering verification.
{
  const s = base(p, 9, "08 · 从信号到组合");
  title(s, "信号必须穿过组合约束，才可能成为可交易策略");
  const stages=[
    [70,"预测收益","等权 / EN / LGBM"],
    [335,"风险估计","Ledoit–Wolf 协方差"],
    [600,"约束优化","多头 · 个股上限 · 换手"],
    [865,"审计输出","持仓 · 收益 · 诊断"]
  ];
  line(s,130,315,1040,315,C.line,4);
  stages.forEach((d,i)=>{
    circle(s,d[0]+70,282,66,i===2?C.cyan:C.navy,String(i+1),C.white,21);
    txt(s,d[1],d[0],205,206,34,20,C.ink,{bold:true,align:"center"});
    txt(s,d[2],d[0],377,206,52,17,C.muted,{align:"center"});
  });
  box(s, 42, 478, 1196, 108, C.greenBg, "#6CE9A6", true);
  txt(s, "工程验证（非研究结论）", 70, 500, 280, 26, 16, C.green, { bold:true });
  txt(s, "43", 70, 530, 90, 40, 31, C.ink, { bold:true });
  txt(s, "项测试通过", 160, 540, 150, 24, 16, C.muted);
  txt(s, "10", 400, 530, 90, 40, 31, C.ink, { bold:true });
  txt(s, "项最终审计通过", 490, 540, 180, 24, 16, C.muted);
  txt(s, "0", 790, 530, 90, 40, 31, C.ink, { bold:true });
  txt(s, "次模型时序泄露", 870, 540, 200, 24, 16, C.muted);
  txt(s, "注：数字来自 fixture smoke 与代码测试，只说明管线约束有效。", 42, 612, 900, 20, 11, C.faint);
  note(s, [
    "因子分数之后还有风险和交易约束。",
    "项目用 Ledoit–Wolf 估计协方差，再用 CVXPY 施加多头、个股上限和换手约束；不可行时有可审计的回退。",
    "当前 43 项测试和 10 项最终审计都通过，但这些是工程验证，不是策略表现。"
  ]);
}

// 10 — Conclusion.
{
  const s = p.slides.add(); s.background.fill = C.navy;
  txt(s, "TAKEAWAY", 52, 44, 260, 24, 14, "#84CAFF", { bold:true });
  txt(s, "可信的复现，\n先于漂亮的收益。", 52, 150, 780, 170, 54, C.white, { bold:true });
  txt(s, "01", 56, 378, 45, 28, 17, "#84CAFF", { bold:true });
  txt(s, "原文策略值得检验，但 40%+ 年化只能作为待验证主张。", 114, 372, 970, 46, 23, C.white, { bold:true });
  txt(s, "02", 56, 448, 45, 28, 17, "#84CAFF", { bold:true });
  txt(s, "历史成分股与公告日 PIT 是结论可信度的第一道门。", 114, 442, 970, 46, 23, C.white, { bold:true });
  txt(s, "03", 56, 518, 45, 28, 17, "#84CAFF", { bold:true });
  txt(s, "模型只保留 ElasticNet + LightGBM；改进重点是公平比较与可交易性。", 114, 512, 1030, 48, 23, C.white, { bold:true });
  box(s, 890, 132, 320, 166, "#173B67", "#2E90FA", true);
  txt(s, "下一步交付", 918, 154, 250, 24, 15, "#84CAFF", { bold:true });
  txt(s, "全样本下载\n→ 严格复现\n→ 样本外比较", 918, 192, 240, 86, 22, C.white, { bold:true });
  txt(s, "谢谢", 1080, 640, 120, 30, 18, "#84CAFF", { bold:true, align:"right" });
  note(s, [
    "最后总结三点。",
    "第一，原文高收益是待验证主张；第二，PIT 和历史股票池比多堆模型更重要；第三，模型只保留一个线性和一个树模型，重点是统一口径。",
    "下一步完成全样本下载后，我会冻结数据版本，输出严格复现、现代评价和样本外比较。"
  ]);
}

await fs.mkdir(OUT, { recursive: true });
for (const [i, s] of p.slides.items.entries()) {
  const stem = `slide-${String(i+1).padStart(2,"0")}`;
  await writeBlob(`${OUT}/${stem}.png`, await p.export({ slide:s, format:"png", scale:1 }));
  const layout = await s.export({ format:"layout" });
  await fs.writeFile(`${OUT}/${stem}.layout.json`, await layout.text());
}
await writeBlob(`${OUT}/deck-montage.webp`, await p.export({ format:"webp", montage:true, scale:1 }));
const pptx = await PresentationFile.exportPptx(p);
await pptx.save(`${OUT}/PB_ROE_夏令营答辩_10分钟版.pptx`);
