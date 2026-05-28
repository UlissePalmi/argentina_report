/* global React, Sparkline, Sparkbars, LineChart, ScenarioFan, BarChart, Heatmap, Timeline, SAMPLE */

// =========================================================
// VARIATION B — Two-Column with Left Rail
// Persistent left rail: TOC · authors · key levels · disclosures
// Main column: title · summary · scenarios · catalysts · risks · prints · heatmap
// =========================================================

function VariationB() {
  const S = SAMPLE;
  const toc = [
    { n:"I",   t:"Executive Summary",   p:"02" },
    { n:"II",  t:"Scenario Analysis",   p:"03" },
    { n:"III", t:"Catalysts & Timeline",p:"05" },
    { n:"IV",  t:"Risks",               p:"07" },
    { n:"V",   t:"Recent Data",         p:"09" },
    { n:"VI",  t:"Cross-Asset Recap",   p:"10" },
    { n:"VII", t:"Disclosures",         p:"12" },
  ];

  return (
    <div className="page" style={{
      display:"grid", gridTemplateColumns:"200px 1fr",
      padding:0
    }}>

      {/* ===== LEFT RAIL ===== */}
      <aside style={{
        background: "var(--paper-deep)",
        borderRight: "1px solid var(--rule)",
        padding:"24px 18px 22px",
        display:"flex", flexDirection:"column", gap:18,
      }}>
        {/* Firm mark */}
        <div>
          <div className="serif" style={{ fontWeight:900, fontSize:22, lineHeight:1, letterSpacing:"-0.01em" }}>
            H<span style={{ color:"var(--accent)" }}>&amp;</span>R
          </div>
          <div className="label" style={{ fontSize:8, marginTop:4 }}>
            {S.firm}<br/>{S.desk}
          </div>
        </div>

        <hr className="rule" />

        {/* Issue meta */}
        <div>
          <div className="label" style={{ fontSize:8 }}>Issue</div>
          <div className="mono" style={{ fontSize:11, marginTop:2, color:"var(--ink)" }}>{S.vol}</div>
          <div className="mono" style={{ fontSize:11, color:"var(--ink-2)" }}>{S.date}</div>
          <div className="tag accent" style={{ marginTop:6, fontSize:7.5, padding:"1px 4px" }}>
            Buy-Side Only
          </div>
        </div>

        <hr className="rule-thin" />

        {/* TOC */}
        <div>
          <div className="kicker" style={{ fontSize:9, marginBottom:6 }}>Contents</div>
          <ol style={{ listStyle:"none", padding:0, margin:0 }}>
            {toc.map((it,i)=>(
              <li key={i} style={{
                display:"grid",
                gridTemplateColumns:"18px 1fr 22px",
                gap:4,
                padding:"4px 0",
                borderBottom:"1px dotted var(--rule)",
                alignItems:"baseline",
              }}>
                <span className="mono" style={{ fontSize:9, color:"var(--accent)", fontWeight:700 }}>{it.n}</span>
                <span className="sans" style={{ fontSize:10, color:"var(--ink)" }}>{it.t}</span>
                <span className="mono" style={{ fontSize:9, color:"var(--ink-3)", textAlign:"right" }}>{it.p}</span>
              </li>
            ))}
          </ol>
        </div>

        <hr className="rule-thin" />

        {/* Authors */}
        <div>
          <div className="kicker" style={{ fontSize:9, marginBottom:6 }}>Strategy Team</div>
          {S.authors.map((a,i)=>(
            <div key={i} style={{ marginBottom:8 }}>
              <div className="serif" style={{ fontSize:10.5, fontWeight:700, lineHeight:1.2 }}>{a.name}</div>
              <div className="sans" style={{ fontSize:9, color:"var(--ink-3)" }}>{a.role}</div>
              <div className="mono" style={{ fontSize:8.5, color:"var(--accent)" }}>{a.email}</div>
            </div>
          ))}
        </div>

        <hr className="rule-thin" />

        {/* Key levels */}
        <div>
          <div className="kicker" style={{ fontSize:9, marginBottom:6 }}>Levels @ Close</div>
          {S.hero.map((m,i)=>(
            <div key={i} style={{
              display:"grid",
              gridTemplateColumns:"1fr auto",
              gap:4,
              padding:"3px 0",
              borderBottom: i<S.hero.length-1 ? "1px solid var(--rule-soft)" : "none",
              alignItems:"baseline",
            }}>
              <span className="sans" style={{ fontSize:9, color:"var(--ink-2)" }}>{m.k}</span>
              <div style={{ textAlign:"right" }}>
                <div className="mono" style={{ fontSize:10.5, fontWeight:600, color:"var(--ink)" }}>{m.v}</div>
                <div className="mono" style={{
                  fontSize:8.5,
                  color: m.d.startsWith("-") ? "var(--down)" : (m.d.startsWith("+") ? "var(--up)" : "var(--ink-3)")
                }}>{m.d}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ flex:1 }} />

        {/* Footer mark */}
        <div className="foot" style={{ fontSize:7.5 }}>
          {S.city}<br/>halfordreade.co
        </div>
      </aside>

      {/* ===== MAIN COLUMN ===== */}
      <main style={{ padding:"26px 32px 22px", display:"flex", flexDirection:"column" }}>

        {/* Top metadata bar */}
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}>
          <div className="kicker">{S.issue}</div>
          <div className="label">Note №241 · {S.date}</div>
        </div>
        <hr className="rule-accent" style={{ margin:"6px 0 14px" }} />

        {/* Title */}
        <header style={{ marginBottom:14 }}>
          <div className="label label-accent" style={{ marginBottom:4 }}>Macro Strategy Note</div>
          <h1 className="h-display" style={{ fontSize:42, marginBottom:8 }}>{S.title}</h1>
          <p className="lead" style={{ maxWidth:"60ch", margin:0, fontStyle:"italic", color:"var(--ink-2)" }}>
            {S.subtitle}
          </p>
        </header>

        {/* Pull quote / bottom line */}
        <div style={{
          background: "var(--paper-deep)",
          borderLeft: "3px solid var(--accent)",
          padding:"10px 14px",
          marginBottom:16,
          display:"grid", gridTemplateColumns:"auto 1fr", gap:14,
        }}>
          <div className="kicker" style={{ writingMode:"vertical-rl", transform:"rotate(180deg)", fontSize:8 }}>
            Bottom Line
          </div>
          <div className="pull" style={{ fontSize:14.5 }}>
            <span className="mark">“</span>{S.bottomline}<span className="mark" style={{ marginLeft:2 }}>”</span>
          </div>
        </div>

        {/* Section I — Executive Summary */}
        <section style={{ marginBottom:14 }}>
          <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:6 }}>
            <span className="mono" style={{ fontSize:18, fontWeight:700, color:"var(--accent)" }}>I.</span>
            <h2 className="h-section" style={{ margin:0 }}>Executive Summary</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
            <span className="label">4 points</span>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:14 }}>
            {S.thesis.map((t,i)=>(
              <div key={i} style={{ display:"grid", gridTemplateColumns:"28px 1fr", gap:6 }}>
                <div>
                  <div className="mono" style={{ fontSize:20, fontWeight:700, color:"var(--accent)", lineHeight:1 }}>
                    {String(i+1).padStart(2,"0")}
                  </div>
                </div>
                <div className="body-tight" style={{ fontSize:11.5, margin:0 }}>{t}</div>
              </div>
            ))}
          </div>
        </section>

        <hr className="rule" style={{ marginBottom:14 }} />

        {/* Section II — Scenarios */}
        <section style={{ marginBottom:14 }}>
          <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:8 }}>
            <span className="mono" style={{ fontSize:18, fontWeight:700, color:"var(--accent)" }}>II.</span>
            <h2 className="h-section" style={{ margin:0 }}>Scenario Analysis</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
            <span className="label">3 paths · 8 vars</span>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1.1fr", gap:18 }}>
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
                  <tr key={i} style={{ fontWeight: r.bold ? 700 : 400, background: r.bold ? "var(--paper-deep)" : "transparent" }}>
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

            <div>
              <div className="label" style={{ marginBottom:2 }}>10Y UST — Modeled Path</div>
              <ScenarioFan width={360} height={150}
                bear={S.proj.bear} base={S.proj.base} bull={S.proj.bull}
                xLabels={S.proj.xLabels} pivot={0} />
            </div>
          </div>
        </section>

        <hr className="rule" style={{ marginBottom:14 }} />

        {/* Section III — Catalysts */}
        <section style={{ marginBottom:14 }}>
          <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:6 }}>
            <span className="mono" style={{ fontSize:18, fontWeight:700, color:"var(--accent)" }}>III.</span>
            <h2 className="h-section" style={{ margin:0 }}>Catalysts &amp; Timeline</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
            <span className="label">Jun → Aug</span>
          </div>
          <Timeline events={S.catalysts} width={618} height={70} />
        </section>

        <hr className="rule" style={{ marginBottom:14 }} />

        {/* Section IV+V — Risks + Recent Data */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1px 1fr", gap:16, marginBottom:14 }}>
          <section>
            <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:8 }}>
              <span className="mono" style={{ fontSize:18, fontWeight:700, color:"var(--accent)" }}>IV.</span>
              <h2 className="h-section" style={{ margin:0 }}>Risks</h2>
            </div>
            {S.risks.slice(0,4).map((r,i)=>(
              <div key={i} style={{
                padding:"6px 0",
                borderTop: i===0 ? "1px solid var(--rule)" : "1px solid var(--rule-soft)"
              }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}>
                  <span className="label label-accent">{r.tag}</span>
                  <span className="mono" style={{ fontSize:9, color:"var(--ink-3)" }}>
                    Severity {"●".repeat(r.sev)}{"○".repeat(5-r.sev)}
                  </span>
                </div>
                <div className="h-sub" style={{ fontSize:11.5, margin:"2px 0" }}>{r.title}</div>
                <div className="body-tight" style={{ fontSize:10.5 }}>{r.body}</div>
              </div>
            ))}
          </section>

          <div className="vrule-soft" />

          <section>
            <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:8 }}>
              <span className="mono" style={{ fontSize:18, fontWeight:700, color:"var(--accent)" }}>V.</span>
              <h2 className="h-section" style={{ margin:0 }}>Recent Data</h2>
            </div>
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

            <div style={{ marginTop:10 }}>
              <div className="kicker" style={{ fontSize:9, marginBottom:4 }}>Fiscal Impulse — pp of GDP</div>
              <BarChart width={310} height={110}
                data={S.fiscal.data} labels={S.fiscal.labels}
                accentIdx={S.fiscal.accent}
                padding={{l:30,r:6,t:8,b:16}} />
            </div>
          </section>
        </div>

        <hr className="rule" style={{ marginBottom:12 }} />

        {/* Section VI — Cross-Asset Heatmap */}
        <section style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:6 }}>
            <span className="mono" style={{ fontSize:18, fontWeight:700, color:"var(--accent)" }}>VI.</span>
            <h2 className="h-section" style={{ margin:0 }}>Cross-Asset Recap</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
            <span className="label">Total return, %</span>
          </div>
          <Heatmap rows={S.heatmap.rows} cols={S.heatmap.cols} values={S.heatmap.values}
                   width={618} height={170} />
        </section>

        {/* Footer */}
        <footer style={{ marginTop:10 }}>
          <hr className="rule-thick" style={{ marginBottom:4 }} />
          <div style={{ display:"flex", justifyContent:"space-between" }}>
            <span className="foot">Halford &amp; Reade · Macro Strategy</span>
            <span className="foot">Page 1 · Distribute Internally · See p.12</span>
          </div>
        </footer>
      </main>
    </div>
  );
}

window.VariationB = VariationB;
