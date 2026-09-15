// Cache-busting build token — bump alongside index.html's ?v= query string
// whenever app.js or the data files change.
const BUILD = "2026-09-15c";

const CODED_COLS = ["study_design", "type_of_analysis", "data_type", "data_source",
  "unit_of_observation", "geo_scope", "era"];

// HTML-escapes a string for HTML sinks. Plotly renders hover `text` and
// hovertemplate output as HTML, so every data-derived string concatenated into
// hover text must pass through esc() first.
export function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// R-compatible round(x, digits) — half-to-even resolved on the EXACT binary
// value of the double, matching R >= 4.0.0 (DATA_CONTRACT.md §12). x is
// decomposed exactly into sign * m * 2^e from its IEEE-754 bits; |x| * 10^d is
// kept as the exact BigInt rational num/den; the half-to-even integer
// q = round(num/den) is computed with no floating-point error at all; the
// result is the correctly-rounded double q / 10^d.
// Proofs (verified against R 4.4.1): round(2.675, 2) = 2.67 (the stored double
// is BELOW the midpoint), round(0.125, 2) = 0.12 (exact in binary, tie -> even),
// round(0.135, 2) = 0.14 (the stored double is ABOVE the midpoint).
export function rRound(x, digits = 0) {
  if (x == null || !isFinite(x)) return x;
  if (x === 0) return x;
  const d = Math.trunc(digits);

  const dv = new DataView(new ArrayBuffer(8));
  dv.setFloat64(0, x);
  const hi = dv.getUint32(0), lo = dv.getUint32(4);
  const negative = (hi >>> 31) === 1;
  const biasedExp = (hi >>> 20) & 0x7ff;
  const frac = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo >>> 0);
  let m, e;
  if (biasedExp === 0) {
    m = frac; e = -1074;                                  // subnormal
  } else {
    m = (1n << 52n) | frac; e = biasedExp - 1023 - 52;    // normal: |x| = m * 2^e
  }

  // num/den = |x| * 10^d, exact
  let num = m, den = 1n;
  if (d >= 0) num *= 10n ** BigInt(d); else den *= 10n ** BigInt(-d);
  if (e >= 0) num *= 2n ** BigInt(e); else den *= 2n ** BigInt(-e);

  // half-to-even quotient
  let q = num / den;
  const twice = (num % den) * 2n;
  if (twice > den || (twice === den && q % 2n === 1n)) q += 1n;
  if (negative) q = -q;

  return Number(q) / Math.pow(10, d);
}

export function fmtNum(x) {
  if (x == null) return "";
  return Number(x).toLocaleString("en-US");
}

function num(v) {
  return (typeof v === "number" && isFinite(v)) ? v : null;
}

function ratio(n, d) {
  const dd = num(d);
  return (dd != null && dd > 0) ? n / dd : null;
}

function sortedYearObj(map) {
  const out = {};
  for (const y of [...map.keys()].sort((a, b) => a - b)) out[y] = map.get(y);
  return out;
}

// Builds the ordered label→column registries (DATA_CONTRACT.md §15.6) from
// content.json. Map preserves insertion order, so selector/legend order is the
// content.json array order. Replaces the previously hardcoded TREND_VARS /
// COMP_VARS / STACK_VARS / MAP_METRICS / SCAT_X / SCAT_Y / SIGNAL_METRICS.
export function buildRegistries(content) {
  if (!content || !content.registries) {
    throw new Error("buildRegistries: content.json with .registries is required");
  }
  const r = content.registries;
  const toMap = arr => new Map(arr.map(o => [o.label, o.column]));
  return {
    TREND_VARS: toMap(r.trend_vars),
    COMP_VARS: toMap(r.comp_vars),
    STACK_VARS: toMap(r.stack_vars),
    MAP_METRICS: toMap(r.map_metrics),
    SCAT_X: toMap(r.scat_x),
    SCAT_Y: toMap(r.scat_y),
    SIGNAL_METRICS: r.signal_metrics.slice()
  };
}

export function loadData({ dict, studies, geo, func, outcome, countries, content }) {
  const levels = dict.levels;
  const codeOf = {};
  for (const col of CODED_COLS) {
    codeOf[col] = new Map(levels[col].map((lab, i) => [lab, i]));
  }
  const pal = dict.meta.pal_inc;
  const palInc = {};
  if (Array.isArray(pal)) dict.meta.inc_lv.forEach((lv, i) => { palInc[lv] = pal[i]; });
  else Object.assign(palInc, pal);
  const functionSets = dict.financing_function_grps.map(() => new Set());
  for (let i = 0; i < func.s.length; i++) functionSets[func.g[i]].add(func.s[i]);
  const outcomeSets = dict.outcome_domain_grps.map(() => new Set());
  for (let i = 0; i < outcome.s.length; i++) outcomeSets[outcome.g[i]].add(outcome.s[i]);
  return {
    dict, levels, studies, geo, function: func, outcome, countries,
    content,
    registries: buildRegistries(content),
    nStudies: studies.id.length,
    codeOf,
    palInc,
    incLv: dict.meta.inc_lv.slice(),
    incOrder: dict.meta.inc_lv.slice().reverse(),
    incomeOf: countries.map(r => r.income),
    regionOf: countries.map(r => r.un_region),
    function_grps: dict.financing_function_grps,
    outcome_grps: dict.outcome_domain_grps,
    functionSets,
    outcomeSets,
    years: dict.years
  };
}

export function normalizeFilter(filt, db) {
  const f = filt || {};
  const one = v => Array.isArray(v) ? (v.length ? v[0] : "All") : (v == null ? "All" : v);
  const arr = v => Array.isArray(v) ? v : (v == null ? [] : [v]);
  return {
    years: f.years ? [f.years[0], f.years[1]] : (db ? db.years.slice() : [2010, 2026]),
    income: arr(f.income),
    region: arr(f.region),
    function: arr(f.function),
    outcome: arr(f.outcome),
    design: arr(f.design),
    analysis: one(f.analysis),
    datatype: one(f.datatype),
    datasource: one(f.datasource),
    scope: one(f.scope)
  };
}

