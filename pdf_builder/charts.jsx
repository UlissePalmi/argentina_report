/* global React */
/* Charts & micro-data components — all SVG, all placeholder-aware */

const INK    = "#1a1714";
const INK2   = "#3a3530";
const INK3   = "#6b625a";
const RULE   = "#c9bfae";
const RULES  = "#ddd3c0";
const ACCENT = "#a23b1f";
const UP     = "#2f6b3a";
const DOWN   = "#a23b1f";

// --- helpers ---
function pathFromPoints(pts) {
  return pts.map((p,i)=>`${i?"L":"M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
}
function scale(arr, lo, hi, outLo, outHi) {
  return arr.map(v => outLo + ((v-lo)/(hi-lo))*(outHi-outLo));
}

// =========================================================
// Sparkline — for inline use in tables / kickers
// =========================================================
function Sparkline({ data, width=70, height=18, stroke=INK, accent=false, fill=false }) {
  const min = Math.min(...data), max = Math.max(...data);
  const xs = data.map((_,i)=> (i/(data.length-1)) * (width-2) + 1);
  const ys = data.map(v => height - 1 - ((v-min)/(max-min || 1)) * (height-2));
  const pts = xs.map((x,i)=>[x,ys[i]]);
  const last = data[data.length-1] >= data[0];
  const color = accent ? ACCENT : (last ? UP : DOWN);
  return (
    <svg width={width} height={height} style={{ verticalAlign:"middle" }}>
      {fill && (
        <path d={`${pathFromPoints(pts)} L${xs[xs.length-1]} ${height} L${xs[0]} ${height} Z`}
              fill={color} fillOpacity="0.12" stroke="none" />
      )}
      <path d={pathFromPoints(pts)} fill="none" stroke={color} strokeWidth="1.2" />
      <circle cx={xs[xs.length-1]} cy={ys[ys.length-1]} r="1.6" fill={color} />
    </svg>
  );
}

// =========================================================
// Sparkbars — for inline magnitude
// =========================================================
function Sparkbars({ data, width=70, height=18, color=INK2 }) {
  const max = Math.max(...data.map(Math.abs));
  const bw = (width - data.length) / data.length;
  return (
    <svg width={width} height={height} style={{ verticalAlign:"middle" }}>
      <line x1="0" x2={width} y1={height/2} y2={height/2} stroke={RULES} strokeWidth="0.5" />
      {data.map((v,i)=>{
        const h = (Math.abs(v)/max) * (height/2 - 1);
        const y = v >= 0 ? (height/2 - h) : height/2;
        return <rect key={i} x={i*(bw+1)} y={y} width={bw} height={h}
                     fill={v>=0 ? UP : DOWN} fillOpacity="0.85" />;
      })}
    </svg>
  );
}

// =========================================================
// Big line chart — index / yield path
// =========================================================
function LineChart({ width=400, height=170, series, yTicks=4, xTicks=6, accent=false,
                    yLabel="", padding={l:32,r:8,t:12,b:18} }) {
  const {l,r,t,b} = padding;
  const W = width - l - r, H = height - t - b;
  const all = series.flatMap(s => s.data);
  const min = Math.min(...all), max = Math.max(...all);
  const range = max - min || 1;
  const lo = min - range*0.05, hi = max + range*0.05;
  const len = series[0].data.length;
  const xs = Array.from({length: len}, (_,i)=> l + (i/(len-1))*W);
  const yScale = v => t + (1 - (v-lo)/(hi-lo)) * H;

  // grid
  const grid = [];
  for (let i=0; i<=yTicks; i++) {
    const v = lo + (i/yTicks)*(hi-lo);
    const y = yScale(v);
    grid.push(<g key={"y"+i}>
      <line x1={l} x2={l+W} y1={y} y2={y} stroke={RULES} strokeWidth="0.5" />
      <text x={l-4} y={y+3} fontSize="8.5" textAnchor="end" fill={INK3}
            fontFamily="IBM Plex Mono, monospace">{v.toFixed(v>100?0:1)}</text>
    </g>);
  }
  // x ticks - generic labels
  const xLabels = series[0].xLabels || Array.from({length:len},(_,i)=>String(i));
  const step = Math.max(1, Math.floor(len/xTicks));
  for (let i=0; i<len; i+=step) {
    grid.push(<text key={"x"+i} x={xs[i]} y={t+H+12} fontSize="8.5" textAnchor="middle"
                    fill={INK3} fontFamily="IBM Plex Mono, monospace">{xLabels[i]}</text>);
  }

  return (
    <svg width={width} height={height} style={{ display:"block" }}>
      <rect x={l} y={t} width={W} height={H} fill="none" stroke={INK} strokeWidth="0.8" />
      {grid}
      {series.map((s, idx) => {
        const pts = s.data.map((v,i)=>[xs[i], yScale(v)]);
        const color = s.color || (accent ? ACCENT : (idx===0 ? INK : INK3));
        return (
          <g key={idx}>
            {s.fill && (
              <path d={`${pathFromPoints(pts)} L${xs[xs.length-1]} ${t+H} L${xs[0]} ${t+H} Z`}
                    fill={color} fillOpacity="0.10" stroke="none" />
            )}
            <path d={pathFromPoints(pts)} fill="none" stroke={color}
                  strokeWidth={s.weight || 1.4}
                  strokeDasharray={s.dash || "none"} />
          </g>
        );
      })}
      {yLabel && <text x={l} y={t-4} fontSize="8.5" fill={INK3}
                       fontFamily="IBM Plex Sans, sans-serif"
                       letterSpacing="0.1em">{yLabel.toUpperCase()}</text>}
    </svg>
  );
}

// =========================================================
// Scenario fan — bear / base / bull projection
// =========================================================
function ScenarioFan({ width=400, height=180, bear, base, bull, xLabels, yLabel="",
                      pivot=0, padding={l:34,r:10,t:12,b:20} }) {
  const {l,r,t,b} = padding;
  const W = width-l-r, H = height-t-b;
  const all = [...bear, ...base, ...bull];
  const min = Math.min(...all), max = Math.max(...all);
  const range = max-min || 1, lo = min-range*0.08, hi = max+range*0.08;
  const len = base.length;
  const xs = Array.from({length:len},(_,i)=> l + (i/(len-1))*W);
  const ys = v => t + (1 - (v-lo)/(hi-lo)) * H;

  const bearP = bear.map((v,i)=>[xs[i], ys(v)]);
  const bullP = bull.map((v,i)=>[xs[i], ys(v)]);
  const baseP = base.map((v,i)=>[xs[i], ys(v)]);
  const fanD = `${pathFromPoints(bullP)} L${xs[len-1]} ${ys(bear[len-1])} ` +
               bear.slice().reverse().map((v,i)=>{
                 const ix = len-1-i;
                 return `L${xs[ix]} ${ys(v)}`;
               }).join(" ") + " Z";

  // ticks
  const ticks = [];
  for (let i=0;i<=4;i++){
    const v = lo + (i/4)*(hi-lo);
    const y = ys(v);
    ticks.push(<g key={i}>
      <line x1={l} x2={l+W} y1={y} y2={y} stroke={RULES} strokeWidth="0.5" />
      <text x={l-4} y={y+3} fontSize="8.5" textAnchor="end" fill={INK3}
            fontFamily="IBM Plex Mono, monospace">{v.toFixed(1)}</text>
    </g>);
  }
  // pivot line (today)
  const pivotX = xs[pivot];

  return (
    <svg width={width} height={height} style={{ display:"block" }}>
      <rect x={l} y={t} width={W} height={H} fill="none" stroke={INK} strokeWidth="0.8" />
      {ticks}
      <path d={fanD} fill={ACCENT} fillOpacity="0.10" stroke="none" />
      <path d={pathFromPoints(bullP)} fill="none" stroke={ACCENT}
            strokeWidth="0.9" strokeDasharray="2,2" />
      <path d={pathFromPoints(bearP)} fill="none" stroke={ACCENT}
            strokeWidth="0.9" strokeDasharray="2,2" />
      <path d={pathFromPoints(baseP)} fill="none" stroke={INK} strokeWidth="1.5" />
      {/* pivot */}
      <line x1={pivotX} x2={pivotX} y1={t} y2={t+H} stroke={INK3}
            strokeWidth="0.5" strokeDasharray="1,2" />
      {/* endpoint labels */}
      <g fontFamily="IBM Plex Mono, monospace" fontSize="8.5" fill={INK}>
        <text x={xs[len-1]+3} y={ys(bull[len-1])+3} fill={ACCENT}>Bull {bull[len-1].toFixed(1)}</text>
        <text x={xs[len-1]+3} y={ys(base[len-1])+3}>Base {base[len-1].toFixed(1)}</text>
        <text x={xs[len-1]+3} y={ys(bear[len-1])+3} fill={ACCENT}>Bear {bear[len-1].toFixed(1)}</text>
      </g>
      {/* x labels */}
      {xLabels && xLabels.map((lab,i)=> i%2===0 && (
        <text key={i} x={xs[i]} y={t+H+12} fontSize="8.5" textAnchor="middle"
              fill={INK3} fontFamily="IBM Plex Mono, monospace">{lab}</text>
      ))}
      {yLabel && <text x={l} y={t-4} fontSize="8.5" fill={INK3}
                       fontFamily="IBM Plex Sans, sans-serif"
                       letterSpacing="0.1em">{yLabel.toUpperCase()}</text>}
    </svg>
  );
}

// =========================================================
// Bar chart — horizontal or vertical
// =========================================================
function BarChart({ width=300, height=140, data, labels, accentIdx,
                   padding={l:36,r:8,t:10,b:18}, signed=true }) {
  const {l,r,t,b} = padding;
  const W = width-l-r, H = height-t-b;
  const max = Math.max(...data.map(Math.abs));
  const lo = signed ? -max*1.1 : 0;
  const hi = max*1.1;
  const ys = v => t + (1 - (v-lo)/(hi-lo)) * H;
  const zero = ys(0);
  const bw = W / data.length - 4;

  return (
    <svg width={width} height={height} style={{ display:"block" }}>
      <rect x={l} y={t} width={W} height={H} fill="none" stroke={INK} strokeWidth="0.8" />
      <line x1={l} x2={l+W} y1={zero} y2={zero} stroke={INK} strokeWidth="0.7" />
      {data.map((v,i)=>{
        const x = l + i*(W/data.length) + 2;
        const y = v >= 0 ? ys(v) : zero;
        const h = Math.abs(ys(v) - zero);
        const isAccent = accentIdx && accentIdx.includes(i);
        return (
          <g key={i}>
            <rect x={x} y={y} width={bw} height={h}
                  fill={isAccent ? ACCENT : (v>=0 ? INK : INK3)} />
            <text x={x+bw/2} y={t+H+12} fontSize="8" textAnchor="middle"
                  fill={INK3} fontFamily="IBM Plex Sans, sans-serif">{labels[i]}</text>
            <text x={x+bw/2} y={v>=0 ? y-3 : y+h+9} fontSize="8" textAnchor="middle"
                  fill={INK} fontFamily="IBM Plex Mono, monospace">{v>0?"+":""}{v.toFixed(1)}</text>
          </g>
        );
      })}
      {/* y ticks */}
      {[lo, 0, hi].map((v,i)=>(
        <text key={i} x={l-4} y={ys(v)+3} fontSize="8.5" textAnchor="end"
              fill={INK3} fontFamily="IBM Plex Mono, monospace">{v.toFixed(1)}</text>
      ))}
    </svg>
  );
}

// =========================================================
// Heatmap — cross-asset returns grid
// =========================================================
function Heatmap({ rows, cols, values, width=300, height=140 }) {
  const labelW = 60, headerH = 22;
  const cellW = (width - labelW) / cols.length;
  const cellH = (height - headerH) / rows.length;
  const flat = values.flat();
  const max = Math.max(...flat.map(Math.abs));
  return (
    <svg width={width} height={height} style={{ display:"block" }}>
      {cols.map((c,j)=>(
        <text key={j} x={labelW + j*cellW + cellW/2} y={14}
              fontSize="8.5" textAnchor="middle" fill={INK3}
              fontFamily="IBM Plex Sans, sans-serif" letterSpacing="0.08em">{c}</text>
      ))}
      {rows.map((r,i)=>(
        <text key={i} x={labelW-4} y={headerH + i*cellH + cellH/2 + 3}
              fontSize="9" textAnchor="end" fill={INK}
              fontFamily="IBM Plex Sans, sans-serif">{r}</text>
      ))}
      {rows.map((r,i)=> cols.map((c,j)=>{
        const v = values[i][j];
        const intensity = Math.abs(v)/max;
        const color = v>=0 ? `rgba(47,107,58,${intensity*0.65})` : `rgba(162,59,31,${intensity*0.7})`;
        return (
          <g key={`${i}-${j}`}>
            <rect x={labelW + j*cellW} y={headerH + i*cellH}
                  width={cellW-1} height={cellH-1} fill={color} stroke={RULES} strokeWidth="0.4" />
            <text x={labelW + j*cellW + cellW/2}
                  y={headerH + i*cellH + cellH/2 + 3}
                  fontSize="8.5" textAnchor="middle"
                  fill={intensity>0.5 ? "#f4f0e6" : INK}
                  fontFamily="IBM Plex Mono, monospace">
              {v>0?"+":""}{v.toFixed(1)}
            </text>
          </g>
        );
      }))}
    </svg>
  );
}

// =========================================================
// Timeline — catalyst calendar
// =========================================================
function Timeline({ events, width=560, height=72 }) {
  // Generous L/R padding so end-anchored labels aren't clipped.
  const padL = 40, padR = 40;
  const W = width - padL - padR;
  const y = 40;
  return (
    <svg width={width} height={height} style={{ display:"block", overflow:"visible" }}>
      <line x1={padL} x2={width-padR} y1={y} y2={y} stroke={INK} strokeWidth="1" />
      {events.map((e,i)=>{
        const x = padL + (i/(events.length-1)) * W;
        const above = i % 2 === 0;
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={y-4} y2={y+4} stroke={INK} strokeWidth="1" />
            <circle cx={x} cy={y} r="3" fill={e.accent ? ACCENT : INK} />
            <text x={x} y={above ? y-12 : y+24} fontSize="9"
                  textAnchor="middle" fill={INK}
                  fontFamily="IBM Plex Mono, monospace" letterSpacing="0.04em">{e.date}</text>
            <text x={x} y={above ? y-22 : y+34} fontSize="9.5"
                  textAnchor="middle" fill={e.accent ? ACCENT : INK2}
                  fontFamily="IBM Plex Sans, sans-serif" fontWeight={e.accent?700:500}>
              {e.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// Expose globally for other Babel scripts
Object.assign(window, {
  Sparkline, Sparkbars, LineChart, ScenarioFan, BarChart, Heatmap, Timeline,
});
