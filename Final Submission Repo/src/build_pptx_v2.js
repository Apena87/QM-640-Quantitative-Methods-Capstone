// QM 640 Interim Presentation, 15-minute deck
// Author: Angel Pena
// Build: node build_pptx.js

const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const DL_CANDIDATES = [
  process.env.DL,
  "/sessions/practical-trusting-feynman/mnt/Downloads",
  "/mnt/c/Users/kraam/Downloads",
  "C:/Users/kraam/Downloads",
];
const DL = DL_CANDIDATES.find(p => p && fs.existsSync(p));
const FS_DIR = path.join(DL, "Final Submission");
const FIG = path.join(FS_DIR, "figures");
const OUT = path.join(FS_DIR, "presentation", "QM640_Interim_Presentation_v2.pptx");
fs.mkdirSync(path.dirname(OUT), { recursive: true });
console.log("Using Downloads:", DL);

// Color palette, Midnight Executive
const NAVY   = "1E2761";
const ICE    = "CADCFC";
const WHITE  = "FFFFFF";
const ACCENT = "C00000";   // red for callouts
const GOLD   = "F0B429";   // accent secondary
const GRAY   = "5A6478";
const LIGHT  = "F4F6FB";

const HEADER_FONT = "Georgia";
const BODY_FONT   = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";  // 13.3 x 7.5
pres.author = "Angel Pena";
pres.title  = "QM 640 Capstone Interim Presentation";

const W = 13.3, H = 7.5;

// ── Master: title bar + footer ──────────────────────────────────────────────
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    // top accent rule
    { rect: { x: 0, y: 0, w: W, h: 0.18, fill: { color: NAVY } } },
    // footer text
    { text: {
      text: "Angel Pena  |  QM 640 Capstone  |  Medicare Part D Analysis  |  Walsh College",
      options: { x: 0.5, y: H - 0.4, w: W - 1, h: 0.3, fontSize: 9, fontFace: BODY_FONT,
                 color: GRAY, align: "left" }
    } },
  ],
  slideNumber: { x: W - 0.6, y: H - 0.4, w: 0.4, h: 0.3,
                 fontSize: 9, fontFace: BODY_FONT, color: GRAY, align: "right" },
});

pres.defineSlideMaster({
  title: "SECTION",
  background: { color: NAVY },
});

// ── Helpers ─────────────────────────────────────────────────────────────────
function slideTitle(slide, text) {
  slide.addText(text, {
    x: 0.5, y: 0.35, w: W - 1, h: 0.7,
    fontSize: 28, fontFace: HEADER_FONT, color: NAVY, bold: true,
    margin: 0, valign: "middle",
  });
}

function divider(slide, y) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: y, w: 0.6, h: 0.04,
    fill: { color: GOLD }, line: { type: "none" },
  });
}

function bulletList(slide, items, opts) {
  const arr = items.map((t, i) => ({
    text: t,
    options: { bullet: { code: "25A0" }, breakLine: i < items.length - 1, color: NAVY,
               paraSpaceAfter: 6 },
  }));
  slide.addText(arr, opts);
}