export function applyFilters(db, filt) {
  const f = normalizeFilter(filt, db);
  const st = db.studies;
  const n = db.nStudies;
  const [lo, hi] = f.years;
  const base = new Uint8Array(n);

  const designCodes = f.design.length
    ? new Set(f.design.map(l => db.codeOf.study_design.get(l))) : null;
  const analysisCode = f.analysis !== "All" ? db.codeOf.type_of_analysis.get(f.analysis) : null;
  const datatypeCode = f.datatype !== "All" ? db.codeOf.data_type.get(f.datatype) : null;
  const datasourceCode = f.datasource !== "All" ? db.codeOf.data_source.get(f.datasource) : null;
  const scopeCode = f.scope !== "All" ? db.codeOf.geo_scope.get(f.scope) : null;
  let funcSet = null;
  if (f.function.length) {
    funcSet = new Set();
    for (const g of f.function) {
      const gi = db.function_grps.indexOf(g);
      if (gi >= 0) for (const s of db.functionSets[gi]) funcSet.add(s);
    }
  }
  let outcomeSet = null;
  if (f.outcome.length) {
    outcomeSet = new Set();
    for (const g of f.outcome) {
      const gi = db.outcome_grps.indexOf(g);
      if (gi >= 0) for (const s of db.outcomeSets[gi]) outcomeSet.add(s);
    }
  }

  for (let s = 0; s < n; s++) {
    const y = st.year[s];
    if (y < lo || y > hi) continue;
    if (designCodes && !designCodes.has(st.study_design[s])) continue;
    if (analysisCode !== null && st.type_of_analysis[s] !== analysisCode) continue;
    if (datatypeCode !== null && st.data_type[s] !== datatypeCode) continue;
    if (datasourceCode !== null && st.data_source[s] !== datasourceCode) continue;
    if (scopeCode !== null && st.geo_scope[s] !== scopeCode) continue;
    if (funcSet && !funcSet.has(s)) continue;
    if (outcomeSet && !outcomeSet.has(s)) continue;
    base[s] = 1;
  }

  const g = db.geo;
  const incSet = f.income.length ? new Set(f.income) : null;
  const regSet = f.region.length ? new Set(f.region) : null;
  const countryFilterActive = !!(incSet || regSet);
  const geoRows = [];
  const geoStudySet = countryFilterActive ? new Set() : null;
  for (let i = 0; i < g.s.length; i++) {
    const s = g.s[i];
    if (!base[s]) continue;
    const c = g.c[i];
    if (incSet && !incSet.has(db.incomeOf[c])) continue;
    if (regSet) {
      const r = db.regionOf[c];
      if (r == null || !regSet.has(r)) continue;
    }
    geoRows.push(i);
    if (geoStudySet) geoStudySet.add(s);
  }

  const studies = [];
  const mask = new Uint8Array(n);
  for (let s = 0; s < n; s++) {
    if (!base[s]) continue;
    if (geoStudySet && !geoStudySet.has(s)) continue;
    studies.push(s);
    mask[s] = 1;
  }

  const counts = new Int32Array(db.countries.length);
  for (const i of geoRows) counts[g.c[i]]++;
  const present = [];
  const rest = [];
  for (let c = 0; c < db.countries.length; c++) {
    if (counts[c] > 0) present.push(c); else rest.push(c);
  }
  present.sort((a, b) => db.countries[a].iso3 < db.countries[b].iso3 ? -1
    : db.countries[a].iso3 > db.countries[b].iso3 ? 1 : 0);
  const byCountry = present.concat(rest).map(c => {
    const r = db.countries[c];
    const dalys = num(r.dalys);
    const spend = num(r.total_spend_bn);
    const pop = num(r.pop);
    return {
      c,
      iso3: r.iso3,
      country: r.country,
      income: r.income,
      un_region: r.un_region,
      pop: pop,
      dalys: dalys,
      total_spend_bn: spend,
      studies: counts[c],
      per100k: ratio(counts[c], dalys == null ? null : dalys / 1e5),
      per_bn: ratio(counts[c], spend),
      per_million: ratio(counts[c], pop == null ? null : pop / 1e6)
    };
  });

  return { filt: f, mask, studies, geoRows, byCountry };
}

export function valueBoxes(db, flt) {
  const n = flt.studies.length;
  const cs = new Set();
  for (const i of flt.geoRows) cs.add(db.geo.c[i]);
  const qCode = db.codeOf.type_of_analysis.get("Quantitative");
  let q = 0, doi = 0;
  for (const s of flt.studies) {
    if (db.studies.type_of_analysis[s] === qCode) q++;
    if (db.studies.has_doi[s] === 1) doi++;
  }
  return {
    v_studies: n,
    v_countries: cs.size,
    v_quant_pct: n ? rRound(100 * q / n) : null,
    v_doi_pct: n ? rRound(100 * doi / n) : null
  };
}

export function trendSeries(db, flt, varName) {
  if (varName === "none") {
    const counts = new Map();
    for (const s of flt.studies) {
      const y = db.studies.year[s];
      counts.set(y, (counts.get(y) || 0) + 1);
    }
    return sortedYearObj(counts);
  }
  const isGeo = varName === "income" || varName === "un_region";
  const grp = grpDim(db, varName);
  const counts = new Map();
  const bump = (y, cat) => {
    let m = counts.get(y);
    if (!m) { m = new Map(); counts.set(y, m); }
    m.set(cat, (m.get(cat) || 0) + 1);
  };
  if (isGeo) {
    const seen = new Set();
    for (const i of flt.geoRows) {
      const s = db.geo.s[i], y = db.geo.y[i], c = db.geo.c[i];
      const cat = varName === "income" ? db.incomeOf[c] : db.regionOf[c];
      if (cat == null) continue;
      const key = s + "|" + y + "|" + cat;
      if (seen.has(key)) continue;
      seen.add(key);
      bump(y, cat);
    }
  } else if (grp) {
    for (let i = 0; i < grp.rows.s.length; i++) {
      const s = grp.rows.s[i];
      if (!flt.mask[s]) continue;
      bump(db.studies.year[s], grp.grps[grp.rows.g[i]]);
    }
  } else {
    const lv = db.levels[varName];
    for (const s of flt.studies) {
      bump(db.studies.year[s], lv[db.studies[varName][s]]);
    }
  }
  const out = {};
  for (const y of [...counts.keys()].sort((a, b) => a - b)) {
    out[y] = Object.fromEntries(counts.get(y));
  }
  return out;
}

// The two multi-value dimensions (financing function, outcome domain) each get
// their own {s,g} junction table, same shape as HEE's disease.json/diseaseSets
// used to be. grpDim() resolves a registry column name to the right table.
function grpDim(db, xv) {
  if (xv === "func_grp") return { rows: db.function, grps: db.function_grps };
  if (xv === "outcome_grp") return { rows: db.outcome, grps: db.outcome_grps };
  return null;
}

function studyCatGetter(db, varName) {
  const st = db.studies;
  if (varName === "doi_label") return s => st.has_doi[s] === 1 ? "Has DOI" : "No DOI";
  const lv = db.levels[varName];
  const col = st[varName];
  return s => lv[col[s]];
}

