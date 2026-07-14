#!/usr/bin/env node
/** Build the 10-minute PB-ROE presentation with @oai/artifact-tool. */

import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile, image, layers, shape, text } from "@oai/artifact-tool";

const W = 1280;
const H = 720;
const BLACK = "#121212";
const MUTED = "#5F6368";
const LIGHT = "#F2F3F5";
const LINE = "#D7D9DD";
const BLUE = "#2878B5";
const PALE_BLUE = "#EAF5FB";
const RED = "#D65A31";
const FONT = "PingFang SC";

function t(value, left, top, width, height, fontSize = 28, options = {}) {
  return text([value], {
    name: options.name ?? `text-${left}-${top}`,
    position: { left, top },
    width,
    height,
    style: {
      fontSize: `${fontSize}px`,
      typeface: FONT,
      color: options.color ?? BLACK,
      alignment: options.alignment ?? "left",
      verticalAlignment: options.verticalAlignment ?? "top",
      autoFit: options.autoFit ?? "shrinkText",
      insets: options.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
      ...(options.bold ? { bold: true } : {}),
    },
  });
}

function rect(left, top, width, height, fill = LIGHT, radius = "roundRect", line = "none") {
  return shape({
    geometry: radius,
    fill,
    line: line === "none" ? { style: "solid", width: 0, fill: "none" } : { style: "solid", width: 1, fill: line },
    position: { left, top },
    width,
    height,
  });
}

function line(left, top, width, color = LINE, thickness = 2) {
  return shape({
    geometry: "rect",
    fill: color,
    line: { style: "solid", width: 0, fill: "none" },
    position: { left, top },
    width,
    height: thickness,
  });
}

function verticalLine(left, top, height, color = LINE, thickness = 2) {
  return shape({
    geometry: "rect",
    fill: color,
    line: { style: "solid", width: 0, fill: "none" },
    position: { left, top },
    width: thickness,
    height,
  });
}

function pageTitle(title, page, eyebrow = "PB-ROE RESEARCH") {
  return [
    t(eyebrow, 42, 28, 360, 24, 13, { color: BLUE, bold: true }),
    t(title, 42, 62, 1160, 62, 38, { bold: true }),
    t(String(page).padStart(2, "0"), 1180, 666, 58, 20, 13, { alignment: "right", color: MUTED }),
  ];
}

function bullet(value, left, top, width, height = 52, color = BLACK) {
  return [
    shape({ geometry: "ellipse", fill: BLUE, position: { left, top: top + 12 }, width: 9, height: 9 }),
    t(value, left + 24, top, width - 24, height, 22, { color }),
  ];
}

function statCard(left, top, width, stat, label, accent = BLUE) {
  return [
    rect(left, top, width, 170, LIGHT),
    shape({ geometry: "rect", fill: accent, position: { left, top }, width: 8, height: 170 }),
    t(stat, left + 28, top + 27, width - 50, 64, 42, { bold: true, color: accent }),
    t(label, left + 28, top + 102, width - 50, 45, 20, { color: MUTED }),
  ];
}

async function png(file) {
  return new Uint8Array(await fs.readFile(file));
}

function picture(bytes, alt, left, top, width, height) {
  return image({
    blob: bytes,
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left, top },
    width,
    height,
  });
}

function addSlide(presentation, elements) {
  const slide = presentation.slides.add();
  slide.background.fill = "#FFFFFF";
  slide.compose(
    layers({ name: "pb-roe-slide", width: "fill", height: "fill" }, elements),
    { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 1 },
  );
  return slide;
}

