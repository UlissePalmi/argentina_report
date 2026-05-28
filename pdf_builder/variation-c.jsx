/* global React, Sparkline, Sparkbars, LineChart, ScenarioFan, BarChart, Heatmap, Timeline, SAMPLE */

// =========================================================
// VARIATION C — Editorial Single-Column with Marginalia
// Magazine spread feel: wide margins, drop cap, pull quote,
// marginal annotations carry the dense data
// =========================================================

function VariationC() {
  const S = SAMPLE;
  return (
    <div className="page" style={{ padding:"0", position:"relative", display:"flex", flexDirection:"column" }}>

      {/* === Top strap === */}
      <div style={{
        background: "var(--ink)", color: "var(--paper)",
        padding: "6px 36px",
        display:"flex", justifyContent:"space-between", alignItems:"center",
      }}>
        <div className="sans" style={{ fontSize:9, letterSpacing:"0.22em", textTransform:"uppercase", fontWeight:600 }}>
          {S.firm} · {S.desk}
        </div>
        <div className="mono" style={{ fontSize:10 }}>
          {S.vol} · {S.date} · {S.city}
        </div>
        <div className="sans" style={{ fontSize:9, letterSpacing:"0.22em", textTransform:"uppercase", color:"var(--accent-soft)", fontWeight:600 }}>
          Buy-Side Only
        </div>
      </div>

      {/* === Masthead === */}
      <header style={{ padding:"22px 36px 0", textAlign:"center" }}>
        <div className="kicker" style={{ fontSize:11 }}>Macro Quarterly · Mid-Cycle Edition</div>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:18, marginTop:8 }}>
          <hr className="rule-thick" style={{ flex:1, maxWidth:80, borderTopWidth:2 }} />
          <div className="serif" style={{ fontSize:13, letterSpacing:"0.32em", textTransform:"uppercase", fontWeight:600, color:"var(--ink-2)" }}>
            H · R
          </div>
          <hr className="rule-thick" style={{ flex:1, maxWidth:80, borderTopWidth:2 }} />
        </div>

        <h1 style={{
          fontFamily:"var(--serif)",
          fontWeight:700, fontStyle:"italic",
          fontSize:54, lineHeight:1.02, letterSpacing:"-0.015em",
          margin:"14px 0 6px",
          color:"var(--ink)",
        }}>
          {S.title}
        </h1>
        <p style={{
          fontFamily:"var(--serif)", fontStyle:"italic",
          fontSize:16, lineHeight:1.4, color:"var(--ink-2)",
          margin:"4px auto 0", maxWidth:"58ch",
        }}>
          {S.subtitle}
        </p>

        <div style={{ marginTop:12, display:"flex", justifyContent:"center", gap:10, alignItems:"center" }}>
          <span className="label">By</span>
          {S.authors.map((a,i)=>(
            <React.Fragment key={i}>
              <span className="smallcaps serif" style={{ fontSize:11, fontWeight:600 }}>{a.name}</span>
              {i<S.authors.length-1 && <span className="label" style={{ color:"var(--ink-4)" }}>·</span>}
            </React.Fragment>
          ))}
        </div>
      </header>

      {/* === Layout: marginalia | main column | marginalia === */}
      <div style={{
        display:"grid",
        gridTemplateColumns:"160px 1fr 160px",
        gap:18,
        padding:"22px 28px 0",
        flex:1,
      }}>

        {/* === LEFT MARGIN — micro data === */}
        <aside style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div>
            <div className="margin-note">
              <span className="lead-word">Levels</span>
            </div>
            {S.hero.map((m,i)=>(
              <div key={i} style={{
                padding:"4px 0",
                borderBottom: i<S.hero.length-1 ? "1px solid var(--rule-soft)" : "none",
              }}>
                <div className="sans" style={{ fontSize:9, color:"var(--ink-3)", letterSpacing:"0.08em" }}>{m.k}</div>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginTop:1 }}>
                  <span className="mono" style={{ fontSize:11, fontWeight:600 }}>{m.v}</span>
                  <span className="mono" style={{
                    fontSize:9,
                    color: m.d.startsWith("-") ? "var(--down)" : (m.d.startsWith("+") ? "var(--up)" : "var(--ink-3)")
                  }}>{m.d}</span>
                </div>
                <Sparkline data={m.spark} width={130} height={14} />
              </div>
            ))}
          </div>

          <div>
            <div className="margin-note">
              <span className="lead-word">House Calls</span>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
              {[
                ["Duration","Add","var(--accent)"],
                ["Equity β","Trim","var(--ink-2)"],
                ["Vol","Long",  "var(--accent)"],
                ["USD","Neutral","var(--ink-2)"],
                ["Credit","UW HY","var(--ink-2)"],
                ["EM","OW LatAm","var(--ink-2)"],
              ].map(([k,v,c],i)=>(
                <div key={i} style={{
                  display:"flex", justifyContent:"space-between",
                  borderBottom:"1px dotted var(--rule)",
                  padding:"3px 0",
                }}>
                  <span className="sans" style={{ fontSize:10, color:"var(--ink-2)" }}>{k}</span>
                  <span className="sans" style={{ fontSize:10, fontWeight:600, color:c }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* === MAIN COLUMN === */}
        <main>
          {/* Stamp + abstract */}
          <div style={{ display:"flex", justifyContent:"flex-end", marginBottom:8 }}>
            <span className="stamp">Note №241 · Buy-Side Only</span>
          </div>

          {/* Drop cap intro */}
          <div className="body-tight dropcap" style={{ fontSize:13.5, lineHeight:1.5, color:"var(--ink)" }}>
            <p>
              The disinflation narrative that propelled risk through 2025 is entering its
              least telegenic phase. Headline CPI has cleared the easy gains; what remains
              is a slow grind through shelter and core services where the Federal Reserve
              has the least leverage. We move <em>Base from Bull</em> across asset allocations
              and tilt into convexity over conviction.
            </p>
            <p>
              Our framework rests on four observations, each sized to a specific catalyst
              window and paired with a downside hedge we believe trades cheap relative to
              realized cross-asset volatility. The window for graceful rotation is open,
              but narrowing — Jackson Hole is our line in the sand.
            </p>
          </div>

          {/* Pull quote */}
          <blockquote style={{
            margin:"16px 0",
            padding:"14px 18px",
            borderTop: "2px solid var(--ink)",
            borderBottom: "2px solid var(--ink)",
            textAlign:"center",
          }}>
            <div className="kicker" style={{ marginBottom:6 }}>Bottom Line</div>
            <p className="pull" style={{ margin:0, fontSize:19 }}>
              <span className="mark">“</span>{S.bottomline}<span className="mark" style={{ marginLeft:2 }}>”</span>
            </p>
          </blockquote>

          {/* Executive summary heading */}
          <div style={{ display:"flex", alignItems:"baseline", gap:8, marginTop:14, marginBottom:8 }}>
            <span className="mono" style={{ fontSize:11, color:"var(--accent)", fontWeight:700 }}>§ I</span>
            <h2 className="h-section" style={{ margin:0, fontSize:20, fontStyle:"italic" }}>The Four Observations</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
          </div>

          {/* Numbered thesis */}
          <ol style={{ listStyle:"none", padding:0, margin:0 }}>
            {S.thesis.map((t,i)=>(
              <li key={i} style={{
                display:"grid",
                gridTemplateColumns:"38px 1fr",
                gap:10,
                padding:"9px 0",
                borderBottom: i<S.thesis.length-1 ? "1px solid var(--rule-soft)" : "none",
              }}>
                <div className="serif" style={{
                  fontSize:30, fontWeight:700, fontStyle:"italic",
                  color:"var(--accent)", lineHeight:0.9, textAlign:"right",
                }}>
                  {i+1}
                </div>
                <div className="body-tight" style={{ fontSize:12, margin:0, color:"var(--ink-2)" }}>{t}</div>
              </li>
            ))}
          </ol>

          {/* Scenario heading */}
          <div style={{ display:"flex", alignItems:"baseline", gap:8, marginTop:18, marginBottom:8 }}>
            <span className="mono" style={{ fontSize:11, color:"var(--accent)", fontWeight:700 }}>§ II</span>
            <h2 className="h-section" style={{ margin:0, fontSize:20, fontStyle:"italic" }}>Three Paths Through Year-End</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
          </div>

          {/* Scenario fan — full main column width */}
          <ScenarioFan width={440} height={170}
            bear={S.proj.bear} base={S.proj.base} bull={S.proj.bull}
            xLabels={S.proj.xLabels} pivot={0}
            yLabel="10Y UST · projected, % " />

          {/* Scenario table — compact */}
          <table className="data" style={{ marginTop:10 }}>
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

          {/* Catalysts heading */}
          <div style={{ display:"flex", alignItems:"baseline", gap:8, marginTop:18, marginBottom:6 }}>
            <span className="mono" style={{ fontSize:11, color:"var(--accent)", fontWeight:700 }}>§ III</span>
            <h2 className="h-section" style={{ margin:0, fontSize:20, fontStyle:"italic" }}>Catalysts</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
          </div>
          <Timeline events={S.catalysts} width={440} height={72} />

          {/* Risks heading */}
          <div style={{ display:"flex", alignItems:"baseline", gap:8, marginTop:18, marginBottom:8 }}>
            <span className="mono" style={{ fontSize:11, color:"var(--accent)", fontWeight:700 }}>§ IV</span>
            <h2 className="h-section" style={{ margin:0, fontSize:20, fontStyle:"italic" }}>Risks</h2>
            <hr className="rule-thin" style={{ flex:1, alignSelf:"center" }} />
          </div>

          {/* Risks compact */}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"6px 18px" }}>
            {S.risks.map((r,i)=>(
              <div key={i} style={{ borderTop:"1px solid var(--rule-soft)", paddingTop:5, paddingBottom:5 }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}>
                  <span className="label label-accent">{r.tag}</span>
                  <span className="mono" style={{ fontSize:9, color:"var(--ink-3)" }}>
                    {"●".repeat(r.sev)}{"○".repeat(5-r.sev)}
                  </span>
                </div>
                <div className="serif" style={{ fontWeight:700, fontSize:11.5, fontStyle:"italic", margin:"2px 0" }}>{r.title}</div>
                <div className="body-tight" style={{ fontSize:10.5 }}>{r.body}</div>
              </div>
            ))}
          </div>
        </main>

        {/* === RIGHT MARGIN — annotations === */}
        <aside style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div className="margin-note">
            <span className="lead-word">Editor’s Note</span>
            This issue reflects a meaningful change in house view: we step back from the
            Bull case dominant since November and adopt a Base posture with explicit
            optionality on both tails.
          </div>

          <div className="margin-note" style={{ borderTop:"1px solid var(--rule)", paddingTop:10 }}>
            <span className="lead-word">CPI YoY — 24m</span>
            <LineChart width={140} height={72}
              series={[{ data:S.cpiPath.data, color:"var(--ink)" }]}
              padding={{l:20,r:4,t:6,b:14}}
              xTicks={3} yTicks={3} />
            <div className="sans" style={{ fontSize:9, marginTop:4, color:"var(--ink-3)" }}>
              Disinflation slope has flattened; last mile begins H2.
            </div>
          </div>

          <div className="margin-note" style={{ borderTop:"1px solid var(--rule)", paddingTop:10 }}>
            <span className="lead-word">Fiscal Impulse</span>
            <BarChart width={140} height={80}
              data={S.fiscal.data} labels={S.fiscal.labels}
              accentIdx={S.fiscal.accent}
              padding={{l:18,r:2,t:4,b:12}} />
            <div className="sans" style={{ fontSize:9, marginTop:4, color:"var(--ink-3)" }}>
              Drag begins Q3’26; peaks Q1’27 at −0.6pp.
            </div>
          </div>

          <div className="margin-note" style={{ borderTop:"1px solid var(--rule)", paddingTop:10 }}>
            <span className="lead-word">Recent Tape</span>
            <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
              {S.prints.slice(0,5).map((p,i)=>(
                <div key={i} style={{ display:"flex", justifyContent:"space-between", padding:"2px 0", borderBottom:"1px dotted var(--rule)" }}>
                  <div>
                    <div className="mono" style={{ fontSize:8.5, color:"var(--ink-3)" }}>{p.date}</div>
                    <div className="sans" style={{ fontSize:9, fontWeight: p.accent ? 600 : 400, color:"var(--ink)" }}>{p.label.split(",")[0]}</div>
                  </div>
                  <div style={{ textAlign:"right" }}>
                    <div className="mono" style={{ fontSize:9.5, fontWeight:600 }}>{p.actual}</div>
                    <div className="mono" style={{
                      fontSize:8.5,
                      color: p.surprise>0.5 ? "var(--up)" : (p.surprise<-0.5 ? "var(--down)" : "var(--ink-3)")
                    }}>{p.surprise>0?"+":""}{p.surprise.toFixed(1)}σ</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="margin-note" style={{ borderTop:"1px solid var(--rule)", paddingTop:10 }}>
            <span className="lead-word">Distribution</span>
            <div className="sans" style={{ fontSize:9 }}>
              Macro Strategy ·<br/>research@halfordreade.co<br/>+44 20 7946 0218
            </div>
          </div>
        </aside>
      </div>

      {/* === Footer === */}
      <footer style={{
        borderTop:"3px double var(--ink)",
        margin:"16px 28px 18px",
        padding:"8px 0 0",
        display:"flex", justifyContent:"space-between", alignItems:"center",
      }}>
        <div className="foot">{S.firm} · Macro Quarterly · {S.vol}</div>
        <div className="serif" style={{ fontStyle:"italic", fontSize:10, color:"var(--ink-3)" }}>
          continued — p. 02
        </div>
        <div className="foot">© 2026 · See disclosures, p. 12</div>
      </footer>
    </div>
  );
}

window.VariationC = VariationC;
