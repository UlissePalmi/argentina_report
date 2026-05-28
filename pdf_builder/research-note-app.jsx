/* global React, ReactDOM, VariationA, DEFAULT_TWEAKS,
          TweaksPanel, useTweaks,
          TweakSection, TweakColor, TweakRadio, TweakSelect, TweakToggle */

// Each accent option is a [accent, accentDeep] pair stored as-is so the
// TweakColor swatch can compare arrays via JSON.stringify identity.
const ACCENT_OPTIONS = [
  ["#a23b1f", "#7d2a14"], // oxblood (default)
  ["#1f3a6b", "#13264a"], // ink navy
  ["#2f6b3a", "#1f4a26"], // bottle green
  ["#8a6a1f", "#5f4810"], // dark gold
  ["#2a2722", "#1a1714"], // charcoal mono
];

// Paper palettes: [paper, paperDeep, rule, ruleSoft]
const PAPER_OPTIONS = [
  ["#f4f0e6", "#ece6d4", "#c9bfae", "#ddd3c0"], // cream (default)
  ["#f9f6ee", "#f1ecdc", "#cdc3b1", "#e0d8c4"], // ivory
  ["#efe8d8", "#e6dec6", "#bcb09a", "#d4c9af"], // parchment
  ["#eeeae0", "#e3ddca", "#beb29c", "#d6cbb2"], // bone
  ["#eceae3", "#e1dcd0", "#b9b1a1", "#d2cab8"], // ash-cream
];

function App() {
  // EDITMODE-aware default tweaks (host can persist edits between sessions).
  const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
    "accent":   ["#a23b1f", "#7d2a14"],
    "paper":    ["#f4f0e6", "#ece6d4", "#c9bfae", "#ddd3c0"],
    "density":  "standard",
    "masthead": "classic",
    "showHero": true,
    "lower":    "risks-prints-fiscal"
  }/*EDITMODE-END*/;

  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [accent, accentDeep]                = t.accent;
  const [paper,  paperDeep, rule, ruleSoft] = t.paper;

  const resolvedTweaks = {
    ...DEFAULT_TWEAKS,
    accent, accentDeep, paper, paperDeep, rule, ruleSoft,
    density:  t.density,
    masthead: t.masthead,
    showHero: t.showHero,
    lower:    t.lower,
  };

  return (
    <React.Fragment>
      <div className="stage">
        <div className="sheet">
          <VariationA tweaks={resolvedTweaks} />
        </div>
        <div className="stage-foot">
          <span className="mono">Halford &amp; Reade · Macro Quarterly</span>
          <span className="mono">A working layout · pipeline-ready</span>
        </div>
      </div>

      <TweaksPanel title="Tweaks">
        <TweakSection label="Color">
          <TweakColor
            label="Accent"
            value={t.accent}
            options={ACCENT_OPTIONS}
            onChange={(v) => setTweak("accent", v)}
          />
          <TweakColor
            label="Paper"
            value={t.paper}
            options={PAPER_OPTIONS}
            onChange={(v) => setTweak("paper", v)}
          />
        </TweakSection>

        <TweakSection label="Layout">
          <TweakRadio
            label="Density"
            value={t.density}
            options={[
              { label:"Tight",  value:"compact"  },
              { label:"Std",    value:"standard" },
              { label:"Loose",  value:"loose"    },
            ]}
            onChange={(v) => setTweak("density", v)}
          />
          <TweakSelect
            label="Masthead"
            value={t.masthead}
            options={[
              { label:"Classic — italic nameplate", value:"classic"  },
              { label:"Engraved — small caps",      value:"engraved" },
              { label:"Modern — bold sans",         value:"modern"   },
            ]}
            onChange={(v) => setTweak("masthead", v)}
          />
          <TweakToggle
            label="Hero levels strip"
            value={t.showHero}
            onChange={(v) => setTweak("showHero", v)}
          />
          <TweakSelect
            label="Lower row"
            value={t.lower}
            options={[
              { label:"Risks · Prints · Fiscal",   value:"risks-prints-fiscal"  },
              { label:"Risks · Prints · Heatmap",  value:"risks-prints-heatmap" },
              { label:"Risks · Heatmap · Fiscal",  value:"risks-heatmap-fiscal" },
            ]}
            onChange={(v) => setTweak("lower", v)}
          />
        </TweakSection>
      </TweaksPanel>
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