function statCard(slide, x, y, w, h, value, label, color = NAVY, valueColor = ACCENT) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { color: LIGHT }, line: { type: "none" },
    shadow: { type: "outer", color: "000000", blur: 8, offset: 2, angle: 90, opacity: 0.10 },
  });
  // left accent bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.08, h, fill: { color }, line: { type: "none" },
  });
  slide.addText(value, {
    x: x + 0.2, y: y + 0.15, w: w - 0.35, h: h * 0.55,
    fontSize: 36, fontFace: HEADER_FONT, color: valueColor, bold: true,
    align: "left", valign: "middle", margin: 0,
  });
  slide.addText(label, {
    x: x + 0.2, y: y + h * 0.55 + 0.05, w: w - 0.35, h: h * 0.40,
    fontSize: 11, fontFace: BODY_FONT, color: GRAY,
    align: "left", valign: "top", margin: 0,
  });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 1, TITLE
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "SECTION" });
  s.addText("Predicting Medicare Part D Drug Spending Patterns", {
    x: 0.7, y: 1.8, w: W - 1.4, h: 0.9,
    fontSize: 36, fontFace: HEADER_FONT, color: WHITE, bold: true, align: "left",
  });
  s.addText("and Identifying Prescriber Outliers", {
    x: 0.7, y: 2.7, w: W - 1.4, h: 0.7,
    fontSize: 30, fontFace: HEADER_FONT, color: ICE, italic: true, align: "left",
  });
  // accent line under title
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 3.6, w: 1.4, h: 0.05, fill: { color: GOLD }, line: { type: "none" },
  });
  s.addText("A Data-Driven Framework for Pharmacy Benefit Management Formulary Optimization", {
    x: 0.7, y: 3.85, w: W - 1.4, h: 0.5,
    fontSize: 14, fontFace: BODY_FONT, color: ICE, align: "left",
  });
  s.addText([
    { text: "Angel Pena", options: { bold: true, color: WHITE, fontSize: 18, breakLine: true } },
    { text: "QM 640: Data Analytics Capstone  |  Walsh College", options: { color: ICE, fontSize: 14, breakLine: true } },
    { text: "Dr. Sanhita Karmakar  |  Spring 2026  |  Interim Report v4",        options: { color: ICE, fontSize: 14 } },
  ], { x: 0.7, y: 5.0, w: W - 1.4, h: 1.5, fontFace: BODY_FONT });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 2, THE PROBLEM (stat callouts)
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "The Problem: Part D Spending Is Outpacing Everything");
  divider(s, 1.10);

  s.addText("Medicare Part D drug spending grew faster than enrollment, faster than overall " +
            "healthcare inflation, and is now a top-three pressure point on Medicare Trust Fund solvency.",
    { x: 0.5, y: 1.30, w: W - 1, h: 0.7,
      fontSize: 15, fontFace: BODY_FONT, color: NAVY, italic: true, valign: "middle" });

  const cardW = 2.95, cardH = 1.7, top = 2.25, gap = 0.20;
  statCard(s, 0.5,                          top, cardW, cardH, "$275.8B",  "Total 2023 Part D cost\n(up from $103.7B in 2013)");
  statCard(s, 0.5 + (cardW + gap) * 1,      top, cardW, cardH, "+166%",    "10-year cumulative growth\n~10.3% CAGR");
  statCard(s, 0.5 + (cardW + gap) * 2,      top, cardW, cardH, "85.2%",    "Brand share of total cost\nDespite <15% of claims");
  statCard(s, 0.5 + (cardW + gap) * 3,      top, cardW, cardH, "33×",      "Brand-vs-generic cost\nper claim ratio (2023)");

  s.addText("Per-beneficiary cost +83.7% vs enrollment +44.8% — this is a price-and-mix problem, not an enrollment problem.",
    { x: 0.5, y: 4.20, w: W - 1, h: 0.4,
      fontSize: 13, fontFace: BODY_FONT, color: GRAY, italic: true, align: "center" });

  // Embed Figure 1 (wider slide-optimized version) below the callout
  s.addImage({ path: path.join(FIG, "fig1_total_cost_trend_slide.png"),
               x: 0.5, y: 4.65, w: 12.3, h: 2.45 });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 3, RESEARCH QUESTIONS
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "Five Research Questions, Five Methods");
  divider(s, 1.10);

  const rqs = [
    ["RQ1", "What drug attributes predict 2019-2023 spending growth?",
     "OLS Regression + 5-fold CV",                        "COMPLETE", ACCENT],
    ["RQ2", "Do state-level brand-vs-generic rates vary significantly?",
     "ANOVA + Multivariable OLS (BRFSS+ACS)",             "COMPLETE", ACCENT],
    ["RQ3", "Do Open Payments financial relationships correlate with brand prescribing?",
     "Within-specialty Logistic Regression",              "COMPLETE", ACCENT],
    ["RQ4", "Can K-means identify distinct drug utilization profiles?",
     "K-Means Clustering (k=4)",        "COMPLETE",  ACCENT],
    ["RQ5", "What annual savings if high-brand prescribers shifted to specialty median?",
     "Simulation + 1,000-iter Bootstrap CI",              "COMPLETE", ACCENT],
  ];

  const rowH = 0.85, top = 1.35;
  rqs.forEach((row, i) => {
    const y = top + i * (rowH + 0.10);
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: W - 1, h: rowH,
      fill: { color: LIGHT }, line: { type: "none" },
    });
    // RQ label tile
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 0.9, h: rowH,
      fill: { color: NAVY }, line: { type: "none" },
    });
    s.addText(row[0], {
      x: 0.5, y, w: 0.9, h: rowH,
      fontSize: 22, fontFace: HEADER_FONT, color: WHITE, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    // Question
    s.addText(row[1], {
      x: 1.55, y: y + 0.05, w: 7.0, h: rowH * 0.55,
      fontSize: 13, fontFace: BODY_FONT, color: NAVY, bold: true, valign: "middle", margin: 0,
    });
    // Method
    s.addText(row[2], {
      x: 1.55, y: y + rowH * 0.55, w: 7.0, h: rowH * 0.45,
      fontSize: 11, fontFace: BODY_FONT, color: GRAY, italic: true, valign: "middle", margin: 0,
    });
    // Status pill, text color picked for contrast (NAVY on gold, WHITE on red)
    const pillTextColor = row[4] === GOLD ? NAVY : WHITE;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 9.2, y: y + 0.20, w: 2.5, h: 0.45,
      fill: { color: row[4] }, line: { type: "none" }, rectRadius: 0.1,
    });
    s.addText(row[3], {
      x: 9.2, y: y + 0.20, w: 2.5, h: 0.45,
      fontSize: 11, fontFace: BODY_FONT, color: pillTextColor, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
  });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 4, DATA SOURCES
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "Data: Three CMS Files, All Public");
  divider(s, 1.10);

  const datasets = [
    {
      title: "Part D Grand Totals",
      sub: "2013-2023  |  11 rows × 30 cols",
      detail: "Aggregate annual spending, claims, beneficiaries, LIS/non-LIS split. " +
              "Source for trend analysis and Figure 1-4.",
      icon: "$",
    },
    {
      title: "Part D Spending by Drug",
      sub: "2019-2023  |  3,598 drugs × 50 cols",
      detail: "Drug-level spending, claims, beneficiaries, unit cost. Outcome variable for " +
              "RQ1 OLS; feature matrix for RQ4 K-means.",
      icon: "Rx",
    },
    {
      title: "Part D Prescribers by Drug",
      sub: "2023  |  1.1M rows (200K sampled)",
      detail: "Prescriber-drug-level claim and cost data with NPI, state, specialty. " +
              "Driver of RQ2 (state ANOVA), RQ3 (specialty proxy), RQ5 (savings simulation).",
      icon: "MD",
    },
  ];

  const cardW = 4.0, cardH = 4.5, top = 1.45, gap = 0.20;
  datasets.forEach((d, i) => {
    const x = 0.5 + i * (cardW + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: ICE, width: 1.5 },
      shadow: { type: "outer", color: "000000", blur: 10, offset: 3, angle: 90, opacity: 0.10 },
    });
    // header strip
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: cardW, h: 1.1,
      fill: { color: NAVY }, line: { type: "none" },
    });
    // icon circle
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.25, y: top + 0.25, w: 0.6, h: 0.6,
      fill: { color: GOLD }, line: { type: "none" },
    });
    s.addText(d.icon, {
      x: x + 0.25, y: top + 0.25, w: 0.6, h: 0.6,
      fontSize: 14, fontFace: HEADER_FONT, color: NAVY, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(d.title, {
      x: x + 1.0, y: top + 0.20, w: cardW - 1.1, h: 0.45,
      fontSize: 16, fontFace: HEADER_FONT, color: WHITE, bold: true, valign: "middle", margin: 0,
    });
    s.addText(d.sub, {
      x: x + 1.0, y: top + 0.62, w: cardW - 1.1, h: 0.35,
      fontSize: 10, fontFace: BODY_FONT, color: ICE, italic: true, valign: "middle", margin: 0,
    });
    s.addText(d.detail, {
      x: x + 0.3, y: top + 1.30, w: cardW - 0.6, h: cardH - 1.5,
      fontSize: 12, fontFace: BODY_FONT, color: NAVY, valign: "top", margin: 0, paraSpaceAfter: 4,
    });
  });

  s.addText("All datasets downloaded from data.cms.gov, no proprietary or restricted access.",
    { x: 0.5, y: 6.30, w: W - 1, h: 0.4,
      fontSize: 12, fontFace: BODY_FONT, color: GRAY, italic: true, align: "center" });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 5, EDA: COST CONCENTRATION
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "Where the Money Goes: Cost Concentration");
  divider(s, 1.10);

  // Two figures side by side
  s.addImage({ path: path.join(FIG, "fig5_top20_drugs.png"),
               x: 0.5, y: 1.35, w: 5.5, h: 5.2 });
  s.addImage({ path: path.join(FIG, "fig2_brand_generic_trend.png"),
               x: 6.4, y: 1.35, w: 6.4, h: 2.5 });

  // Insight box bottom right
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: 4.10, w: 6.4, h: 2.45,
    fill: { color: LIGHT }, line: { type: "none" },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.4, y: 4.10, w: 0.08, h: 2.45,
    fill: { color: ACCENT }, line: { type: "none" },
  });
  s.addText("Key insight", {
    x: 6.6, y: 4.20, w: 6.0, h: 0.35,
    fontSize: 11, fontFace: BODY_FONT, color: ACCENT, bold: true, margin: 0,
  });
  s.addText("A handful of brand drugs, Eliquis, Ozempic, Jardiance, Mounjaro, Trulicity " +
            ", anchor the top of the distribution.",
    { x: 6.6, y: 4.55, w: 6.0, h: 0.6,
      fontSize: 14, fontFace: BODY_FONT, color: NAVY, bold: true, margin: 0 });
  s.addText("Brand share of total cost rose from 81.5% (2013) to 85.2% (2023) even as generic claim volume kept growing. " +
            "Brand prescriptions cost 33× generic prescriptions on average, $976 vs. $29.25 per claim in 2023.",
    { x: 6.6, y: 5.10, w: 6.0, h: 1.4,
      fontSize: 12, fontFace: BODY_FONT, color: NAVY, valign: "top", margin: 0, paraSpaceAfter: 4 });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 6, METHODS OVERVIEW (visual pipeline)
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "Methodology Pipeline");
  divider(s, 1.10);

  const stages = [
    { label: "Acquire",  body: "Download three CMS files, parse pivot Excel headers, retain 3,598 drugs + 200K prescriber rows" },
    { label: "Clean",     body: "Log-transform skewed predictors; engineer dollar_growth (spend_2023 − spend_2019); brand-flag rows" },
    { label: "Model",   body: "OLS (RQ1) • K-means k=4 (RQ4) • State ANOVA (RQ2) • Specialty ANOVA (RQ3) • Savings simulation (RQ5)" },
    { label: "Validate", body: "Cohen 1988 sample-size check per RQ; ANOVA + Kruskal-Wallis pairing; elbow method; floor/ceiling bounds" },
    { label: "Report",  body: "Live read from CSVs, no hardcoded numbers; 14 figures; PDF + DOCX + this deck" },
  ];

  const cardW = 2.40, cardH = 4.8, top = 1.45, gap = 0.12;
  stages.forEach((st, i) => {
    const x = 0.5 + i * (cardW + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: cardW, h: cardH,
      fill: { color: WHITE }, line: { color: ICE, width: 1.5 },
    });
    // top number circle
    s.addShape(pres.shapes.OVAL, {
      x: x + (cardW - 0.7) / 2, y: top + 0.25, w: 0.7, h: 0.7,
      fill: { color: NAVY }, line: { type: "none" },
    });
    s.addText(String(i + 1), {
      x: x + (cardW - 0.7) / 2, y: top + 0.25, w: 0.7, h: 0.7,
      fontSize: 22, fontFace: HEADER_FONT, color: WHITE, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(st.label, {
      x, y: top + 1.10, w: cardW, h: 0.5,
      fontSize: 17, fontFace: HEADER_FONT, color: NAVY, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    // divider
    s.addShape(pres.shapes.RECTANGLE, {
      x: x + 0.3, y: top + 1.65, w: cardW - 0.6, h: 0.03,
      fill: { color: GOLD }, line: { type: "none" },
    });
    s.addText(st.body, {
      x: x + 0.2, y: top + 1.85, w: cardW - 0.4, h: cardH - 2.1,
      fontSize: 11, fontFace: BODY_FONT, color: NAVY, valign: "top", margin: 0, paraSpaceAfter: 3,
    });
  });

  s.addText("Every output number traces back to a CSV produced by analysis_v2.py.",
    { x: 0.5, y: 6.55, w: W - 1, h: 0.35,
      fontSize: 12, fontFace: BODY_FONT, color: GRAY, italic: true, align: "center" });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 7, RQ1: OLS REGRESSION
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "RQ1, What Drives Drug Spending Growth?");
  divider(s, 1.10);

  // Big R² stat
  statCard(s, 0.5, 1.40, 3.6, 1.6, "R² = 0.913", "OLS goodness of fit, n = 3,404 drugs");

  // bullets
  bulletList(s, [
    "All 5 predictors significant at p < .0001",
    "Claims volume is the dominant signal (β log_claims = 1.94)",
    "Unit cost contributes positively (β = 0.54); manufacturer count slightly negatively (β = −0.02)",
    "log_dollar_growth replaces % growth, weights drugs by absolute program impact",
    "Implication: spending growth = volume × price × intensity, not enrollment",
  ], { x: 0.5, y: 3.10, w: 5.2, h: 3.6,
       fontSize: 13, fontFace: BODY_FONT, paraSpaceAfter: 6 });

  // Figure 8 right
  s.addImage({ path: path.join(FIG, "fig8_regression.png"),
               x: 5.9, y: 1.40, w: 6.9, h: 4.5 });
  s.addText("Figure 8.  Predicted vs. actual log(spend) and residuals.",
    { x: 5.9, y: 6.00, w: 6.9, h: 0.4,
      fontSize: 10, fontFace: BODY_FONT, color: GRAY, italic: true, align: "center" });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 8, RQ4: K-MEANS CLUSTERS
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "RQ4, Four Distinct Drug Profiles");
  divider(s, 1.10);

  const clusters = [
    { label: "High-Spend High-Growth", n: "845 drugs",
      drugs: "Eliquis (+$11B), Ozempic (+$8.6B), Jardiance (+$7.4B), Trulicity (+$5.1B), Mounjaro (+$2.4B)",
      color: ACCENT, role: "Real formulary targets" },
    { label: "High-Cost Specialty", n: "821 drugs",
      drugs: "Median unit cost $314; biologics, oncology, rare disease",
      color: NAVY, role: "Limited substitution options" },
    { label: "High-Volume Generic", n: "743 drugs",
      drugs: "High claims, negative dollar growth, generic conversion working",
      color: GOLD, role: "Success stories" },
    { label: "Low-Impact Declining", n: "1,189 drugs",
      drugs: "Low spend, shrinking, minimal formulary relevance",
      color: GRAY, role: "Park / monitor" },
  ];

  const cardW = (W - 1.2) / 4, cardH = 3.0, top = 1.30, gap = 0.20;
  clusters.forEach((c, i) => {
    const x = 0.5 + i * (cardW + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: cardW, h: cardH,
      fill: { color: LIGHT }, line: { type: "none" },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: top, w: cardW, h: 0.45,
      fill: { color: c.color }, line: { type: "none" },
    });
    s.addText(c.label, {
      x, y: top, w: cardW, h: 0.45,
      fontSize: 12, fontFace: HEADER_FONT, color: WHITE, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(c.n, {
      x, y: top + 0.55, w: cardW, h: 0.4,
      fontSize: 18, fontFace: HEADER_FONT, color: c.color, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    s.addText(c.drugs, {
      x: x + 0.15, y: top + 1.05, w: cardW - 0.3, h: cardH - 1.65,
      fontSize: 11, fontFace: BODY_FONT, color: NAVY, valign: "top", margin: 0, paraSpaceAfter: 3,
    });
    s.addText(c.role, {
      x: x + 0.15, y: top + cardH - 0.55, w: cardW - 0.3, h: 0.45,
      fontSize: 11, fontFace: BODY_FONT, color: NAVY, italic: true, bold: true, align: "center", margin: 0,
    });
  });

  s.addImage({ path: path.join(FIG, "fig9_clustering.png"),
               x: 1.0, y: 4.45, w: 11.3, h: 2.60, sizing: { type: "contain", w: 11.3, h: 2.60 } });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 9, RQ2: STATE ANOVA
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "RQ2: State Demographics Drive Brand Share");
  divider(s, 1.10);

  // Three stat cards
  statCard(s, 0.5, 1.35, 3.95, 1.5, "F = 179.5", "Full-file ANOVA, 54 states, n = 995,954");
  statCard(s, 4.65, 1.35, 3.95, 1.5, "R² = 0.61", "BRFSS+ACS OLS, n = 51 (50 states + DC)");
  statCard(s, 8.80, 1.35, 4.00, 1.5, "η² = 0.01", "State alone explains only ~1% of variance");

  bulletList(s, [
    "State as a categorical factor explains only ~1% of prescriber brand-share variance",
    "But 7 BRFSS+ACS state demographics together explain ~61% of state-level variance",
    "Significant predictors: age 65+ (negative), hypertension (positive), obesity and uninsured rate (both negative)",
    "Takeaway: demographics matter more than geographic identity per se",
  ], { x: 0.5, y: 3.05, w: W - 1, h: 1.2,
       fontSize: 12, fontFace: BODY_FONT, paraSpaceAfter: 4 });

  s.addImage({ path: path.join(FIG, "fig12_state_brand_slide.png"),
               x: 0.5, y: 4.30, w: 12.3, h: 2.85 });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 10, RQ3: SPECIALTY PROXY
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "RQ3: Open Payments Predicts Brand Prescribing");
  divider(s, 1.10);

  statCard(s, 0.5, 1.35, 3.95, 1.5, "57.1%", "of Part D prescribers have Open Payments records");
  statCard(s, 4.65, 1.35, 3.95, 1.5, "OR 1.09", "$1K+ payments raise above-median odds 9.3%");
  statCard(s, 8.80, 1.35, 4.00, 1.5, "OR 0.95", "Meals alone: NEGATIVE association");

  bulletList(s, [
    "Within-specialty logistic on 650,861 prescribers; LR test p < .0001",
    "Speaker fees (OR=1.024), large payments (OR=1.094), total exposure (OR=1.035) all positive and significant",
    "Food-and-beverage payments alone trend negative, the signal lives in larger, targeted transfers",
    "Specialty ANOVA still holds: F=5,509, eta^2=0.139 on the full file",
  ], { x: 0.5, y: 3.05, w: W - 1, h: 1.2,
       fontSize: 12, fontFace: BODY_FONT, paraSpaceAfter: 4 });

  s.addImage({ path: path.join(FIG, "fig13_specialty_brand_slide.png"),
               x: 0.5, y: 4.30, w: 12.3, h: 2.85 });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 11, RQ5: SAVINGS SIMULATION
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "RQ5: $9.91B Annual Savings (95% CI $9.59B-$10.26B)");
  divider(s, 1.10);

  // Hero stat
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.35, w: 5.6, h: 2.7,
    fill: { color: NAVY }, line: { type: "none" },
  });
  s.addText("$9.91B / year", {
    x: 0.5, y: 1.55, w: 5.6, h: 1.2,
    fontSize: 40, fontFace: HEADER_FONT, color: GOLD, bold: true,
    align: "center", valign: "middle", margin: 0,
  });
  s.addText("Floor estimate, 50% substitution per Choudhry et al. (2011). 95% bootstrap CI: $9.59B-$10.26B",
    { x: 0.5, y: 2.85, w: 5.6, h: 0.7,
      fontSize: 13, fontFace: BODY_FONT, color: ICE, italic: true,
      align: "center", valign: "middle", margin: 0 });
  s.addText("3.6% of total 2023 Part D ($275.8B), real, recurring, but bounded",
    { x: 0.5, y: 3.50, w: 5.6, h: 0.5,
      fontSize: 11, fontFace: BODY_FONT, color: ICE,
      align: "center", valign: "middle", margin: 0 });

  // How it's computed
  bulletList(s, [
    "Substitutable-pair cost differential: $316.86 per claim (368 brand-generic pairs identified)",
    "Per-prescriber excess brand share above specialty median, full 1.1M-NPI file",
    "1,000-iteration bootstrap CI on the full population, no extrapolation needed",
    "Sensitivity sweep across 30% to 70% substitution shown in Table 14 of the report",
    "Top specialties by ceiling: Family Practice, Internal Medicine, Nurse Practitioners",
  ], { x: 6.3, y: 1.35, w: 6.5, h: 2.7,
       fontSize: 13, fontFace: BODY_FONT, paraSpaceAfter: 4 });

  s.addImage({ path: path.join(FIG, "fig14_savings_dist_slide.png"),
               x: 0.5, y: 4.20, w: 12.3, h: 2.95 });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 12, SAMPLE SIZE VALIDATION
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "Every RQ Has Statistical Power to Detect Real Effects");
  divider(s, 1.10);

  s.addText("Sample size minimums computed a priori (Cohen 1988): α = .05, power = 0.80, medium effects.",
    { x: 0.5, y: 1.30, w: W - 1, h: 0.5,
      fontSize: 13, fontFace: BODY_FONT, color: NAVY, italic: true });

  const headers = ["RQ", "Test", "Minimum n", "Achieved n", "Status"];
  const rows = [
    ["RQ1", "Multiple OLS + 5-fold Cross-Validation",        "92",    "3,404", "✓ Exceeded"],
    ["RQ2", "Full-file ANOVA + BRFSS+ACS OLS",               "567",   "995,699", "✓ Exceeded"],
    ["RQ3", "Specialty ANOVA + Open Payments Logistic",      "360",   "650,861", "✓ Exceeded"],
    ["RQ4", "K-means clustering, 50 per cluster",            "200",   "3,598", "✓ Exceeded"],
    ["RQ5", "Sample mean + 1,000-iter Bootstrap CI",         "385",   "995,954", "✓ Exceeded"],
  ];

  const tableData = [
    headers.map(h => ({ text: h,
      options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "center", fontSize: 13, fontFace: HEADER_FONT } })),
    ...rows.map(r => r.map((c, i) => ({ text: c,
      options: { color: NAVY, align: i === 0 || i >= 2 ? "center" : "left", fontSize: 12, fontFace: BODY_FONT } }))),
  ];

  s.addTable(tableData, {
    x: 0.5, y: 1.95, w: W - 1, h: 3.6,
    colW: [0.9, 5.2, 1.6, 1.6, 3.0],
    rowH: 0.55,
    border: { pt: 0.5, color: ICE },
  });

  // takeaway
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.75, w: W - 1, h: 1.2,
    fill: { color: LIGHT }, line: { type: "none" },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.75, w: 0.08, h: 1.2,
    fill: { color: ACCENT }, line: { type: "none" },
  });
  s.addText("Every research question clears its statistical-power threshold by a wide margin, most by 5-15×. " +
            "Results are not chance findings.",
    { x: 0.75, y: 5.80, w: W - 1.25, h: 1.1,
      fontSize: 14, fontFace: BODY_FONT, color: NAVY, bold: true, valign: "middle", margin: 0 });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 13, KEY TAKEAWAYS
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "Five Findings That Matter");
  divider(s, 1.10);

  const findings = [
    { n: "1", t: "Spending growth is price × intensity",
      d: "OLS confirms claims, unit cost, and dollar growth, not enrollment, explain 91% of log-spending. Formulary intensity is the lever." },
    { n: "2", t: "GLP-1s, DOACs, SGLT2s anchor the cost problem",
      d: "K-means isolates 845 drugs as the High-Spend High-Growth cluster. Eliquis, Ozempic, Jardiance, Trulicity, Mounjaro added $34B+ in spend." },
    { n: "3", t: "State demographics drive brand share, state identity does not",
      d: "State as a factor: η² = 0.01. Seven BRFSS+ACS demographics together: R² = 0.61. Specialty is even stronger (η² = 0.139)." },
    { n: "4", t: "Open Payments significantly predicts brand prescribing",
      d: "Logistic on 650,861 physicians: total payment OR=1.035, speaker fees OR=1.024, large $1K+ payments OR=1.094. Food-and-beverage alone is negative; the signal lives in larger, targeted transfers." },
    { n: "5", t: "$9.91B annual savings (95% CI $9.59B-$10.26B)",
      d: "Full-population bootstrap estimate using a substitutable-pair cost differential. About 3.6% of total Part D 2023 spend, recurring every year." },
  ];

  const rowH = 0.95, top = 1.30;
  findings.forEach((f, i) => {
    const y = top + i * (rowH + 0.10);
    // number badge
    s.addShape(pres.shapes.OVAL, {
      x: 0.5, y: y + 0.10, w: 0.75, h: 0.75,
      fill: { color: NAVY }, line: { type: "none" },
    });
    s.addText(f.n, {
      x: 0.5, y: y + 0.10, w: 0.75, h: 0.75,
      fontSize: 26, fontFace: HEADER_FONT, color: GOLD, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
    // title + body
    s.addText(f.t, {
      x: 1.4, y: y, w: W - 1.9, h: 0.45,
      fontSize: 16, fontFace: HEADER_FONT, color: NAVY, bold: true, valign: "middle", margin: 0,
    });
    s.addText(f.d, {
      x: 1.4, y: y + 0.45, w: W - 1.9, h: rowH - 0.45,
      fontSize: 12, fontFace: BODY_FONT, color: NAVY, valign: "top", margin: 0, paraSpaceAfter: 3,
    });
  });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 14, LIMITATIONS + NEXT STEPS
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  slideTitle(s, "What's Provisional & What Comes Next");
  divider(s, 1.10);

  // Left: limitations
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.35, w: 6.0, h: 5.5,
    fill: { color: LIGHT }, line: { type: "none" },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.35, w: 0.08, h: 5.5,
    fill: { color: ACCENT }, line: { type: "none" },
  });
  s.addText("Honest limitations", {
    x: 0.75, y: 1.45, w: 5.7, h: 0.5,
    fontSize: 18, fontFace: HEADER_FONT, color: NAVY, bold: true, margin: 0,
  });
  bulletList(s, [
    "Every association is observational, not causal",
    "RQ5 floor uses a single 50% substitution rate (range 30-70% shown in report Table 14)",
    "BRFSS values transcribed from published CDC tables; live API access not available",
    "Dollar growth treats post-2019 entrants as $0 baseline",
    "Cluster solution not yet stress-tested against alternative algorithms",
  ], { x: 0.75, y: 2.05, w: 5.6, h: 4.6,
       fontSize: 14, fontFace: BODY_FONT, paraSpaceAfter: 12, valign: "top" });

  // Right: next steps
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.8, y: 1.35, w: 6.0, h: 5.5,
    fill: { color: LIGHT }, line: { type: "none" },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.8, y: 1.35, w: 0.08, h: 5.5,
    fill: { color: GOLD }, line: { type: "none" },
  });
  s.addText("Final-report roadmap", {
    x: 7.05, y: 1.45, w: 5.7, h: 0.5,
    fontSize: 18, fontFace: HEADER_FONT, color: NAVY, bold: true, margin: 0,
  });
  bulletList(s, [
    "Incorporate committee feedback from this presentation",
    "Disaggregate RQ3 logistic by therapeutic class (GLP-1, DOAC, statin, biologic)",
    "Drug-class-specific RQ5 substitution rates instead of single 50% assumption",
    "Stress-test RQ4 with Gaussian mixture and DBSCAN, report silhouette scores",
    "Integrate findings into a PBM-facing recommendation memo with stakeholder-specific actions",
  ], { x: 7.05, y: 2.05, w: 5.6, h: 4.6,
       fontSize: 13, fontFace: BODY_FONT, paraSpaceAfter: 6, valign: "top" });
}


