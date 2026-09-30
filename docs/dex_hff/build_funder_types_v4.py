"""Funder-type figure from the HSF extraction 29 Sept v4 file (interim: the rest
of the gallery still builds from hff_pipeline_full_single_model_final_v2.csv
via build_data.py / build_figures.py, because v4 carries no financing-function
tags yet).

research_funder is free text (CrossRef), ';'-separated. Each named funder is
assigned ONE type by the ordered keyword rules in FUNDER_TYPE_RULES (first
match wins); a study then counts once in every type any of its funders falls
in, so shares sum to >100%. Keyword-based, no LLM calls.

Outputs (never touches docs/data or docs/figures):
  docs/figures_v4/fig_funder_types_v4.png
  docs/data_v4/funder_types_v4.csv    funder string -> type, with study counts (audit)
  docs/data_v4/funder_types_v4.json   headline numbers + figure caption

Run: python docs/dex_hff/build_funder_types_v4.py
"""
import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # docs/
DEX = ROOT / "dex_hff"
FIGS = ROOT / "figures_v4"
DATA = ROOT / "data_v4"
FIGS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
V4 = DEX / "HSF extraction 29 Sept v4.xlsx"

# Style constants mirrored from build_figures.py so the figure sits in the same family.
ACCENT = "#1f5fa8"
GOLD = "#b08d3e"
INK = "#10243e"
SUBHEAD_COLOR = "#5a6472"
PAPER = "#faf9f6"
MUTED = "#c9cfd6"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.edgecolor": "#c9c3b3",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
})

PHARMA = "Pharmaceutical companies"
PRIVATE = "Other private companies"
NATGOV = "National governments"
SUBGOV = "Sub-national governments"
MULTI = "Multilateral & EU bodies"
NONPROFIT = "Foundations & non-profits"
ACADEMIC = "Universities, hospitals & institutes"
OTHER = "Unclassified"

# The three types the figure is about, and their colours.
HIGHLIGHT = {NATGOV: ACCENT, PHARMA: "#ca746a", PRIVATE: GOLD}

PHARMA_COMPANIES = [
    "pfizer", "novartis", "roche", "hoffmann", "genentech", "merck", "msd", "astrazeneca",
    "glaxo", "glaxosmithkline", "gsk", "sanofi", "bayer", "janssen", "johnson and johnson", "abbvie", "abbott",
    "eli lilly", "lilly", "bristol myers", "bristol-myers", "amgen", "gilead", "takeda",
    "boehringer", "novo nordisk", "biogen", "teva", "astellas", "daiichi", "eisai", "otsuka",
    "servier", "ipsen", "lundbeck", "wyeth", "baxter", "celgene", "regeneron", "alexion",
    "ucb", "grifols", "csl", "shire", "seqirus", "moderna", "biontech", "viatris", "mylan",
    "allergan", "chugai", "shionogi", "kyowa", "menarini", "chiesi", "recordati", "hikma",
    "biocon", "cipla", "zydus", "glenmark", "lupin", "sinovac", "sinopharm", "hengrui",
    "celltrion", "serum institute of india", "vertex", "jazz", "mundipharma", "bausch",
    "alcon", "sumitomo", "ferring", "orion", "gedeon richter", "krka", "sandoz", "stada",
    "phrma", "national pharmaceutical council",
]
NOT_A_COMPANY = r"(association|society|agency|management|school|faculty|college|universit|ministry|council|federation|commission|board)"

MULTILATERAL = [
    "world health organization", "who", "paho", "pan american health", "world bank", "unicef",
    "unaids", "undp", "unfpa", "unitaid", "united nations", "global fund", "gavi",
    "european commission", "european union", "horizon 2020", "h2020", "horizon europe",
    "seventh framework", "fp7", "framework programme", "european research council",
    "erc", "asian development bank", "african development bank", "inter american development bank",
    "international labour", "oecd", "international monetary fund", "imf", "erasmus",
    "interreg", "european regional development", "european social fund", "innovative medicines initiative",
    "european cooperation in science", "p4h",
]

