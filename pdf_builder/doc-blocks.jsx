/* global React, Sparkline, Sparkbars, LineChart, ScenarioFan, BarChart, Heatmap, Timeline, SAMPLE */

// =========================================================
// Block library — composable research-document objects
// Each block is a self-contained section, takes (props, S=SAMPLE).
// BLOCKS registry exposes label, recommended span, optional minRows,
// and default props for the composer palette.
// =========================================================

// ---------- Shared chrome ----------
function BlockChrome({ kicker, title, subtitle, right, rule = "thin", children }) {
  const RuleEl = rule === "thick" ? "rule-thick"
              : rule === "accent" ? "rule-accent"
              : rule === "none"   ? null
              : "rule";
  return (
    <div className="block">
      {(kicker || title || right) && (
        <header className="block-head">
          <div className="block-head-text">
            {kicker && <div className="kicker">{kicker}</div>}
            {title && <h3 className="h-section">{title}</h3>}
            {subtitle && <div className="label" style={{ marginTop:2 }}>{subtitle}</div>}
          </div>
          {right && <div className="block-head-right">{right}</div>}
        </header>
      )}
      {RuleEl && <hr className={RuleEl} style={{ marginBottom: 8 }} />}
      <div className="block-body">{children}</div>
    </div>
  );
}

// ============= TITLE / LEAD =============
function TitleBlock({ size = "display" }) {
  const S = SAMPLE;
  const fontSize = size === "display" ? 44 : size === "large" ? 34 : 28;
  return (
    <div className="block">
      <div className="kicker" style={{ marginBottom:6 }}>Thesis</div>
      <h1 className="h-display" style={{ fontSize, lineHeight:1.04 }}>{S.title}</h1>
      <p style={{
        fontFamily:"var(--serif)", fontStyle:"italic",
        fontSize:15, lineHeight:1.4, color:"var(--ink-2)",
        margin:"8px 0 0", maxWidth:"60ch",
      }}>
        {S.subtitle}
      </p>
    </div>
  );
}

function BottomLine() {
  const S = SAMPLE;
  return (
    <div className="block" style={{
      background:"var(--paper-deep)",
      borderLeft:"3px solid var(--accent)",
      padding:"10px 14px",
    }}>
      <div className="label label-accent" style={{ marginBottom:4 }}>Bottom Line</div>
      <div className="pull" style={{ fontSize:15.5 }}>
        <span className="mark">“</span>{S.bottomline}<span className="mark" style={{ marginLeft:2 }}>”</span>
      </div>
      <div style={{ display:"flex", gap:4, marginTop:8, flexWrap:"wrap" }}>
        <span className="tag accent">Duration: Add</span>
        <span className="tag">Equity: Trim</span>
        <span className="tag accent">Vol: Long</span>
      </div>
    </div>
  );
}

function DropCapIntro({ paragraphs = 2 }) {
  return (
    <div className="block">
      <div className="body-tight dropcap" style={{ fontSize:12.5, lineHeight:1.5 }}>
        <p>
          The disinflation narrative that propelled risk through 2025 is entering its
          least telegenic phase. Headline CPI has cleared the easy gains; what remains
          is a slow grind through shelter and core services where the Federal Reserve
          has the least leverage. We move <em>Base from Bull</em> across asset allocations
          and tilt into convexity over conviction.
        </p>
        {paragraphs >= 2 && (
          <p>
            Our framework rests on four observations, each sized to a specific catalyst
            window and paired with a downside hedge we believe trades cheap relative to
            realized cross-asset volatility. The window for graceful rotation is open,
            but narrowing — Jackson Hole is our line in the sand.
          </p>
        )}
      </div>
    </div>
  );
}

