/* global React, ReactDOM, BLOCKS, INITIAL_DOC, uid, PageView, SAMPLE,
          VariationA, DEFAULT_TWEAKS,
          TweaksPanel, useTweaks,
          TweakSection, TweakColor, TweakRadio, TweakSelect, TweakToggle */

// =========================================================
// Document state: reducer + helpers
// =========================================================
function docReducer(state, action) {
  const pages = state.pages.map(p => ({ ...p, blocks: [...p.blocks] }));
  const pageIdx = (pid) => pages.findIndex(p => p.id === pid);
  const blockIdx = (page, bid) => page.blocks.findIndex(b => b.id === bid);

  switch (action.type) {
    case "remove-block": {
      const p = pages[pageIdx(action.pageId)];
      p.blocks = p.blocks.filter(b => b.id !== action.blockId);
      return { ...state, pages };
    }
    case "move-block": {
      const p = pages[pageIdx(action.pageId)];
      const i = blockIdx(p, action.blockId);
      const j = i + action.dir;
      if (j < 0 || j >= p.blocks.length) return state;
      [p.blocks[i], p.blocks[j]] = [p.blocks[j], p.blocks[i]];
      return { ...state, pages };
    }
    case "set-span": {
      const p = pages[pageIdx(action.pageId)];
      const b = p.blocks[blockIdx(p, action.blockId)];
      b.span = Math.max(2, Math.min(12, action.span));
      return { ...state, pages };
    }
    case "add-block": {
      const p = pages[pageIdx(action.pageId)];
      const def = BLOCKS[action.blockType];
      if (!def) return state;
      p.blocks.push({ id: uid(), type: action.blockType, span: def.span });
      return { ...state, pages };
    }
    case "move-page": {
      const i = pageIdx(action.pageId);
      const j = i + action.dir;
      if (j < 0 || j >= pages.length) return state;
      [pages[i], pages[j]] = [pages[j], pages[i]];
      return { ...state, pages };
    }
    case "remove-page": {
      if (pages.length <= 1) return state;
      return { ...state, pages: pages.filter(p => p.id !== action.pageId) };
    }
    case "duplicate-page": {
      const i = pageIdx(action.pageId);
      const src = pages[i];
      const copy = {
        ...src,
        id: uid(),
        blocks: src.blocks.map(b => ({ ...b, id: uid() })),
      };
      pages.splice(i + 1, 0, copy);
      return { ...state, pages };
    }
    case "add-page": {
      pages.push({
        id: uid(),
        eyebrow: "New Page",
        blocks: [],
      });
      return { ...state, pages };
    }
    default:
      return state;
  }
}

// =========================================================
// Library palette — floating block picker
// =========================================================
function LibraryPanel({ targetPageNumber, onAdd, onClose }) {
  const groups = React.useMemo(() => {
    const out = {};
    Object.entries(BLOCKS).forEach(([type, def]) => {
      const g = def.group || "Other";
      (out[g] ||= []).push({ type, ...def });
    });
    return out;
  }, []);
  const order = ["Heading", "Data", "Charts", "Structure", "Other"];

  return (
    <div className="lib-panel">
      <button className="lib-close" onClick={onClose} title="Close">×</button>
      <h4>Block Library</h4>
      <div className="lib-sub">Click to add</div>
      {targetPageNumber != null && (
        <div className="lib-target">
          Adds to <b>Page {String(targetPageNumber).padStart(2,"0")}</b>
        </div>
      )}
      {order.filter(g => groups[g]).map(g => (
        <div key={g} className="lib-group">
          <div className="lib-group-label">{g}</div>
          {groups[g].map(item => (
            <button key={item.type} className="lib-item"
                    onClick={() => onAdd(item.type)}>
              <span>{item.label}</span>
              <span className="lib-item-span">{item.span}/12</span>
            </button>
          ))}
        </div>
      ))}
      <div className="lib-hint">
        Blocks land at the end of the target page. Use ↑↓ on each block to reorder,
        or +/− to change its column span.
      </div>
    </div>
  );
}