SUBNATIONAL = [
    "province", "provincial", "municipal", "county", "city of", "state of", "prefecture",
    "fapesp", "fapemig", "faperj", "fapesc", "fundacao de amparo", "fundação de amparo",
    "generalitat", "junta de", "comunidad de madrid", "agaur", "agència de gestió", "agencia de gestio",
    "regione", "région", "region ", "fonds de recherche du québec", "fonds de recherche du quebec",
    "ontario", "alberta", "british columbia", "manitoba", "saskatchewan", "nova scotia", "quebec",
    "research foundation flanders", "fwo", "shanghai", "beijing", "guangdong", "zhejiang", "jiangsu",
    "shandong", "sichuan", "hubei", "hunan", "henan", "fujian", "anhui", "heilongjiang", "chongqing",
    "tianjin", "yunnan", "shaanxi", "shanxi", "jiangxi", "hebei", "liaoning", "jilin", "guangxi",
    "shenzhen", "guangzhou", "hangzhou", "wuhan", "chengdu", "nanjing", "queensland", "new south wales", "research bc", "eusko jaurlaritza", "landsting", "region stockholm", "fnrs",
    "new york state", "california", "state department of health", "state government",
    "bavarian", "bayerisch", "baden", "north rhine", "nordrhein", "lombardy", "lombardia", "catalonia",
]

NATIONAL_GOV = [
    "ministry", "ministerio", "ministério", "ministère", "ministero", "minister", "bundesministerium",
    "federal", "government", "department of health", "department of veterans", "veterans affairs",
    "department of defense", "department of education", "department of labor", "u s department",
    "us department", "department of health and human services", "hhs",
    "national institutes of health", "nih", "national institute of", "national institute on",
    "national institute for", "national cancer institute", "national heart", "national library of medicine",
    "national center for", "national centre for", "national center of", "fogarty",
    "centers for disease control", "cdc", "centers for medicare", "cms", "agency for healthcare research",
    "ahrq", "health resources and services", "samhsa", "substance abuse and mental health",
    "patient centered outcomes research", "pcori", "social security administration", "food and drug administration",
    "national science foundation", "national natural science foundation", "national social science fund",
    "national social science foundation", "national key", "china postdoctoral science foundation",
    "national research foundation", "science foundation", "research council", "research councils",
    "ukri", "uk research and innovation", "nihr", "national health service", "nhs",
    "national health and medical research", "nhmrc", "canadian institutes of health", "cihr",
    "social sciences and humanities research", "sshrc", "natural sciences and engineering",
    "health research board", "health and medical research fund", "zonmw", "zorginstituut",
    "instituto de salud carlos iii", "carlos iii", "deutsche forschungsgemeinschaft", "dfg", "bmbf",
    "agence nationale", "anr", "japan society for the promotion", "jsps", "japan agency for medical",
    "amed", "coordination for the improvement of higher education", "capes",
    "national council for scientific and technological", "cnpq", "conacyt", "conicet", "colciencias",
    "national health commission", "national healthcare security", "national medical research council",
    "korea health industry", "korea health technology", "national research", "academy of finland",
    "swedish research council", "forte", "vinnova", "vetenskapsrådet", "innovation fund denmark",
    "swiss national", "snsf", "austrian science fund", "fwf", "netherlands organisation", "nwo",
    "usaid", "agency for international development", "department for international development", "dfid",
    "foreign commonwealth", "fcdo", "foreign affairs", "giz", "deutsche gesellschaft für internationale",
    "jica", "sida", "norad", "danida", "idrc", "international development research centre",
    "global affairs canada", "australian aid", "dfat", "koica", "public health agency", "public health england",
    "department of science and technology", "department of biotechnology", "indian council of medical research",
    "icmr", "council of scientific", "science and technology development fund", "tubitak", "scientific and technological research council",
    "ministry of science", "national program", "national programme", "state key", "national major",
    "national office", "national agency", "national fund", "fundação para a ciência", "fct",
    "statens", "riksbankens", "research grants council", "health bureau", "medical research fund",
    "national health research", "higher education commission", "national council",
    "national health insurance", "health insurance review", "philippine health insurance",
    "health insurance system research", "kela", "forskningsråd", "forskningsrad", "nationalfonds",
    "aperfeiçoamento", "aperfeicoamento", "conselho nacional", "consejo nacional", "scholarship council",
    "nederlandse organisatie", "netherlands organization", "utviklingssamarbeid", "développement",
    "developpement", "utvecklingssamarbete", "international development", "canada research chairs",
    "health technology assessment programme", "health services and delivery research",
    "public health research programme", "health services research and development",
    "entwicklung und zusammenarbeit", "development and cooperation", "development cooperation",
    "science and technology agency", "science and technology council", "emergency plan for aids relief",
    "pepfar", "grand challenges canada", "akademischer austauschdienst", "daad", "nsf",
    "narodowe centrum", "council of social science research", "republic of china", "national science centre",
    "agencia estatal", "disease control and prevention agency", "national science council", "rijksinstituut",
    "fondo nacional", "nci", "mrc", "nimh", "chief scientist office", "unitatea executiva", "uefiscdi",
    "evidence based healthcare collaborating agency", "competition authority", "defense health agency",
    "japan international cooperation", "genome canada", "science and technology major project",
    "danmarks frie forskningsfond", "commonwealth scholarship", "robert koch",
]