function PullQuoteBlock({ text }) {
  const S = SAMPLE;
  const body = text || S.bottomline;
  return (
    <blockquote className="block" style={{
      margin:0,
      padding:"14px 18px",
      borderTop:"2px solid var(--ink)",
      borderBottom:"2px solid var(--ink)",
      textAlign:"center",
    }}>
      <div className="kicker" style={{ marginBottom:6 }}>Pull Quote</div>
      <p className="pull" style={{ margin:0, fontSize:19 }}>
        <span className="mark">“</span>{body}<span className="mark" style={{ marginLeft:2 }}>”</span>
      </p>
    </blockquote>
  );
}

function AuthorBlock() {
  const S = SAMPLE;
  return (
    <BlockChrome kicker="Authors" title="Strategy Team">
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:14 }}>
        {S.authors.map((a,i)=>(
          <div key={i}>
            <div className="serif" style={{ fontSize:13, fontWeight:700, lineHeight:1.2 }}>{a.name}</div>
            <div className="sans" style={{ fontSize:10, color:"var(--ink-3)" }}>{a.role}</div>
            <div className="mono" style={{ fontSize:9.5, color:"var(--accent)", marginTop:2 }}>{a.email}</div>
          </div>
        ))}
      </div>
    </BlockChrome>
  );
}