async function main() {
  const repo = path.resolve(process.argv[2] ?? process.cwd());
  const output = path.resolve(process.argv[3] ?? path.join(repo, "docs/PB-ROE复现与改进_10min.pptx"));
  const figures = path.join(repo, "docs/results/figures");
  const [paper, factorIc, factorGroups, modelIc, portfolio] = await Promise.all([
    png(path.join(figures, "paper-reproduction-comparison.png")),
    png(path.join(figures, "equal-weight-ic-matplotlib.png")),
    png(path.join(figures, "equal-weight-quantiles-30bp.png")),
    png(path.join(figures, "model-ic-segment-comparison.png")),
    png(path.join(figures, "portfolio-segment-metrics.png")),
  ]);

  const p = Presentation.create({ slideSize: { width: W, height: H } });

  addSlide(p, [
    t("SUMMER RESEARCH · 2026", 42, 42, 500, 28, 15, { color: BLUE, bold: true }),
    t("PB-ROE复现\n与现代改进", 42, 176, 1010, 235, 76, { bold: true, autoFit: "none" }),
    t("从原研报复现，到3因子模型与主动风险组合", 46, 476, 760, 52, 27, { color: MUTED }),
    line(42, 607, 1196, BLACK, 2),
    t("历史沪深300 · Point-in-time · 2015–2022开发 / 2023–2025冻结", 42, 632, 1000, 28, 17, { color: MUTED }),
  ]);

  const stages = [
    ["01", "原文复现", "2005–2011\n回答方向与量级能否重现"],
    ["02", "因子验证", "12个候选\n只在开发期筛选"],
    ["03", "模型比较", "Elastic Net\n对照唯一树模型LightGBM"],
    ["04", "组合优化", "成本、行业、换手\n与主动风险约束"],
  ];
  const stageElements = [...pageTitle("一个问题，四段证据链", 2)];
  stageElements.push(line(84, 334, 1080, BLACK, 2));
  stages.forEach(([num, title, body], i) => {
    const left = 54 + i * 304;
    stageElements.push(shape({ geometry: "ellipse", fill: i === 3 ? BLUE : BLACK, position: { left: left + 24, top: 312 }, width: 45, height: 45 }));
    stageElements.push(t(num, left + 24, 321, 45, 24, 13, { color: "#FFFFFF", alignment: "center", bold: true }));
    stageElements.push(t(title, left, 203, 240, 42, 28, { bold: true }));
    stageElements.push(t(body, left, 390, 245, 108, 21, { color: MUTED }));
  });
  stageElements.push(t("核心判断：复杂度是否带来可验证的样本外增量？", 54, 575, 900, 54, 32, { bold: true, color: BLUE }));
  addSlide(p, stageElements);

  addSlide(p, [
    ...pageTitle("原研报核心方向与收益量级得到复现", 3),
    rect(42, 139, 860, 503, "#FFFFFF", "roundRect", LINE),
    picture(paper, "原研报与本项目成本后年化收益对照", 61, 154, 824, 474),
    ...statCard(936, 165, 302, "35.0%", "原研报 PB-ROE Top50"),
    ...statCard(936, 355, 302, "29.31%", "本项目复现", BLUE),
    t("行业等权最优\n未复现", 956, 555, 250, 60, 23, { bold: true, color: RED }),
  ]);

  addSlide(p, [
    ...pageTitle("数据口径先于模型：避免看见未来", 4),
    ...statCard(42, 162, 356, "300", "每期历史沪深300成分"),
    ...statCard(462, 162, 356, "790", "窗口内成分并集，仅用于历史还原", BLUE),
    ...statCard(882, 162, 356, "48,560", "现代样本可交易截面观测"),
    rect(42, 379, 1196, 215, PALE_BLUE),
    ...bullet("财务值只在公告生效日后可用：effective_date ≤ signal_date", 76, 420, 1110),
    ...bullet("2015–2022用于筛选与训练；2023–2025冻结后才报告", 76, 478, 1110),
    ...bullet("790不是中证800股票池；正式研究从始至终使用历史沪深300", 76, 536, 1110),
  ]);

  addSlide(p, [
    ...pageTitle("12个候选，按同一门槛只留下3个", 5),
    t("筛选门槛", 42, 149, 230, 38, 24, { bold: true, color: BLUE }),
    ...bullet("Rank IC ≥ 2%", 42, 205, 300),
    ...bullet("Newey–West t ≥ 2", 42, 259, 340),
    ...bullet("五分组单调性 ≥ 0.8", 42, 313, 360),
    ...bullet("30bp Top–Bottom为正", 42, 367, 360),
    verticalLine(420, 145, 435, LINE, 1),
    ...statCard(455, 157, 245, "2.89%", "12–1月动量 IC"),
    ...statCard(723, 157, 245, "4.50%", "低特异波动 IC"),
    ...statCard(991, 157, 245, "3.67%", "PB-ROE综合 IC"),
    rect(455, 374, 781, 184, LIGHT),
    t("12 → 3", 486, 400, 236, 67, 47, { bold: true, color: BLUE }),
    t("不是预设选6个，也不是覆盖率合格就入模。\n反转、低Beta、BP等因单调性或成本门槛被淘汰。", 718, 400, 472, 108, 23),
    t("全部筛选只读取开发期", 455, 588, 600, 32, 20, { color: MUTED }),
  ]);

  addSlide(p, [
    ...pageTitle("三因子在开发期同时满足IC与五分组验证", 6),
    rect(42, 139, 590, 494, "#FFFFFF", "roundRect", LINE),
    rect(648, 139, 590, 494, "#FFFFFF", "roundRect", LINE),
    picture(factorIc, "三因子等权得分月度IC和累计IC", 56, 158, 562, 449),
    picture(factorGroups, "三因子五分组收益和累计净值", 662, 158, 562, 449),
    t("开发期：IC 6.19% / t 5.69", 64, 611, 480, 24, 18, { bold: true, color: BLUE }),
    t("开发期：五组严格递增 / 30bp多空 6.94%", 670, 611, 530, 24, 18, { bold: true, color: BLUE }),
  ]);

  addSlide(p, [
    ...pageTitle("线性模型明显优于LightGBM", 7),
    rect(42, 139, 780, 500, "#FFFFFF", "roundRect", LINE),
    picture(modelIc, "Elastic Net和LightGBM分段Rank IC与t值", 60, 157, 744, 461),
    ...statCard(854, 168, 384, "8.12%", "Elastic Net 冻结期IC", BLUE),
    ...statCard(854, 364, 384, "1.73%", "LightGBM 冻结期IC", RED),
    t("只有3个稳定方向因子，复杂树模型没有学到可重复的非线性增量。", 866, 570, 350, 66, 20, { color: MUTED }),
  ]);

  addSlide(p, [
    ...pageTitle("把预测变成可交易的指数增强组合", 8),
    rect(42, 154, 572, 448, PALE_BLUE),
    t("目标函数", 75, 187, 230, 35, 22, { color: BLUE, bold: true }),
    t("预期收益\n− 主动风险\n− 换手惩罚", 75, 250, 455, 205, 45, { bold: true }),
    t("风险项：(w − b)′Σ(w − b)", 75, 518, 470, 35, 23, { color: MUTED }),
    rect(654, 154, 584, 448, LIGHT),
    t("组合约束", 690, 187, 300, 35, 22, { color: BLUE, bold: true }),
    ...bullet("满仓、不可做空", 690, 252, 470),
    ...bullet("单票权重 ≤ 3%", 690, 312, 470),
    ...bullet("行业偏离 ≤ 5%", 690, 372, 470),
    ...bullet("单月换手 ≤ 30%", 690, 432, 470),
    ...bullet("10 / 30 / 50bp成本检验", 690, 492, 470),
    t("138个月全部求解成功 · fallback = 0", 654, 626, 584, 28, 18, { alignment: "right", color: MUTED }),
  ]);

  addSlide(p, [
    ...pageTitle("Elastic Net超过基准，但超额并不稳定", 9),
    rect(42, 139, 780, 500, "#FFFFFF", "roundRect", LINE),
    picture(portfolio, "开发期和冻结期组合年化收益及Sharpe", 61, 157, 742, 460),
    ...statCard(854, 157, 384, "7.24%", "冻结期30bp年化；基准5.62%", BLUE),
    ...statCard(854, 351, 384, "0.32", "冻结期Sharpe；基准0.20", BLUE),
    t("50bp年化 6.49%\n冻结期IR仅0.07\n超额主要来自2023回撤保护", 875, 553, 330, 82, 20, { color: MUTED }),
  ]);

  addSlide(p, [
    t("CONCLUSION", 42, 35, 280, 28, 15, { color: BLUE, bold: true }),
    t("复杂度不是答案，\n可验证性才是。", 42, 105, 760, 155, 55, { bold: true }),
    rect(42, 310, 372, 218, LIGHT),
    rect(454, 310, 372, 218, LIGHT),
    rect(866, 310, 372, 218, LIGHT),
    t("01", 70, 335, 55, 30, 17, { color: BLUE, bold: true }),
    t("PB-ROE历史方向\n与量级可以复现", 70, 382, 304, 90, 27, { bold: true }),
    t("02", 482, 335, 55, 30, 17, { color: BLUE, bold: true }),
    t("12个候选严格筛选后\n只留下3个", 482, 382, 304, 90, 27, { bold: true }),
    t("03", 894, 335, 55, 30, 17, { color: BLUE, bold: true }),
    t("Elastic Net优于树模型\n并带来有限组合增量", 894, 382, 304, 100, 27, { bold: true }),
    line(42, 584, 1196, BLACK, 2),
    t("限制：缺少真实历史指数权重；主动风险版本查看过冻结期，结果是后验稳健性证据。", 42, 613, 1100, 46, 20, { color: MUTED }),
    t("10", 1180, 666, 58, 20, 13, { alignment: "right", color: MUTED }),
  ]);

  await fs.mkdir(path.dirname(output), { recursive: true });
  const pptx = await PresentationFile.exportPptx(p);
  await pptx.save(output);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