NONPROFIT_NAMES = [
    "foundation", "fondation", "fundación", "fundacion", "fundação", "stiftung", "fondazione",
    "trust", "charit", "association", "society", "alliance", "initiative", "fund", "fonds",
    "commonwealth fund", "wellcome", "gates", "rockefeller", "arnold ventures", "kaiser family",
    "cancer research uk", "red cross", "save the children", "oxfam", "medecins", "médecins",
    "partners in health", "path", "clinton health", "china medical board", "atlantic philanthropies",
    "open society", "bloomberg philanthropies", "nuffield", "health foundation", "kings fund", "king's fund",
    "leverhulme", "volkswagen", "robert bosch", "novo nordisk foundation", "carnegie corporation",
    "rand corporation", "mitre", "consortium", "research to prevent blindness", "carlsbergfondet",
    "international growth centre",
]

ACADEMIC_NAMES = [
    "universit", "universid", "universit", "college", "school of", "hospital", "clinic",
    "institute", "institut", "istituto", "instituto", "research center", "research centre",
    "centre for", "center for", "academy", "academia", "karolinska", "vidyapeetham", "polytechnic",
    "medical center", "medical centre", "health sciences", "iit", "aiims", "ku leuven", "leuven", "hochschule", "max planck", "harvard",
]

COMPANY_SUFFIX = re.compile(
    r"\b(inc|ltd|llc|limited|corp|corporation|company|co|gmbh|plc|s a|sa|ag|bv|b v|pty|nv|srl|spa|kk)\b"
)
PRIVATE_NAMES = [
    "insurance", "unitedhealth", "optum", "aetna", "humana", "anthem", "blue cross", "blue shield",
    "cigna", "kaiser permanente", "ibm", "google", "microsoft", "amazon", "philips", "siemens", "medtronic",
    "iqvia", "deloitte", "mckinsey", "pwc", "ernst and young", "kpmg", "tencent", "alibaba", "huawei",
    "samsung", "toyota", "nestle", "nestlé", "unilever", "danone", "intel", "apple", "meta platforms",
    "boston scientific", "becton", "stryker", "edwards lifesciences", "zimmer", "fresenius", "baxter",
    "healthcare ltd", "consulting", "pharmacy chain", "walgreens", "cvs", "bank of", "industries",
    "achmea", "meso scale", "illumina", "sas institute",
]