export function compCounts(db, flt, xv, sv, mode) {
  const pct = mode === "pct";
  const stacked = !!(sv && sv !== xv);
  const counts = new Map();
  const add = (cat, stk) => {
    if (cat == null) return;
    if (!stacked) {
      counts.set(cat, (counts.get(cat) || 0) + 1);
    } else {
      if (stk == null) return;
      let m = counts.get(cat);
      if (!m) { m = new Map(); counts.set(cat, m); }
      m.set(stk, (m.get(stk) || 0) + 1);
    }
  };

  const gd = grpDim(db, xv);
  if (gd) {
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    const rows = gd.rows;
    for (let i = 0; i < rows.s.length; i++) {
      const s = rows.s[i];
      if (!flt.mask[s]) continue;
      add(gd.grps[rows.g[i]], stacked ? stackOf(s) : null);
    }
  } else {
    const catOf = studyCatGetter(db, xv);
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    for (const s of flt.studies) add(catOf(s), stacked ? stackOf(s) : null);
  }

  const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

  if (!stacked) {
    const rows = [...counts.entries()].map(([x, nn]) => ({ x, n: nn }));
    rows.sort((a, b) => cmpStr(a.x, b.x));
    const total = rows.reduce((a, r) => a + r.n, 0);
    for (const r of rows) r.v = pct ? (total > 0 ? 100 * r.n / total : 0) : r.n;
    rows.sort((a, b) => b.v - a.v);
    return { type: "simple", rows, total, pct };
  }

  const cats = [...counts.keys()].sort(cmpStr);
  const totals = new Map();
  for (const c of cats) {
    let t = 0;
    for (const v of counts.get(c).values()) t += v;
    totals.set(c, t);
  }
  const catOrder = cats.slice()
    .sort((a, b) => (totals.get(a) - totals.get(b)) || cmpStr(a, b))
    .reverse();
  const stackSet = new Set();
  for (const c of cats) for (const k of counts.get(c).keys()) stackSet.add(k);
  const stacks = [...stackSet].sort(cmpStr);
  const rawCounts = {};
  const values = {};
  for (const c of cats) {
    rawCounts[c] = Object.fromEntries(counts.get(c));
    values[c] = {};
    for (const [k, nn] of counts.get(c)) {
      values[c][k] = pct ? (totals.get(c) > 0 ? 100 * nn / totals.get(c) : 0) : nn;
    }
  }
  return { type: "stacked", catOrder, stacks, counts: rawCounts, values, totals: Object.fromEntries(totals), pct };
}

export function byCountryTop(db, flt, k = 10) {
  const rows = flt.byCountry.filter(r => r.studies > 0);
  rows.sort((a, b) => b.studies - a.studies);
  return rows.slice(0, k).map(r => ({
    iso3: r.iso3,
    studies: r.studies,
    per100k: r.per100k,
    per_bn: r.per_bn,
    per_million: r.per_million
  }));
}

export function scatterPoints(db, flt, xv, yv) {
  return flt.byCountry.filter(r =>
    r.studies > 0 &&
    r[xv] != null && r[xv] > 0 &&
    r[yv] != null && r[yv] > 0 &&
    r.income != null);
}

export function tableRows(db, flt, k = 25) {
  const rows = flt.byCountry.filter(r => r.studies > 0);
  rows.sort((a, b) => b.studies - a.studies);
  return rows.slice(0, k).map(r => ({
    Country: r.country,
    Income: r.income,
    Region: r.un_region == null ? "" : r.un_region,
    Studies: r.studies,
    "Per 100k DALYs": r.per100k == null ? null : rRound(r.per100k, 2),
    "Per US$1bn": r.per_bn == null ? null : rRound(r.per_bn, 2),
    "Per million": r.per_million == null ? null : rRound(r.per_million, 2)
  }));
}

const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

function profileSets(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const income = db.countries[ci].income;
  const g = db.geo;
  const cs = new Set(), ps = new Set();
  for (let i = 0; i < g.s.length; i++) {
    const c = g.c[i], s = g.s[i];
    if (c === ci) cs.add(s);
    if (db.incomeOf[c] === income) ps.add(s);
  }
  return { ci, income, cs, ps };
}

function methodsMixSets(db, cs, ps) {
  const lv = db.levels.study_design;
  const col = db.studies.study_design;
  const cn = new Map(), pn = new Map();
  for (const s of cs) { const t = lv[col[s]]; cn.set(t, (cn.get(t) || 0) + 1); }
  for (const s of ps) { const t = lv[col[s]]; pn.set(t, (pn.get(t) || 0) + 1); }
  const nc = cs.size, np = ps.size;
  const rows = [...new Set([...cn.keys(), ...pn.keys()])].map(t => ({
    type: t,
    country_share: nc > 0 ? 100 * (cn.get(t) || 0) / nc : null,
    peer_share: np > 0 ? 100 * (pn.get(t) || 0) / np : null
  }));
  const y_order = rows.slice()
    .sort((a, b) => ((b.peer_share == null ? 0 : b.peer_share) -
                     (a.peer_share == null ? 0 : a.peer_share)) || cmpStr(a.type, b.type))
    .map(r => r.type);
  rows.sort((a, b) => y_order.indexOf(a.type) - y_order.indexOf(b.type));
  return { rows, y_order };
}

export function methodsMix(db, iso3) {
  const sets = profileSets(db, iso3);
  return sets ? methodsMixSets(db, sets.cs, sets.ps) : null;
}

function signalCounts(db, set) {
  const st = db.studies;
  const qCode = db.codeOf.type_of_analysis.get("Quantitative");
  const adCode = db.codeOf.data_source.get("Administrative data");
  let q = 0, doi = 0, ad = 0;
  for (const s of set) {
    if (st.type_of_analysis[s] === qCode) q++;
    if (st.has_doi[s] === 1) doi++;
    if (st.data_source[s] === adCode) ad++;
  }
  return { n: set.size, q, doi, ad };
}

function signalsSets(db, cs, ps) {
  const c = signalCounts(db, cs), p = signalCounts(db, ps);
  const whole = (k, cc) => cc.n > 0 ? 100 * cc[k] / cc.n : null;
  const val = (metric, cc) => {
    if (metric === "Quantitative") return whole("q", cc);
    if (metric === "Has DOI") return whole("doi", cc);
    return whole("ad", cc);
  };
  const rows = db.registries.SIGNAL_METRICS.map(metric => ({
    metric, country_pct: val(metric, c), peer_pct: val(metric, p)
  }));
  return { rows };
}

export function signals(db, iso3) {
  const sets = profileSets(db, iso3);
  return sets ? signalsSets(db, sets.cs, sets.ps) : null;
}

export function benchmark(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const income = db.countries[ci].income;
  const rows = [];
  for (const r of db.countries) {
    if (r.income !== income) continue;
    const dalys = num(r.dalys), per100k = num(r.per100k_dalys);
    if (dalys == null || per100k == null || dalys <= 0 || per100k <= 0) continue;
    rows.push({ iso3: r.iso3, country: r.country, studies: r.studies, dalys, per100k });
  }
  rows.sort((a, b) => cmpStr(a.iso3, b.iso3));
  const v = rows.map(r => r.per100k).sort((a, b) => a - b);
  const mid = v.length >> 1;
  const median_per100k = !v.length ? null
    : (v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2);
  const selected = rows.some(r => r.iso3 === iso3) ? iso3 : null;
  return { rows, median_per100k, n_points: rows.length, selected };
}