// ============= DATA TABLES =============
function HeroLevelsBlock({ compact = false }) {
  const S = SAMPLE;
  return (
    <div className="block">
      <div className="kicker" style={{ marginBottom:4 }}>Market Levels</div>
      <hr className="rule-thick" style={{ marginBottom:8 }} />
      <div style={{ display:"grid", gridTemplateColumns:`repeat(${S.hero.length}, 1fr)`, gap:0 }}>
        {S.hero.map((m,i)=>(
          <div key={i} style={{
            padding: compact ? "4px 8px" : "6px 10px",
            borderRight: i<S.hero.length-1 ? "1px solid var(--rule-soft)" : "none",
          }}>
            <div className="label" style={{ fontSize:8 }}>{m.k}</div>
            <div className="mono" style={{
              fontSize: compact ? 13 : 15,
              fontWeight:600, color:"var(--ink)", marginTop:2
            }}>{m.v}</div>
            <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginTop:2 }}>
              <span className="mono" style={{
                fontSize:9.5,
                color: m.d.startsWith("-") ? "var(--down)" : (m.d.startsWith("+") ? "var(--up)" : "var(--ink-3)")
              }}>{m.d}</span>
              <Sparkline data={m.spark} width={compact ? 36 : 50} height={14} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ThesisBlock({ kicker = "I. Executive Summary", title = "Four moves into the last mile" }) {
  const S = SAMPLE;
  return (
    <BlockChrome kicker={kicker} title={title}>
      <ol style={{ listStyle:"none", padding:0, margin:0 }}>
        {S.thesis.map((th,i)=>(
          <li key={i} style={{
            display:"grid", gridTemplateColumns:"26px 1fr", gap:8,
            padding:"7px 0",
            borderTop: i===0 ? "1px solid var(--rule)" : "1px solid var(--rule-soft)",
          }}>
            <span className="mono" style={{ fontSize:14, color:"var(--accent)", fontWeight:700 }}>
              {String(i+1).padStart(2,"0")}
            </span>
            <span className="body-tight" style={{ fontSize:11.5, margin:0 }}>{th}</span>
          </li>
        ))}
      </ol>
    </BlockChrome>
  );
}

function ScenarioTableBlock({ kicker = "II. Estimates", title = "Three paths · year-end" }) {
  const S = SAMPLE;
  return (
    <BlockChrome kicker={kicker} title={title}>
      <table className="data">
        <thead>
          <tr>
            <th></th>
            {S.scenarios.cols.map((c,i)=>(
              <th key={i} className="n" style={{
                color: i===0 ? "var(--down)" : (i===2 ? "var(--up)" : "var(--ink)"),
              }}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {S.scenarios.rows.map((r,i)=>(
            <tr key={i} style={{
              fontWeight: r.bold ? 700 : 400,
              background: r.bold ? "var(--paper-deep)" : "transparent"
            }}>
              <td className="name">{r.label}</td>
              {r.vals.map((v,j)=>(
                <td key={j} className="n" style={{
                  color: j===1 ? "var(--ink)" : "var(--ink-2)",
                  fontWeight: j===1 ? 600 : 400,
                }}>{v}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </BlockChrome>
  );
}

function PrintsBlock({ kicker = "V. Recent Data", title = "Macro tape · 30 days" }) {
  const S = SAMPLE;
  return (
    <BlockChrome kicker={kicker} title={title}>
      <table className="data">
        <thead>
          <tr>
            <th>Date</th>
            <th>Time</th>
            <th>Release</th>
            <th className="n">Actual</th>
            <th className="n">Cons.</th>
            <th className="n">σ</th>
          </tr>
        </thead>
        <tbody>
          {S.prints.map((p,i)=>(
            <tr key={i} style={{ fontWeight: p.accent ? 600 : 400 }}>
              <td className="mono" style={{ fontSize:9.5 }}>{p.date}</td>
              <td className="mono" style={{ fontSize:9, color:"var(--ink-3)" }}>{p.time}</td>
              <td className="name" style={{ fontSize:10 }}>{p.label}</td>
              <td className="n">{p.actual}</td>
              <td className="n" style={{ color:"var(--ink-3)" }}>{p.cons}</td>
              <td className="n" style={{
                color: p.surprise>0.5 ? "var(--up)" : (p.surprise<-0.5 ? "var(--down)" : "var(--ink-3)")
              }}>{p.surprise>0?"+":""}{p.surprise.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </BlockChrome>
  );
}

function RisksBlock({ kicker = "IV. Risks", title = "Five tail concerns, ranked", limit }) {
  const S = SAMPLE;
  const items = limit ? S.risks.slice(0, limit) : S.risks;
  return (
    <BlockChrome kicker={kicker} title={title}>
      {items.map((r,i)=>(
        <div key={i} style={{
          padding:"6px 0",
          borderTop: i===0 ? "1px solid var(--rule)" : "1px solid var(--rule-soft)"
        }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:2 }}>
            <span className="label label-accent">{r.tag}</span>
            <span className="mono" style={{ fontSize:9, color:"var(--ink-3)" }}>
              Severity {"●".repeat(r.sev)}{"○".repeat(5-r.sev)}
            </span>
          </div>
          <div className="h-sub" style={{ fontSize:11.5, marginBottom:2 }}>{r.title}</div>
          <div className="body-tight" style={{ fontSize:10.5, color:"var(--ink-2)" }}>{r.body}</div>
        </div>
      ))}
    </BlockChrome>
  );
}

function CatalystsBlock({ kicker = "III. Catalysts", title = "Calendar through Jackson Hole" }) {
  const S = SAMPLE;
  const [w, setW] = React.useState(null);
  const ref = React.useRef(null);
  React.useLayoutEffect(()=>{
    if (!ref.current) return;
    setW(ref.current.offsetWidth);
    const ro = new ResizeObserver(entries => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return ()=> ro.disconnect();
  },[]);
  return (
    <BlockChrome kicker={kicker} title={title} right={<span className="label">Jun 06 → Aug 22 · 2026</span>}>
      <div ref={ref} style={{ width:"100%" }}>
        {w != null && <Timeline events={S.catalysts} width={w} height={72} />}
      </div>
    </BlockChrome>
  );
}

// ============= CHARTS =============
function ScenarioFanBlock({ kicker = "Projection", title = "10Y UST · bear / base / bull", height = 170 }) {
  const S = SAMPLE;
  const [w, setW] = React.useState(null);
  const ref = React.useRef(null);
  React.useLayoutEffect(()=>{
    if (!ref.current) return;
    setW(ref.current.offsetWidth);
    const ro = new ResizeObserver(entries => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return ()=> ro.disconnect();
  },[]);
  return (
    <BlockChrome kicker={kicker} title={title}>
      <div ref={ref}>
        {w != null && <ScenarioFan width={w} height={height} bear={S.proj.bear} base={S.proj.base} bull={S.proj.bull} xLabels={S.proj.xLabels} pivot={0} />}
      </div>
      <div className="label" style={{ fontSize:8, marginTop:4, color:"var(--ink-4)" }}>
        Source: H&amp;R Strategy. Dashed lines indicate tail scenarios at ±1σ from base.
      </div>
    </BlockChrome>
  );
}

function FiscalBlock({ kicker = "VI. Fiscal Impulse", title = "Pivot to drag, Q3 2026" }) {
  const S = SAMPLE;
  const [w, setW] = React.useState(null);
  const ref = React.useRef(null);
  React.useLayoutEffect(()=>{
    if (!ref.current) return;
    setW(ref.current.offsetWidth);
    const ro = new ResizeObserver(entries => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return ()=> ro.disconnect();
  },[]);
  return (
    <BlockChrome kicker={kicker} title={title}>
      <div ref={ref}>
        {w != null && <BarChart width={w} height={140} data={S.fiscal.data} labels={S.fiscal.labels} accentIdx={S.fiscal.accent} />}
      </div>
      <div className="body-tight" style={{ fontSize:10.5, marginTop:6, color:"var(--ink-2)" }}>
        Contribution to YoY GDP, pp. TCJA expirations bind Q4 2026, removing
        <span className="num" style={{ color:"var(--accent)" }}> 0.6pp </span>
        from 2027 — the largest fiscal drag of the cycle.
      </div>
    </BlockChrome>
  );
}

function HeatmapBlock({ kicker = "VII. Cross-Asset", title = "Total returns, %", rows }) {
  const S = SAMPLE;
  const [w, setW] = React.useState(null);
  const ref = React.useRef(null);
  React.useLayoutEffect(()=>{
    if (!ref.current) return;
    setW(ref.current.offsetWidth);
    const ro = new ResizeObserver(entries => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return ()=> ro.disconnect();
  },[]);
  const r = rows || S.heatmap.rows.length;
  const cellH = 18;
  return (
    <BlockChrome kicker={kicker} title={title}>
      <div ref={ref}>
        {w != null && <Heatmap rows={S.heatmap.rows.slice(0,r)} cols={S.heatmap.cols} values={S.heatmap.values.slice(0,r)} width={w} height={26 + r*cellH} />}
      </div>
    </BlockChrome>
  );
}

function CPIChartBlock({ kicker = "Inflation", title = "CPI YoY · 24 months" }) {
  const S = SAMPLE;
  const [w, setW] = React.useState(null);
  const ref = React.useRef(null);
  React.useLayoutEffect(()=>{
    if (!ref.current) return;
    setW(ref.current.offsetWidth);
    const ro = new ResizeObserver(entries => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return ()=> ro.disconnect();
  },[]);
  return (
    <BlockChrome kicker={kicker} title={title}>
      <div ref={ref}>
        {w != null && <LineChart width={w} height={150} series={[{ data:S.cpiPath.data, color:"var(--ink)", fill:true }]} padding={{l:34,r:8,t:10,b:18}} xTicks={6} yTicks={4} yLabel="% YoY" />}
      </div>
      <div className="body-tight" style={{ fontSize:10.5, marginTop:6, color:"var(--ink-2)" }}>
        Disinflation slope has flattened; the last mile begins H2 2026.
      </div>
    </BlockChrome>
  );
}

// ============= STRUCTURE =============
function SectionHeader({ roman = "I", title = "Section Title", lede }) {
  return (
    <div className="block" style={{ paddingTop:6 }}>
      <div style={{ display:"flex", alignItems:"baseline", gap:12, minWidth:0 }}>
        <span className="serif" style={{ fontSize:34, fontStyle:"italic", color:"var(--accent)", fontWeight:700, lineHeight:1, flex:"0 0 auto", whiteSpace:"nowrap" }}>
          §{roman}
        </span>
        <h2 className="h-section" style={{ fontSize:24, margin:0, flex:"0 0 auto", whiteSpace:"nowrap" }}>{title}</h2>
        <hr className="rule-thick" style={{ flex:"1 1 auto", alignSelf:"center", minWidth:20 }} />
      </div>
      {lede && (
        <p className="body-tight" style={{ fontSize:12, fontStyle:"italic", marginTop:6, maxWidth:"70ch" }}>
          {lede}
        </p>
      )}
    </div>
  );
}

function Spacer({ rows = 1 }) {
  return <div className="block" style={{ minHeight: rows * 24 }} />;
}

function DisclosureBlock() {
  return (
    <BlockChrome kicker="Disclosures" title="Important information">
      <div className="body-tight" style={{ fontSize:10, color:"var(--ink-2)", columnCount:2, columnGap:18 }}>
        <p>
          This document is for institutional distribution only and constitutes
          general macro commentary. It does not represent an offer to buy or sell
          any security and is not personalised investment advice. Past performance
          is not indicative of future results.
        </p>
        <p>
          Halford &amp; Reade, its officers and employees may hold positions in
          instruments referenced. Forecast paths reflect a probabilistic model and
          are accompanied by explicit confidence intervals; outcomes outside the
          stated ±1σ envelope occur with non-trivial frequency.
        </p>
        <p>
          Distribution: clients of the Macro Strategy desk. Redistribution outside
          the firm is prohibited without written consent. See full Important
          Disclosures, available upon request.
        </p>
      </div>
    </BlockChrome>
  );
}

// ============= REGISTRY =============
// Maps a block `type` to its component + composer-palette metadata.
// `span` is the default 12-col grid span. `rows` is an optional grid row span.
const BLOCKS = {
  title:        { label:"Title Block",        component: TitleBlock,       span:12, group:"Heading" },
  bottomline:   { label:"Bottom Line",        component: BottomLine,       span:6,  group:"Heading" },
  pullquote:    { label:"Pull Quote",         component: PullQuoteBlock,   span:12, group:"Heading" },
  section:      { label:"Section Header",     component: SectionHeader,    span:12, group:"Heading" },
  intro:        { label:"Drop-Cap Intro",     component: DropCapIntro,     span:7,  group:"Heading" },

  hero:         { label:"Market Levels Strip",component: HeroLevelsBlock,  span:12, group:"Data" },
  thesis:       { label:"Thesis · numbered",  component: ThesisBlock,      span:7,  group:"Data" },
  scenarios:    { label:"Scenario Table",     component: ScenarioTableBlock,span:5, group:"Data" },
  prints:       { label:"Recent Prints",      component: PrintsBlock,      span:6,  group:"Data" },
  risks:        { label:"Risks",              component: RisksBlock,       span:7,  group:"Data" },
  catalysts:    { label:"Catalyst Timeline",  component: CatalystsBlock,   span:12, group:"Data" },

  scenariofan:  { label:"Scenario Fan",       component: ScenarioFanBlock, span:7,  group:"Charts" },
  fiscal:       { label:"Fiscal Bar",         component: FiscalBlock,      span:5,  group:"Charts" },
  heatmap:      { label:"Cross-Asset Heat",   component: HeatmapBlock,     span:5,  group:"Charts" },
  cpi:          { label:"CPI Line",           component: CPIChartBlock,    span:7,  group:"Charts" },

  authors:      { label:"Authors",            component: AuthorBlock,      span:12, group:"Structure" },
  disclosure:   { label:"Disclosures",        component: DisclosureBlock,  span:12, group:"Structure" },
  spacer:       { label:"Spacer",             component: Spacer,           span:12, group:"Structure" },
};

window.BLOCKS = BLOCKS;