def _fix_mojibake(s):
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def _norm(s):
    s = _fix_mojibake(s).lower().replace("&", " and ")
    s = re.sub(r"[.,\-'’()/]", " ", s)
    return " " + re.sub(r"\s+", " ", s).strip() + " "


def _has(text, terms):
    # Short terms (acronyms like "who", "nih", "cdc") match as whole words only.
    for t in terms:
        if len(t) <= 5 and " " not in t:
            if re.search(rf"\b{re.escape(t)}\b", text):
                return True
        elif t in text:
            return True
    return False


def funder_type(raw):
    t = _norm(raw)
    if _has(t, ["sas institute", "achmea", "illumina"]):
        return PRIVATE
    if _has(t, ["novo nordisk foundation", "novo nordisk fonden", "wellcome", "gates"]):
        return NONPROFIT
    if _has(t, PHARMA_COMPANIES) or (re.search(r"pharma(ceutic|\b)|biopharm", t) and not re.search(NOT_A_COMPANY, t)):
        return PHARMA
    if _has(t, MULTILATERAL):
        return MULTI
    # Before the geography rules, so e.g. "Shanghai Jiao Tong University" or
    # "Federal University of ..." isn't read as a government.
    if re.search(r"universi|vidyapeetham|leuven", t) and not re.search(r"ministry|grants commission", t):
        return ACADEMIC
    if _has(t, SUBNATIONAL):
        return SUBGOV
    if _has(t, NATIONAL_GOV):
        return NATGOV
    if _has(t, NONPROFIT_NAMES):
        return NONPROFIT
    if _has(t, ACADEMIC_NAMES):
        return ACADEMIC
    if _has(t, PRIVATE_NAMES) or COMPANY_SUFFIX.search(t):
        return PRIVATE
    return OTHER


df = pd.read_excel(V4, sheet_name="Data", usecols=["record_id", "year", "research_funder"], dtype=str)
N = len(df)
rf = df["research_funder"].fillna("").str.strip()
# "None.", "not funded", "No funding was received" etc. are statements, not funders.
NO_FUNDER = re.compile(r"^\W*(none|nil|n\W?a|not applicable|not funded|unfunded|self.funded)\W*$"
                       r"|^\W*(funded|funding|research|grants?|projekt deal)\W*$"
                       r"|\b(no|not|none|without)\b.{0,40}\b(fund|funding|funded|grant|financial support)",
                       re.IGNORECASE)


def funder_tokens(fn):
    fn = fn.replace("&amp;", "&")
    return {x.strip() for x in fn.split(";") if x.strip() and not NO_FUNDER.search(x.strip())}


rf = rf.where((rf != "Could not find"), "")
has_funder = rf.map(lambda fn: bool(funder_tokens(fn)))
funded = df[has_funder].copy()
N_FUNDED = len(funded)

type_study_n = Counter()
funder_rows = Counter()
funder_type_of = {}
unclassified_studies = 0
for fn in funded["research_funder"]:
    toks = funder_tokens(fn)
    types = set()
    for tok in toks:
        ft = funder_type_of.setdefault(tok, funder_type(tok))
        funder_rows[tok] += 1
        types.add(ft)
    for ft in types:
        type_study_n[ft] += 1
    if types == {OTHER}:
        unclassified_studies += 1

audit = pd.DataFrame(
    [(k, funder_type_of[k], n) for k, n in funder_rows.items()],
    columns=["research_funder_name", "funder_type", "n_studies"],
).sort_values(["funder_type", "n_studies"], ascending=[True, False])
audit.to_csv(DATA / "funder_types_v4.csv", index=False, encoding="utf-8-sig")


def share(n):
    return 100 * n / N_FUNDED