export function countryProfile(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const r = db.countries[ci];
  const peers = db.countries.filter(x => x.income === r.income);
  const n_peer = peers.length;
  const median = vals => {
    const v = vals.map(num).filter(x => x != null).sort((a, b) => a - b);
    if (!v.length) return null;
    const m = v.length >> 1;
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  };
  const medians = {
    m_daly: median(peers.map(x => x.per100k_dalys)),
    m_bn: median(peers.map(x => x.per_bn_usd)),
    m_mil: median(peers.map(x => x.per_million))
  };

  const g = db.geo;
  const cTrendCountry = new Map();
  const cTrendPeer = new Map();
  const mineSet = new Set();
  const peerSet = new Set();
  for (let i = 0; i < g.s.length; i++) {
    const c = g.c[i], y = g.y[i], s = g.s[i];
    if (c === ci) {
      cTrendCountry.set(y, (cTrendCountry.get(y) || 0) + 1);
      mineSet.add(s);
    }
    if (db.incomeOf[c] === r.income) {
      cTrendPeer.set(y, (cTrendPeer.get(y) || 0) + 1);
      peerSet.add(s);
    }
  }
  const peerTrend = {};
  for (const y of [...cTrendPeer.keys()].sort((a, b) => a - b)) {
    peerTrend[y] = cTrendPeer.get(y) / n_peer;
  }

  const mixC = {}, mixP = {};
  let totC = 0, totP = 0;
  const fn = db.function;
  for (let i = 0; i < fn.s.length; i++) {
    const s = fn.s[i];
    const grp = db.function_grps[fn.g[i]];
    if (mineSet.has(s)) { mixC[grp] = (mixC[grp] || 0) + 1; totC++; }
    if (peerSet.has(s)) { mixP[grp] = (mixP[grp] || 0) + 1; totP++; }
  }
  const shares = (o, t) => {
    const out = {};
    for (const k of Object.keys(o).sort()) out[k] = t > 0 ? 100 * o[k] / t : 0;
    return out;
  };

  const mm = methodsMixSets(db, mineSet, peerSet);
  const sg = signalsSets(db, mineSet, peerSet);
  const bm = benchmark(db, iso3);

  return {
    iso3: r.iso3,
    income: r.income,
    un_region: r.un_region,
    c_n: r.studies,
    c_daly: num(r.per100k_dalys),
    c_spend: num(r.per_bn_usd),
    c_percap: num(r.per_million),
    medians,
    n_peer,
    c_trend: { country: sortedYearObj(cTrendCountry), peer: peerTrend },
    c_mix: { country: shares(mixC, totC), peer: shares(mixP, totP) },
    c_methods: Object.assign(
      Object.fromEntries(mm.rows.map(x => [x.type,
        { country_share: x.country_share, peer_share: x.peer_share }])),
      { y_order: mm.y_order }),
    c_signals: Object.fromEntries(sg.rows.map(x => [x.metric,
      { country_pct: x.country_pct, peer_pct: x.peer_pct }])),
    c_benchmark: { median_per100k: bm.median_per100k, n_points: bm.n_points, rows: bm.rows }
  };
}

export function countryFacts(db, iso3) {
  const r = db.countries.find(x => x.iso3 === iso3);
  if (!r) return [];
  const pop = num(r.pop), dalys = num(r.dalys), spend = num(r.total_spend_bn);
  const pairs = [
    ["Income group", r.income],
    ["UN region", r.un_region == null ? "—" : r.un_region]
  ];
  if (pop != null) pairs.push(["Population", fmtNum(rRound(pop / 1e6)) + " M"]);
  if (dalys != null) pairs.push(["Disease burden", fmtNum(rRound(dalys / 1e6)) + " M DALYs (2023)"]);
  if (spend != null) pairs.push(["Health spending", "US$ " + fmtNum(rRound(spend)) + " bn (PPP 2022)"]);
  pairs.push(["Studies per million", rRound(num(r.per_million), 2)]);
  return pairs;
}

// Registry constants (TREND_VARS / COMP_VARS / STACK_VARS / MAP_METRICS /
// SCAT_X / SCAT_Y / SIGNAL_METRICS) come from content.json registries —
// see buildRegistries() and db.registries.

const ACCENT = "#1f5fa8";
const GREY = "#adb5bd";