// =========================================================
// Theme — same curated palettes as the single-page view
// =========================================================
const ACCENT_OPTIONS = [
  ["#a23b1f", "#7d2a14"],
  ["#1f3a6b", "#13264a"],
  ["#2f6b3a", "#1f4a26"],
  ["#8a6a1f", "#5f4810"],
  ["#2a2722", "#1a1714"],
];
const PAPER_OPTIONS = [
  ["#f4f0e6", "#ece6d4", "#c9bfae", "#ddd3c0"],
  ["#f9f6ee", "#f1ecdc", "#cdc3b1", "#e0d8c4"],
  ["#efe8d8", "#e6dec6", "#bcb09a", "#d4c9af"],
  ["#eeeae0", "#e3ddca", "#beb29c", "#d6cbb2"],
  ["#eceae3", "#e1dcd0", "#b9b1a1", "#d2cab8"],
];

// =========================================================
// App
// =========================================================
function App() {
  // Theme (persisted via host)
  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "accent":   ["#a23b1f", "#7d2a14"],
    "paper":    ["#f4f0e6", "#ece6d4", "#c9bfae", "#ddd3c0"],
    "density":  "standard"
  }/*EDITMODE-END*/;
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [accent, accentDeep]                = t.accent;
  const [paper,  paperDeep, rule, ruleSoft] = t.paper;

  // Document (in-page state — not persisted to disk).
  const [doc, dispatch] = React.useReducer(docReducer, INITIAL_DOC);

  // Composer mode
  const [editing, setEditing] = React.useState(false);

  // Library palette (visible + target page)
  const [library, setLibrary] = React.useState({ open: false, targetPageId: null });

  // Selected page (last clicked) — also the default target for library adds
  const [selectedPageId, setSelectedPageId] = React.useState(doc.pages[0].id);

  // Augmented dispatch that also handles open-library
  const handle = React.useCallback((action) => {
    if (action.type === "open-library") {
      setLibrary({ open: true, targetPageId: action.forPage });
      setSelectedPageId(action.forPage);
      return;
    }
    dispatch(action);
  }, []);

  const targetPageId = library.targetPageId || selectedPageId;
  const targetPage = doc.pages.find(p => p.id === targetPageId);
  const targetPageNumber = targetPage ? doc.pages.indexOf(targetPage) + 1 : 1;

  // Apply theme as CSS variables to a wrapper div
  const themeStyle = {
    "--accent":      accent,
    "--accent-deep": accentDeep,
    "--paper":       paper,
    "--paper-deep":  paperDeep,
    "--rule":        rule,
    "--rule-soft":   ruleSoft,
  };

  // Resolved tweaks for VariationA (used by cover pages)
  const coverTweaks = {
    ...DEFAULT_TWEAKS,
    accent, accentDeep, paper, paperDeep, rule, ruleSoft,
  };

  return (
    <React.Fragment>
      <div className="doc-stage" style={themeStyle}>
        <div className="doc-toolbar">
          <span className="doc-title">{doc.meta.title}</span>
          <span className="doc-sub">{doc.pages.length} pages · {doc.meta.date}</span>
        </div>

        {doc.pages.map((page, idx) => (
          <PageView key={page.id}
            page={page} idx={idx} total={doc.pages.length}
            editing={editing}
            dispatch={handle}
            onSelectPage={setSelectedPageId}
            selected={editing && page.id === selectedPageId}
            tweaks={coverTweaks}
          />
        ))}

        {editing && (
          <button className="add-page-btn"
                  onClick={() => dispatch({ type:"add-page" })}>
            ＋ Add page
          </button>
        )}
      </div>

      {/* Top-right toolbar: edit toggle + library toggle */}
      <div className="doc-mode-toolbar">
        <button className={editing ? "on" : ""}
                onClick={() => setEditing(v => !v)}>
          {editing ? "Editing: On" : "Edit Document"}
        </button>
        {editing && (
          <button className={library.open ? "on" : ""}
                  onClick={() => setLibrary(l => ({ open: !l.open, targetPageId: selectedPageId }))}>
            Library
          </button>
        )}
      </div>

      {editing && library.open && (
        <LibraryPanel
          targetPageNumber={targetPageNumber}
          onAdd={(type) => handle({ type:"add-block", pageId: targetPageId, blockType: type })}
          onClose={() => setLibrary(l => ({ ...l, open: false }))}
        />
      )}

      {/* Theme tweaks live in the host's Tweaks panel toggle */}
      <TweaksPanel title="Tweaks">
        <TweakSection label="Theme">
          <TweakColor label="Accent" value={t.accent} options={ACCENT_OPTIONS}
                      onChange={(v) => setTweak("accent", v)} />
          <TweakColor label="Paper"  value={t.paper}  options={PAPER_OPTIONS}
                      onChange={(v) => setTweak("paper", v)} />
        </TweakSection>
      </TweaksPanel>
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