# --- figure: share of funded studies by funder type, three requested types highlighted
order = sorted([k for k in type_study_n if k != OTHER], key=lambda k: type_study_n[k])
order = [OTHER] + order  # unclassified pinned to the bottom
vals = [share(type_study_n[k]) for k in order]
colors = [HIGHLIGHT.get(k, MUTED) for k in order]

fig, ax = plt.subplots(figsize=(8.6, 5.2))
ax.barh(order, vals, color=colors, zorder=3, height=0.66)
for y, (k, v) in enumerate(zip(order, vals)):
    ax.text(v, y, f"  {v:.1f}%  ({type_study_n[k]:,})", va="center", fontsize=9,
            color=INK, fontweight="bold" if k in HIGHLIGHT else "normal")
for lbl in ax.get_yticklabels():
    if lbl.get_text() in HIGHLIGHT:
        lbl.set_fontweight("bold")
ax.set_xlim(0, max(vals) * 1.25)
ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
ax.set_xlabel("share of studies that name a funder")
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
ax.grid(axis="x", color="#e7e3da", linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

ng, ph, pr = (share(type_study_n[k]) for k in (NATGOV, PHARMA, PRIVATE))
headline = "National governments fund most studies; industry funds few"
desc = "Share of studies naming each type of funder, among studies that report any funder."
finding = (f"National governments fund {ng:.0f}% of funded studies; pharmaceutical companies "
           f"{ph:.1f}% and other private companies {pr:.1f}%.")
# Header anchored to the figure (not the axes) so the long finding line doesn't
# squeeze the plot area; the axes are placed explicitly underneath it.
fig.set_size_inches(10.5, 6.2)
fig.subplots_adjust(left=0.27, right=0.97, top=0.80, bottom=0.12)
fig.text(0.01, 0.975, headline, fontsize=16, fontweight="bold", color=INK, ha="left", va="top")
fig.text(0.01, 0.905, desc, fontsize=10.5, color=SUBHEAD_COLOR, ha="left", va="top")
fig.text(0.01, 0.862, finding, fontsize=10.5, fontweight="bold", color=INK, ha="left", va="top")
footnote = (f"Base: {N_FUNDED:,} of {N:,} studies ({100 * N_FUNDED / N:.1f}%) report a research funder "
            f"(HSF extraction 29 Sept v4; research_funder from CrossRef).\nEach named funder is assigned one type by "
            f"keyword rules; a study naming funders of several types counts in each, so shares sum to >100%.\n"
            f"National governments include ministries, national agencies, public research councils and bilateral aid "
            f"agencies. Pharmaceutical companies\ninclude their corporate foundations. Funder-to-type mapping: "
            f"docs/data_v4/funder_types_v4.csv.")
fig.text(0.01, 0.02, footnote, fontsize=8, color=SUBHEAD_COLOR, ha="left", va="top", linespacing=1.4)
fname = "fig_funder_types_v4.png"
fig.savefig(FIGS / fname, dpi=150, bbox_inches="tight")
plt.close(fig)

summary = {
    "source": V4.name, "n_studies": N, "n_funded": N_FUNDED,
    "n_distinct_funder_strings": len(funder_rows),
    "studies_by_type": {k: type_study_n[k] for k in order[::-1]},
    "share_of_funded_pct": {k: round(share(type_study_n[k]), 1) for k in order[::-1]},
    "figure": {"file": fname, "title": headline, "caption": f"{desc} {finding}"},
}
(DATA / "funder_types_v4.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"\nStudies whose funders are ALL unclassified: {unclassified_studies:,}")
print("\nTop unclassified funders:")
print(audit[audit.funder_type == OTHER].nlargest(40, "n_studies").to_string(index=False))
for k in (PHARMA, PRIVATE, NATGOV):
    print(f"\nTop {k}:")
    print(audit[audit.funder_type == k].nlargest(25, "n_studies").to_string(index=False))