if (typeof document !== "undefined") {

  const $ = id => document.getElementById(id);
  const PLOTLY_CFG = { responsive: true, displayModeBar: false };
  const BASE_FONT = { family: "Inter, sans-serif", size: 12, color: "#1c2733" };

  let db = null;
  let GALLERY = [];
  let FIG_INDEX = {};
  const state = {
    filt: null,
    result: null,
    country: "IND",
    ts: {}
  };

  function debounce(fn, ms) {
    let t = null;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // TRUST BOUNDARY: el()'s `html` argument goes through innerHTML and must
  // ONLY receive developer-authored literals. Data-derived strings (anything
  // from data/*.json, user-influenced values, exception messages) must be set
  // with textContent, or escaped with esc() before being embedded in an HTML
  // string (Plotly hover text). content.json strings are developer-authored
  // (generated by our R build from R/app-content.R) and would be acceptable
  // here, but are rendered via textContent anyway.
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function fillSelect(sel, labels, selected) {
    sel.textContent = "";
    for (const lab of labels) {
      const o = document.createElement("option");
      o.value = lab;
      o.textContent = lab;
      if (selected && selected.includes(lab)) o.selected = true;
      sel.appendChild(o);
    }
  }

  function openModal(file) {
    const f = FIG_INDEX[file];
    if (!f) return;
    $("fig-modal-title").textContent = f.title;
    const img = $("fig-modal-img");
    img.src = "figures/" + f.file;
    img.alt = f.title;
    $("fig-modal-caption").textContent = f.caption;
    $("fig-modal").classList.add("open");
  }

  function closeModal() {
    $("fig-modal").classList.remove("open");
    $("fig-modal-img").src = "";
  }

  function switchTab(name) {
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      b.classList.toggle("active", b.dataset.tab === name);
    }
    for (const p of document.querySelectorAll(".tab-pane")) {
      p.classList.toggle("active", p.id === "pane-" + name);
    }
    if (name === "overview" && window.Plotly) {
      for (const id of ["ov-trend", "ov-func"]) {
        if ($(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "explorer" && state.result) {
      for (const id of ["x-trend", "x-map", "x-comp", "x-scatter"]) {
        if (window.Plotly && $(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "country" && window.Plotly) {
      for (const id of ["c-trend", "c-mix", "c-methods", "c-signals", "c-benchmark"]) {
        if ($(id).data) window.Plotly.Plots.resize($(id));
      }
    }
  }

  function renderOverview() {
    const m = db.dict.meta;
    $("nav-built").textContent = "bundle " + m.built;

    // Hero paragraph: ordered segments from content.json. Each segment
    // becomes a <span>/<strong>/<em> filled via textContent — no innerHTML.
    const hero = $("ov-hero");
    hero.textContent = "";
    for (const seg of db.content.hero) {
      const node = document.createElement(seg.strong ? "strong" : seg.em ? "em" : "span");
      node.textContent = seg.text;
      hero.appendChild(node);
    }

    // Glance tiles: final formatted strings from content.json;
    // sub === null means no footer line.
    const wrap = $("ov-tiles");
    wrap.textContent = "";
    for (const t of db.content.glance_tiles) {
      const box = el("div", "value-box bg-" + t.theme);
      const title = el("div", "value-box-title");
      title.textContent = t.label;
      const value = el("div", "value-box-value");
      value.textContent = t.value;
      box.appendChild(title);
      box.appendChild(value);
      if (t.sub != null) {
        const sub = el("div", "value-box-sub");
        sub.textContent = t.sub;
        box.appendChild(sub);
      }
      wrap.appendChild(box);
    }

  }

  // Two small live charts replace HEE's pre-rendered hero images — computed
  // via the same trendSeries/compCounts functions the Explorer uses, run once
  // against the unfiltered dataset.
  function renderOverviewCharts() {
    const flt = applyFilters(db, {});
    const ser = trendSeries(db, flt, "none");
    const years = Object.keys(ser).map(Number);
    window.Plotly.react("ov-trend", [{
      x: years, y: years.map(y => ser[y]),
      mode: "lines", type: "scatter",
      line: { color: ACCENT, width: 3 },
      hovertemplate: "%{x}: %{y} studies<extra></extra>"
    }], {
      font: BASE_FONT,
      margin: { t: 10, b: 40, l: 50, r: 20 },
      xaxis: { gridcolor: "#eeebe3" },
      yaxis: { title: "studies", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    const res = compCounts(db, flt, "func_grp", null, "n");
    const bottomUp = res.rows.slice().reverse();
    window.Plotly.react("ov-func", [{
      type: "bar", orientation: "h",
      y: res.rows.map(r => r.x), x: res.rows.map(r => r.v),
      marker: { color: ACCENT },
      hovertemplate: "%{y}: %{x}<extra></extra>"
    }], {
      font: BASE_FONT,
      margin: { t: 10, b: 40, l: 230, r: 20 },
      yaxis: { categoryorder: "array", categoryarray: bottomUp.map(r => r.x), automargin: true },
      xaxis: { title: "studies", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderGalleryIndex() {
    const idx = $("gal-section-index");
    idx.textContent = "";
    GALLERY.forEach((sec, i) => {
      const card = el("button", "section-card");
      const title = el("div", "sec-title");
      title.textContent = sec.title;
      const count = el("div", "sec-count");
      count.textContent = sec.figs.length + " figures";
      card.appendChild(title);
      card.appendChild(count);
      card.addEventListener("click", () => showSection(i));
      idx.appendChild(card);
    });
  }

  function showSection(i) {
    const sec = GALLERY[i];
    $("gal-index").style.display = "none";
    $("gal-section").style.display = "block";
    $("gal-sec-title").textContent = sec.title;
    $("gal-sec-blurb").textContent = sec.blurb.replace(/\s+/g, " ").trim();
    const grid = $("gal-sec-grid");
    grid.textContent = "";
    for (const f of sec.figs) {
      const card = el("div", "fig-card");
      const img = el("img");
      img.src = "figures/" + f.file;
      img.alt = f.title;
      img.loading = "lazy";
      img.addEventListener("click", () => openModal(f.file));
      card.appendChild(img);
      const body = el("div", "fig-body");
      const ft = el("div", "fig-title");
      ft.textContent = f.title;
      const fc = el("div", "fig-caption");
      fc.textContent = f.caption.replace(/\s+/g, " ").trim();
      body.appendChild(ft);
      body.appendChild(fc);
      card.appendChild(body);
      grid.appendChild(card);
    }
    window.scrollTo(0, 0);
  }

  function hideSection() {
    $("gal-section").style.display = "none";
    $("gal-index").style.display = "block";
  }

  // Methods selection funnel: rows from content.json. `records`
  // strings arrive final-formatted (incl. Unicode minus U+2212); the strong
  // flag renders label and records in <strong> elements (textContent only).
  function renderFunnel() {
    const tb = $("methods-funnel");
    tb.textContent = "";
    for (const row of db.content.funnel) {
      const tr = document.createElement("tr");
      for (const text of [row.label, row.records]) {
        const td = document.createElement("td");
        if (row.strong) {
          const s = document.createElement("strong");
          s.textContent = text;
          td.appendChild(s);
        } else {
          td.textContent = text;
        }
        tr.appendChild(td);
      }
      tb.appendChild(tr);
    }
  }

  function makeRadios(containerId, name, choices) {
    const c = $(containerId);
    c.textContent = "";
    choices.forEach((ch, i) => {
      const lab = el("label");
      const inp = el("input");
      inp.type = "radio";
      inp.name = name;
      inp.value = ch;
      inp.checked = i === 0;
      inp.addEventListener("change", () => {
        state.filt[name.slice(2)] = ch;
        refreshExplorer();
      });
      lab.appendChild(inp);
      lab.appendChild(document.createTextNode(ch));
      c.appendChild(lab);
    });
  }

  function makeMultiSelect(id, options, placeholder, key) {
    const sel = $(id);
    for (const o of options) {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o;
      sel.appendChild(opt);
    }
    state.ts[key] = new window.TomSelect(sel, {
      plugins: ["remove_button"],
      placeholder: placeholder,
      allowEmptyOption: false,
      onChange: vals => {
        state.filt[key] = Array.isArray(vals) ? vals.slice() : (vals ? [vals] : []);
        refreshExplorer();
      }
    });
  }

  function setupExplorerControls() {
    const m = db.dict.meta;
    state.filt = {
      years: db.years.slice(),
      income: [], region: [], function: [], outcome: [], design: [],
      analysis: "All", datatype: "All", datasource: "All", scope: "All"
    };

    const slider = $("x-years");
    window.noUiSlider.create(slider, {
      start: db.years,
      connect: true,
      step: 1,
      range: { min: db.years[0], max: db.years[1] }
    });
    const readout = $("x-years-readout");
    const setReadout = () => {
      readout.textContent = state.filt.years[0] + " – " + state.filt.years[1];
    };
    setReadout();
    const debouncedYears = debounce(() => refreshExplorer(), 250);
    slider.noUiSlider.on("update", (values) => {
      state.filt.years = [Math.round(+values[0]), Math.round(+values[1])];
      setReadout();
      debouncedYears();
    });

    makeMultiSelect("x-income", db.incOrder, "All groups", "income");
    makeMultiSelect("x-region", db.dict.REGIONS, "All regions", "region");
    makeMultiSelect("x-function", db.function_grps, "All functions", "function");
    makeMultiSelect("x-outcome", db.outcome_grps, "All domains", "outcome");
    makeMultiSelect("x-design", db.levels.study_design, "All designs", "design");

    makeRadios("x-analysis", "x_analysis", ["All", "Quantitative", "Qualitative", "Mixed methods"]);

    const datatype = $("x-datatype");
    fillSelect(datatype, ["All"].concat(db.levels.data_type));
    datatype.addEventListener("change", () => {
      state.filt.datatype = datatype.value;
      refreshExplorer();
    });

    const datasource = $("x-datasource");
    fillSelect(datasource, ["All"].concat(db.levels.data_source));
    datasource.addEventListener("change", () => {
      state.filt.datasource = datasource.value;
      refreshExplorer();
    });

    const scope = $("x-scope");
    fillSelect(scope, ["All"].concat(db.levels.geo_scope));
    scope.addEventListener("change", () => {
      state.filt.scope = scope.value;
      refreshExplorer();
    });

    $("x-reset").addEventListener("click", () => {
      slider.noUiSlider.set(db.years);
      for (const k of ["income", "region", "function", "outcome", "design"]) state.ts[k].clear();
      const first = $("x-analysis").querySelector("input");
      first.checked = true;
      state.filt.analysis = "All";
      datatype.value = "All";
      state.filt.datatype = "All";
      datasource.value = "All";
      state.filt.datasource = "All";
      scope.value = "All";
      state.filt.scope = "All";
      state.filt.years = db.years.slice();
      setReadout();
      refreshExplorer();
    });

    const REG = db.registries;
    fillSelect($("x-trend-by"), [...REG.TREND_VARS.keys()], ["Income group"]);
    fillSelect($("x-map-metric"), [...REG.MAP_METRICS.keys()], ["Studies"]);
    fillSelect($("x-comp-var"), [...REG.COMP_VARS.keys()], ["Financing function"]);
    fillSelect($("x-comp-stack"), [...REG.STACK_VARS.keys()], ["None"]);
    const compMode = $("x-comp-mode");
    compMode.textContent = "";
    for (const [lab, val] of [["Count", "n"], ["Share (%)", "pct"]]) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = lab;
      compMode.appendChild(o);
    }
    fillSelect($("x-scatter-x"), [...REG.SCAT_X.keys()], ["Total DALYs (GBD 2023)"]);
    fillSelect($("x-scatter-y"), [...REG.SCAT_Y.keys()], ["Studies per 100k DALYs"]);

    $("x-trend-by").addEventListener("change", renderTrend);
    $("x-map-metric").addEventListener("change", renderMap);
    $("x-comp-var").addEventListener("change", renderComp);
    $("x-comp-stack").addEventListener("change", renderComp);
    $("x-comp-mode").addEventListener("change", renderComp);
    $("x-scatter-x").addEventListener("change", renderScatter);
    $("x-scatter-y").addEventListener("change", renderScatter);
  }

  function refreshExplorer() {
    state.result = applyFilters(db, state.filt);
    renderValueBoxes();
    renderTrend();
    renderMap();
    renderComp();
    renderScatter();
    renderTable();
  }

  function renderValueBoxes() {
    const v = valueBoxes(db, state.result);
    $("v-studies").textContent = fmtNum(v.v_studies);
    $("v-countries").textContent = fmtNum(v.v_countries);
    $("v-quant").textContent = v.v_quant_pct == null ? "—" : v.v_quant_pct + "%";
    $("v-doi").textContent = v.v_doi_pct == null ? "—" : v.v_doi_pct + "%";
  }

  function hLegend(y) {
    return { orientation: "h", y: y, x: 0 };
  }

  function renderTrend() {
    const label = $("x-trend-by").value;
    const v = db.registries.TREND_VARS.get(label);
    const ser = trendSeries(db, state.result, v);
    const years = Object.keys(ser).map(Number);
    let traces;
    if (v === "none") {
      traces = [{
        x: years, y: years.map(y => ser[y]),
        mode: "lines", type: "scatter",
        line: { color: ACCENT, width: 3 },
        name: "studies", hovertemplate: "%{x}: %{y} studies<extra></extra>"
      }];
    } else {
      let cats;
      let colorMap = null;
      if (v === "income") {
        cats = db.incLv.slice();
        colorMap = db.palInc;
      } else {
        cats = [...new Set(years.flatMap(y => Object.keys(ser[y])))].sort();
      }
      traces = cats.map(cat => ({
        x: years,
        y: years.map(y => (ser[y] && ser[y][cat] != null) ? ser[y][cat] : null),
        mode: "lines", type: "scatter",
        name: cat,
        connectgaps: false,
        line: { width: 2.4, color: colorMap ? colorMap[cat] : undefined },
        // cat comes from dict levels (developer-curated); escaped anyway —
        // Plotly renders hovertemplate output as HTML.
        hovertemplate: "%{x} · " + esc(cat) + ": %{y} studies<extra></extra>"
      }));
    }
    window.Plotly.react("x-trend", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 60, r: 20 },
      legend: hLegend(-0.18),
      xaxis: { title: null, gridcolor: "#eeebe3" },
      yaxis: { title: "studies", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderMap() {
    const label = $("x-map-metric").value;
    const m = db.registries.MAP_METRICS.get(label);
    const rows = state.result.byCountry;
    const isCounts = m === "studies";
    const z = rows.map(r => isCounts ? Math.log10(r.studies + 1) : r[m]);
    // Plotly renders hover text as HTML — country names are data-derived and
    // must be escaped before concatenation.
    const text = rows.map(r => isCounts
      ? esc(r.country) + "<br>" + fmtNum(r.studies) + " studies"
      : esc(r.country) + "<br>" + fmtNum(r.studies) + " studies<br>" +
        (r[m] == null ? "NA" : rRound(r[m], 2)) + " " + esc(label.toLowerCase()));
    const colorscale = isCounts
      ? [[0, "#f1f3f5"], [0.0001, "#c6dbef"], [0.5, "#2a78d6"], [1, "#08306b"]]
      : [[0, "#f7fbff"], [0.5, "#6baed6"], [1, "#08306b"]];
    const colorbar = isCounts
      ? {
          title: "studies<br>(log)",
          tickvals: [0, 1, 10, 100, 1000].map(x => Math.log10(x + 1)),
          ticktext: ["0", "1", "10", "100", "1000"],
          thickness: 12, len: 0.8
        }
      : { title: label.split(" ").join("<br>"), thickness: 12, len: 0.8 };
    window.Plotly.react("x-map", [{
      type: "choropleth",
      locations: rows.map(r => r.iso3),
      z: z,
      text: text,
      hoverinfo: "text",
      colorscale: colorscale,
      marker: { line: { color: "#ffffff", width: 0.3 } },
      colorbar: colorbar
    }], {
      font: BASE_FONT,
      geo: {
        projection: { type: "robinson" },
        showframe: false,
        showcoastlines: false,
        bgcolor: "rgba(0,0,0,0)"
      },
      margin: { t: 0, b: 0, l: 0, r: 0 }
    }, PLOTLY_CFG);
  }

  function renderComp() {
    const label = $("x-comp-var").value;
    const xv = db.registries.COMP_VARS.get(label);
    const sv = db.registries.STACK_VARS.get($("x-comp-stack").value);
    const mode = $("x-comp-mode").value;
    const res = compCounts(db, state.result, xv, sv, mode);
    const note = (xv === "func_grp" || xv === "outcome_grp") ? " · a study can sit in several groups" : "";
    const annotation = {
      text: label + note, xref: "paper", yref: "paper",
      x: 0, y: 1.06, xanchor: "left", showarrow: false,
      font: { size: 11, color: "#6b7280" }
    };
    let traces, layout;
    if (res.type === "simple") {
      const desc = res.rows;
      const bottomUp = desc.slice().reverse();
      traces = [{
        type: "bar", orientation: "h",
        y: desc.map(r => r.x),
        x: desc.map(r => r.v),
        marker: { color: ACCENT },
        hovertemplate: "%{y}: %{x}<extra></extra>"
      }];
      layout = {
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp.map(r => r.x),
          automargin: true
        },
        xaxis: {
          title: res.pct ? "share of filtered studies (%)" : "studies",
          gridcolor: "#eeebe3",
          ticksuffix: res.pct ? "%" : ""
        }
      };
    } else {
      const bottomUp = res.catOrder.slice().reverse();
      traces = res.stacks.map(k => ({
        type: "bar", orientation: "h",
        name: k,
        y: res.catOrder,
        x: res.catOrder.map(c => res.values[c][k] != null ? res.values[c][k] : 0),
        // k comes from dict levels (developer-curated); escaped anyway —
        // Plotly renders hovertemplate output as HTML.
        hovertemplate: "%{y} · " + esc(k) + ": %{x}<extra></extra>"
      }));
      layout = {
        barmode: "stack",
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp,
          automargin: true
        },
        xaxis: {
          title: res.pct ? "share within category (%)" : "studies",
          gridcolor: "#eeebe3",
          range: res.pct ? [0, 100] : undefined,
          ticksuffix: res.pct ? "%" : ""
        }
      };
    }
    window.Plotly.react("x-comp", traces, Object.assign({
      font: BASE_FONT,
      margin: { t: 30, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
      annotations: [annotation]
    }, layout), PLOTLY_CFG);
  }

  function renderScatter() {
    const xLabel = $("x-scatter-x").value;
    const yLabel = $("x-scatter-y").value;
    const xv = db.registries.SCAT_X.get(xLabel);
    const yv = db.registries.SCAT_Y.get(yLabel);
    const pts = scatterPoints(db, state.result, xv, yv);
    const traces = db.incLv.map(inc => {
      const rows = pts.filter(r => r.income === inc);
      return {
        type: "scatter", mode: "markers",
        name: inc,
        x: rows.map(r => r[xv]),
        y: rows.map(r => r[yv]),
        // country names are data-derived; Plotly renders hover text as HTML.
        text: rows.map(r => esc(r.country) + "<br>" + fmtNum(r.studies) + " studies"),
        hoverinfo: "text",
        marker: { color: db.palInc[inc], size: 8, opacity: 0.8 }
      };
    });
    window.Plotly.react("x-scatter", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 70, l: 70, r: 20 },
      legend: hLegend(-0.2),
      xaxis: { type: "log", title: xLabel + " (log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: yLabel + " (log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderTable() {
    const rows = tableRows(db, state.result, 25);
    const cols = ["Country", "Income", "Region", "Studies", "Per 100k DALYs", "Per US$1bn", "Per million"];
    const numCols = new Set(["Studies", "Per 100k DALYs", "Per US$1bn", "Per million"]);
    // Country/Income/Region cells are data-derived strings: build the table
    // with createElement + textContent — never innerHTML string concat.
    const tbl = $("x-table");
    tbl.textContent = "";
    const thead = document.createElement("thead");
    const htr = document.createElement("tr");
    for (const c of cols) {
      const th = document.createElement("th");
      if (numCols.has(c)) th.className = "num";
      th.textContent = c;
      htr.appendChild(th);
    }
    thead.appendChild(htr);
    tbl.appendChild(thead);
    const tbody = document.createElement("tbody");
    for (const r of rows) {
      const tr = document.createElement("tr");
      for (const c of cols) {
        const v = r[c];
        const td = document.createElement("td");
        if (numCols.has(c)) td.className = "num";
        td.textContent = v == null ? "" : (c === "Studies" ? fmtNum(v) : String(v));
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    tbl.appendChild(tbody);
  }

  function setupCountryPane() {
    const sel = $("c-picker");
    for (const r of db.countries) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      if (r.iso3 === "IND") o.selected = true;
      sel.appendChild(o);
    }
    new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      onChange: val => {
        if (!val) return;
        state.country = val;
        renderCountryAll();
      }
    });
    renderCountryAll();
  }

  function renderCountryAll() {
    const iso3 = state.country;
    const prof = countryProfile(db, iso3);
    if (!prof) return;

    const facts = $("c-facts");
    facts.textContent = "";
    // Fact keys/values are data-derived (country names, region names,
    // formatted numbers) — textContent only, never el()'s innerHTML path.
    for (const [k, v] of countryFacts(db, iso3)) {
      const dt = el("dt");
      dt.textContent = k;
      const dd = el("dd");
      dd.textContent = String(v);
      facts.appendChild(dt);
      facts.appendChild(dd);
    }

    $("c-n").textContent = fmtNum(prof.c_n);
    $("c-daly").textContent = prof.c_daly == null ? "no burden data"
      : rRound(prof.c_daly, 2) + "  (median " + rRound(prof.medians.m_daly, 2) + ")";
    $("c-spend").textContent = prof.c_spend == null ? "no spending data"
      : rRound(prof.c_spend, 2) + "  (median " + rRound(prof.medians.m_bn, 2) + ")";
    $("c-percap").textContent = rRound(prof.c_percap, 2) + "  (median " + rRound(prof.medians.m_mil, 2) + ")";

    const ct = prof.c_trend;
    const cYears = Object.keys(ct.country).map(Number);
    const pYears = Object.keys(ct.peer).map(Number);
    window.Plotly.react("c-trend", [
      {
        x: cYears, y: cYears.map(y => ct.country[y]),
        mode: "lines", type: "scatter", name: "country",
        line: { color: ACCENT, width: 3 },
        hovertemplate: "%{x}: %{y} studies<extra>country</extra>"
      },
      {
        x: pYears, y: pYears.map(y => ct.peer[y]),
        mode: "lines", type: "scatter", name: "income-group mean",
        line: { color: GREY, width: 3 },
        hovertemplate: "%{x}: %{y:.2f} per country<extra>income-group mean</extra>"
      }
    ], {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 60, r: 20 },
      legend: hLegend(-0.18),
      xaxis: { gridcolor: "#eeebe3" },
      yaxis: { title: "studies per year", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    const mix = prof.c_mix;
    const grps = [...new Set([...Object.keys(mix.country), ...Object.keys(mix.peer)])];
    const meanShare = g => {
      const vals = [];
      if (mix.country[g] != null) vals.push(mix.country[g]);
      if (mix.peer[g] != null) vals.push(mix.peer[g]);
      return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
    };
    grps.sort((a, b) => meanShare(a) - meanShare(b));
    window.Plotly.react("c-mix", [
      {
        type: "bar", orientation: "h", name: "country",
        y: grps, x: grps.map(g => mix.country[g] != null ? mix.country[g] : null),
        marker: { color: ACCENT },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: grps, x: grps.map(g => mix.peer[g] != null ? mix.peer[g] : null),
        marker: { color: GREY },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "share of function-coded studies (%)", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: grps, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Study design mix. y_order = peer-share desc (ties alphabetical asc).
    // Plotly's categoryarray places its FIRST entry at the BOTTOM of a
    // horizontal-bar y axis, so categoryarray = y_order AS-IS means the chart
    // reads top→bottom as REVERSE y_order (peer share ascending).
    const meth = prof.c_methods;
    const yOrder = meth.y_order;
    const methVal = (side, t) => meth[t] && meth[t][side] != null ? meth[t][side] : null;
    window.Plotly.react("c-methods", [
      {
        type: "bar", orientation: "h", name: "country",
        y: yOrder, x: yOrder.map(t => methVal("country_share", t)),
        marker: { color: ACCENT },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: yOrder, x: yOrder.map(t => methVal("peer_share", t)),
        marker: { color: GREY },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "share of studies (%)", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: yOrder, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Approach & reporting. SIGNAL_METRICS order is fixed in content.json;
    // reversed here so the first-listed metric renders on top (Plotly's
    // categoryarray places its first entry at the bottom of a horizontal bar).
    const sig = prof.c_signals;
    const sigCats = db.registries.SIGNAL_METRICS.slice().reverse();
    const sigVal = (side, m) => sig[m] && sig[m][side] != null ? sig[m][side] : null;
    window.Plotly.react("c-signals", [
      {
        type: "bar", orientation: "h", name: "country",
        y: sigCats, x: sigCats.map(m => sigVal("country_pct", m)),
        marker: { color: ACCENT },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: sigCats, x: sigCats.map(m => sigVal("peer_pct", m)),
        marker: { color: GREY },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "% of studies", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: sigCats, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Peer benchmark: log10×log10 scatter of the filtered income-group
    // rows; peers grey-blue, selected country gold, dashed type-7 median line with
    // a muted annotation. Rows without usable burden are visibly absent.
    const bm = prof.c_benchmark;
    // country names are data-derived; Plotly renders hover text as HTML.
    const hoverOf = x => esc(x.country) + " — " + fmtNum(x.studies) + " studies — " +
      rRound(x.per100k, 2) + " per 100k DALYs";
    const bmPeers = bm.rows.filter(x => x.iso3 !== prof.iso3);
    const bmSel = bm.rows.filter(x => x.iso3 === prof.iso3);
    const bmLayout = {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 70, r: 20 },
      xaxis: { type: "log", title: "Total disease burden (DALYs, 2023, log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: "Studies per 100k DALYs (log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    };
    if (bm.median_per100k != null) {
      bmLayout.shapes = [{
        type: "line", xref: "paper", x0: 0, x1: 1,
        yref: "y", y0: bm.median_per100k, y1: bm.median_per100k,
        line: { color: "#6b7280", width: 1, dash: "dash" }
      }];
      bmLayout.annotations = [{
        text: "income-group median", xref: "paper", x: 0.99, xanchor: "right",
        yref: "y", y: bm.median_per100k, yanchor: "bottom", showarrow: false,
        font: { size: 10, color: "#6b7280" }
      }];
    }
    window.Plotly.react("c-benchmark", [
      {
        type: "scatter", mode: "markers", name: "income group", showlegend: false,
        x: bmPeers.map(x => x.dalys), y: bmPeers.map(x => x.per100k),
        text: bmPeers.map(hoverOf), hoverinfo: "text",
        marker: { color: "#9aa7b5", size: 9, opacity: 0.8 }
      },
      {
        type: "scatter", mode: "markers", name: "country", showlegend: false,
        x: bmSel.map(x => x.dalys), y: bmSel.map(x => x.per100k),
        text: bmSel.map(hoverOf), hoverinfo: "text",
        marker: { color: "#b08d3e", size: 14 }
      }
    ], bmLayout, PLOTLY_CFG);
  }

  async function boot() {
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      b.addEventListener("click", () => switchTab(b.dataset.tab));
    }
    $("fig-modal-close").addEventListener("click", closeModal);
    $("fig-modal").addEventListener("click", e => { if (e.target === $("fig-modal")) closeModal(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
    $("gal-back").addEventListener("click", hideSection);

    const get = async name => {
      // ?v=BUILD cache-buster; BUILD is stamped at publish time (see top).
      const r = await fetch("data/" + name + ".json?v=" + BUILD);
      if (!r.ok) throw new Error("failed to load data/" + name + ".json: " + r.status);
      return r.json();
    };
    const [dict, studies, geo, func, outcome, countries, content] = await Promise.all(
      ["dict", "studies", "geo", "function", "outcome", "countries", "content"].map(get));
    db = loadData({ dict, studies, geo, func, outcome, countries, content });

    GALLERY = db.content.gallery || [];
    FIG_INDEX = {};
    for (const sec of GALLERY) for (const f of sec.figs) FIG_INDEX[f.file] = f;

    renderOverview();
    renderOverviewCharts();
    renderGalleryIndex();
    renderFunnel();
    setupExplorerControls();
    refreshExplorer();
    setupCountryPane();
  }

  // err.message can embed data-derived text (URLs, server responses) —
  // textContent only, never el()'s innerHTML path.
  function showBootError(err) {
    const box = el("div", "loading-wrap");
    box.textContent = "Failed to start: " + err.message;
    document.querySelector("main").prepend(box);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => boot().catch(showBootError));
  } else {
    boot().catch(showBootError);
  }
}