// ════════════════════════════════════════════════════════════════════════════
// SLIDE 15, Q&A / THANK YOU
// ════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide({ masterName: "SECTION" });
  s.addText("Thank you", {
    x: 0.7, y: 2.2, w: W - 1.4, h: 1.0,
    fontSize: 60, fontFace: HEADER_FONT, color: WHITE, bold: true,
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.7, y: 3.3, w: 1.4, h: 0.06,
    fill: { color: GOLD }, line: { type: "none" },
  });
  s.addText("Questions & Discussion", {
    x: 0.7, y: 3.55, w: W - 1.4, h: 0.7,
    fontSize: 24, fontFace: HEADER_FONT, color: ICE, italic: true,
  });

  s.addText([
    { text: "Angel Pena", options: { bold: true, color: WHITE, fontSize: 16, breakLine: true } },
    { text: "QM 640 Data Analytics Capstone  |  Walsh College", options: { color: ICE, fontSize: 13, breakLine: true } },
    { text: "Repo: github.com/Apena87/QM-640-Quantitative-Methods-Capstone", options: { color: ICE, fontSize: 13 } },
  ], { x: 0.7, y: 5.0, w: W - 1.4, h: 1.5, fontFace: BODY_FONT });
}


// === SAVE =============================================================
process.on("uncaughtException", e => { console.error("UNCAUGHT:", e); process.exit(1); });
process.on("unhandledRejection", e => { console.error("REJECTED:", e); process.exit(1); });

console.log("Reached save block");
pres.write({ outputType: "nodebuffer" })
  .then(buf => {
    fs.writeFileSync(OUT, buf);
    console.log("Saved:", OUT, "(", buf.length, "bytes)");
  })
  .catch(e => { console.error("CATCH:", e); process.exit(1); });
