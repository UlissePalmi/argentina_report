/* global React, BLOCKS, SAMPLE */

// =========================================================
// Page shell — running chrome + 12-col grid
// =========================================================

function PageHeader({ pageIdx, total, edition, eyebrow }) {
  const S = SAMPLE;
  const NS = { whiteSpace: "nowrap" };
  return (
    <header className="page-head">
      <div className="page-head-row">
        <div style={{ minWidth: 0 }}>
          <div className="eyebrow" style={NS}>{S.firm} · {S.desk}</div>
          <div className="sans" style={{ ...NS, fontSize:11, fontWeight:600, color:"var(--ink)", marginTop:2 }}>
            {edition || S.issue}
          </div>
        </div>
        <div style={{ textAlign:"right" }}>
          <div className="label" style={{ ...NS, fontSize:9 }}>{S.vol} · {S.date}</div>
          <div className="mono" style={{ ...NS, fontSize:10, color:"var(--ink-2)", marginTop:2 }}>
            {String(pageIdx+1).padStart(2,"0")} / {String(total).padStart(2,"0")}
          </div>
        </div>
      </div>
      <hr className="rule-double" style={{ margin:"6px 0 4px" }} />
      <div className="page-head-row" style={{ alignItems:"baseline" }}>
        <span className="kicker" style={NS}>{eyebrow || "Macro Quarterly · H2 2026"}</span>
        <span className="label" style={NS}>Buy-Side Only · Distribute Internally</span>
      </div>
    </header>
  );
}

function PageFooter({ pageIdx, total }) {
  const S = SAMPLE;
  const NS = { whiteSpace: "nowrap" };
  return (
    <footer className="page-foot">
      <hr className="rule-thick" style={{ marginBottom:6 }} />
      <div className="page-foot-row">
        <span className="foot" style={NS}>{S.firm} · Macro Strategy</span>
        <span className="foot" style={NS}>© 2026 · See disclosures, p. {String(total).padStart(2,"0")}</span>
        <span className="foot" style={NS}>— {String(pageIdx+1).padStart(2,"0")} —</span>
      </div>
    </footer>
  );
}

// One rendered block, with composer overlay if editing
function RenderedBlock({ block, pageIdx, blockIdx, isLast, editing, onMove, onRemove, onSpan }) {
  const def = BLOCKS[block.type];
  if (!def) {
    return (
      <div className="block" style={{ gridColumn:`span ${block.span || 12}`,
                                       background:"#ffe0d0", padding:8 }}>
        <span className="mono" style={{ fontSize:11, color:"var(--down)" }}>
          Unknown block: {block.type}
        </span>
      </div>
    );
  }
  const Component = def.component;
  const span = block.span || def.span || 12;
  const rows = block.rows;

  return (
    <div className={editing ? "block-wrap editing" : "block-wrap"}
         style={{
           gridColumn:`span ${span}`,
           gridRow: rows ? `span ${rows}` : "auto",
         }}>
      {editing && (
        <div className="block-toolbar">
          <span className="block-tag">{def.label} · {span}/12</span>
          <div className="block-toolbar-spacer" />
          <button className="block-btn" onClick={()=>onSpan(span - 1)} disabled={span<=2}
                  title="Narrower">−</button>
          <button className="block-btn" onClick={()=>onSpan(span + 1)} disabled={span>=12}
                  title="Wider">+</button>
          <button className="block-btn" onClick={()=>onMove(-1)} disabled={blockIdx===0}
                  title="Move up">↑</button>
          <button className="block-btn" onClick={()=>onMove(+1)} disabled={isLast}
                  title="Move down">↓</button>
          <button className="block-btn danger" onClick={onRemove} title="Remove">×</button>
        </div>
      )}
      <Component {...(block.props || {})} />
    </div>
  );
}

// One page — its header, grid of blocks, and footer
function PageView({ page, idx, total, editing, dispatch, onSelectPage, selected, tweaks }) {
  // Cover pages render the rich Variation A note in place of the block grid.
  if (page.kind === "cover") {
    return (
      <article className={selected ? "doc-page cover selected" : "doc-page cover"}
               data-page-id={page.id}
               style={{ padding: 0 }}
               onClick={() => onSelectPage(page.id)}>
        <VariationA tweaks={tweaks} />
        {editing && (
          <div className="page-edit-strip">
            <span className="mono" style={{ fontSize:10 }}>Page {String(idx+1).padStart(2,"0")} · Cover</span>
            <div style={{ display:"flex", gap:4 }}>
              <button className="block-btn" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"move-page", pageId:page.id, dir:-1 });}}
                      disabled={idx===0} title="Move page up">↑</button>
              <button className="block-btn" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"move-page", pageId:page.id, dir:+1 });}}
                      disabled={idx===total-1} title="Move page down">↓</button>
              <button className="block-btn" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"duplicate-page", pageId:page.id });}}
                      title="Duplicate page">⎘</button>
              <button className="block-btn danger" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"remove-page", pageId:page.id });}}
                      disabled={total<=1} title="Remove page">×</button>
            </div>
          </div>
        )}
      </article>
    );
  }

  return (
    <article className={selected ? "doc-page selected" : "doc-page"}
             data-page-id={page.id}
             onClick={() => onSelectPage(page.id)}>
      <PageHeader pageIdx={idx} total={total}
                  edition={page.edition} eyebrow={page.eyebrow} />

      <div className="page-grid">
        {page.blocks.map((b, i) => (
          <RenderedBlock key={b.id}
            block={b} pageIdx={idx} blockIdx={i}
            isLast={i === page.blocks.length - 1}
            editing={editing}
            onMove={(dir) => dispatch({ type:"move-block", pageId:page.id, blockId:b.id, dir })}
            onRemove={() => dispatch({ type:"remove-block", pageId:page.id, blockId:b.id })}
            onSpan={(s) => dispatch({ type:"set-span", pageId:page.id, blockId:b.id, span:s })}
          />
        ))}

        {editing && (
          <div className="block-wrap add-here" style={{ gridColumn:"span 12" }}>
            <button className="add-block-btn"
                    onClick={() => dispatch({ type:"open-library", forPage: page.id })}>
              <span className="plus">＋</span> Add block to page {String(idx+1).padStart(2,"0")}
            </button>
          </div>
        )}
      </div>

      <PageFooter pageIdx={idx} total={total} />

      {editing && (
        <div className="page-edit-strip">
          <span className="mono" style={{ fontSize:10 }}>Page {String(idx+1).padStart(2,"0")}</span>
          <div style={{ display:"flex", gap:4 }}>
            <button className="block-btn" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"move-page", pageId:page.id, dir:-1 });}}
                    disabled={idx===0} title="Move page up">↑</button>
            <button className="block-btn" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"move-page", pageId:page.id, dir:+1 });}}
                    disabled={idx===total-1} title="Move page down">↓</button>
            <button className="block-btn" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"duplicate-page", pageId:page.id });}}
                    title="Duplicate page">⎘</button>
            <button className="block-btn danger" onClick={(e)=>{e.stopPropagation(); dispatch({ type:"remove-page", pageId:page.id });}}
                    disabled={total<=1} title="Remove page">×</button>
          </div>
        </div>
      )}
    </article>
  );
}

window.PageView = PageView;
