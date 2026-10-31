# -*- coding: utf-8 -*-
"""
GC Route & Caniveaux Pro — collecte, analyse et gestion de données d'un projet routier
(terrassements, chaussée, assainissement, caniveaux, ouvrages hydrauliques).
Lancement :  streamlit run App.py

Résultats indicatifs (méthodes simplifiées) : à valider par un ingénieur / bureau d'études.
"""
import io
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="GC Route & Caniveaux Pro", page_icon="🛣️", layout="wide",
                   initial_sidebar_state="expanded")

# ===================== THÈME =====================
JAUNE = "#FFC400"
JAUNE_CLAIR = "#FFF3B0"
CREME = "#FFFBE6"
NOIR = "#14213D"
ROUGE = "#D62828"
VERT = "#2A9D4F"
ORANGE = "#F77F00"
BLEU = "#1D4ED8"
GRIS = "#6B7280"
PALETTE = [NOIR, JAUNE, ROUGE, BLEU, VERT, ORANGE, GRIS]

CSS = f"""
<style>
.stApp {{ background: linear-gradient(180deg,#FFFEF5 0%,{CREME} 55%,#FFF6CC 100%); color:{NOIR}; }}
h1,h2,h3,h4,h5 {{ color:{NOIR} !important; font-weight:800 !important; }}
[data-testid="stSidebar"] {{ background:{NOIR}; border-right:5px solid {JAUNE}; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] small {{ color:{JAUNE_CLAIR} !important; }}
.brand {{ background:{JAUNE}; color:{NOIR}; font-weight:900; font-size:1.2rem; padding:12px 14px;
          border-radius:12px; text-align:center; margin-bottom:8px; border:2px solid {JAUNE_CLAIR}; }}
.hero {{ background:linear-gradient(110deg,{JAUNE} 0%,#FFE35C 60%,{JAUNE_CLAIR} 100%);
         border:3px solid {NOIR}; border-radius:16px 16px 0 0; padding:16px 26px; }}
.hero h1 {{ margin:0; color:{NOIR} !important; font-size:1.9rem; }}
.hero p {{ margin:4px 0 0; color:{NOIR}; font-weight:600; }}
.hazard {{ height:12px; border:3px solid {NOIR}; border-top:0; border-radius:0 0 16px 16px; margin-bottom:18px;
           background:repeating-linear-gradient(45deg,{NOIR} 0 14px,{JAUNE} 14px 28px); background-size:40px 100%;
           animation:slide 1.2s linear infinite; }}
@keyframes slide {{ from {{ background-position:0 0; }} to {{ background-position:40px 0; }} }}
[data-testid="stMetric"] {{ background:#FFFFFF; border:2px solid {NOIR}; border-left:10px solid {JAUNE};
          padding:10px 16px; border-radius:12px; box-shadow:4px 4px 0 {NOIR}22; }}
[data-testid="stMetricValue"] {{ color:{NOIR}; font-weight:800; }}
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {{
    background:{JAUNE}; color:{NOIR}; border:2px solid {NOIR}; font-weight:800; border-radius:10px; }}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {{
    background:{NOIR}; color:{JAUNE}; border-color:{JAUNE}; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{ background:#FFFFFF; border:2px solid {NOIR}; border-radius:10px 10px 0 0;
    padding:8px 16px; font-weight:700; color:{NOIR}; }}
.stTabs [aria-selected="true"] {{ background:{JAUNE}; }}
.note {{ background:{NOIR}; color:{JAUNE_CLAIR}; padding:10px 16px; border-radius:10px; border-left:8px solid {JAUNE};
         margin:8px 0 14px; font-size:0.95rem; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def _wide():
    try:
        v = tuple(int(x) for x in st.__version__.split(".")[:2])
    except Exception:
        v = (0, 0)
    return {"width": "stretch"} if v >= (1, 50) else {"use_container_width": True}


WIDE = _wide()
_PN = [0]


# ===================== OUTILS =====================
def hero(titre, sous=""):
    st.markdown(f"<div class='hero'><h1>{titre}</h1><p>{sous}</p></div><div class='hazard'></div>",
                unsafe_allow_html=True)


def note(txt):
    st.markdown(f"<div class='note'>{txt}</div>", unsafe_allow_html=True)


def fnum(x, default=0.0):
    try:
        v = float(x)
        return default if math.isnan(v) else v
    except Exception:
        return default


def fmt(x, nd=2):
    try:
        return f"{x:,.{nd}f}".replace(",", " ")
    except Exception:
        return str(x)


def num(df, col):
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def verdict(cond, ok_msg, ko_msg):
    (st.success if cond else st.error)(("✅ " + ok_msg) if cond else ("❌ " + ko_msg))


def pplot(fig, height=420):
    _PN[0] += 1
    fig.update_layout(height=height, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFDF2", font=dict(color=NOIR),
                      colorway=PALETTE, margin=dict(l=20, r=20, t=55, b=20), title_font=dict(size=16, color=NOIR))
    fig.update_xaxes(gridcolor="#EADFA6", zerolinecolor="#C9B96A")
    fig.update_yaxes(gridcolor="#EADFA6", zerolinecolor="#C9B96A")
    try:
        st.plotly_chart(fig, key=f"pl{_PN[0]}", **WIDE)
    except TypeError:
        st.plotly_chart(fig, key=f"pl{_PN[0]}")


def show_df(df, **kw):
    try:
        st.dataframe(df, hide_index=True, **WIDE, **kw)
    except TypeError:
        st.dataframe(df, hide_index=True, **kw)


# ===================== SCHÉMAS =====================
COLS = {
    "releves": ["Date", "PK (m)", "Paramètre", "Valeur", "Unité", "Opérateur", "Remarque"],
    "journal": ["Date", "Météo", "Effectif", "Activités", "Observations"],
    "compactage": ["Date", "PK (m)", "Couche", "Densité sèche (t/m³)", "OPM (t/m³)", "Teneur en eau (%)", "w OPM (%)"],
    "cbr": ["Date", "PK (m)", "Couche", "CBR (%)"],
    "metre": ["Lot", "Désignation", "Unité", "Quantité", "PU"],
    "taches": ["Tâche", "Début", "Durée (j)", "Avancement (%)", "Responsable", "Prédécesseurs"],
    "risques": ["Risque", "Phase", "Probabilité", "Gravité", "Mesure de maîtrise"],
    "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
    "profil": ["PK (m)", "Terrain (m)", "Projet (m)", "Largeur plateforme (m)"],
    "reseau": ["Tronçon", "Aire propre (ha)", "C", "Longueur (m)", "Pente (%)", "Section", "b ou D (m)", "H (m)",
               "Talus m", "n Manning", "Amont"],
    "trafic": ["Type de véhicule", "Véh/jour", "Essieux simples", "Charge essieu simple (kN)", "Essieux tandem",
               "Charge tandem (kN)"],
    "degr": ["Section", "Type", "Sévérité", "Surface (m²)"],
}
DATES = {"releves": ["Date"], "journal": ["Date"], "compactage": ["Date"], "cbr": ["Date"], "taches": ["Début"]}
NUMS = {
    "releves": ["PK (m)", "Valeur"], "journal": ["Effectif"],
    "compactage": ["PK (m)", "Densité sèche (t/m³)", "OPM (t/m³)", "Teneur en eau (%)", "w OPM (%)"],
    "cbr": ["PK (m)", "CBR (%)"], "metre": ["Quantité", "PU"], "taches": ["Durée (j)", "Avancement (%)"],
    "risques": ["Probabilité", "Gravité"], "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
    "profil": ["PK (m)", "Terrain (m)", "Projet (m)", "Largeur plateforme (m)"],
    "reseau": ["Aire propre (ha)", "C", "Longueur (m)", "Pente (%)", "b ou D (m)", "H (m)", "Talus m", "n Manning"],
    "trafic": ["Véh/jour", "Essieux simples", "Charge essieu simple (kN)", "Essieux tandem", "Charge tandem (kN)"],
    "degr": ["Surface (m²)"],
}
LABELS = {
    "releves": "Relevés de contrôle", "journal": "Journal de chantier", "compactage": "Essais de compactage",
    "cbr": "Essais CBR", "metre": "Métré", "taches": "Planning", "risques": "Risques HSE", "ev": "Suivi coûts",
    "profil": "Profil en long", "reseau": "Réseau caniveaux", "trafic": "Trafic poids lourds",
    "degr": "Dégradations",
}
LAYERS = ["Remblai", "Couche de forme", "Fondation (GNT)", "Base (GNT)"]
METEO = ["Ensoleillé", "Nuageux", "Pluie légère", "Pluie forte", "Vent fort", "Forte chaleur"]
CATEGORIES = ["Autoroute / 2×2 voies", "Route nationale", "Route départementale", "Route communale",
              "Voie urbaine", "Piste / desserte"]
SECTIONS = ["Rectangulaire", "Trapézoïdal", "Triangulaire", "Circulaire (buse)"]
PARAMS = {"Densité in situ (% OPM)": "%", "Température enrobé": "°C", "Épaisseur de couche": "cm",
          "Dévers mesuré": "%", "Teneur en eau": "%", "Orniérage": "mm", "IRI": "m/km",
          "Déflexion (Benkelman)": "1/100 mm", "Largeur de plateforme": "m"}
TOLERANCES = {"Densité in situ (% OPM)": (95, None), "Température enrobé": (130, 170), "Dévers mesuré": (2.0, 3.0),
              "Orniérage": (None, 15), "IRI": (None, 3.0)}
MANNING = {"PVC / PEHD (0,011)": 0.011, "Béton lisse (0,013)": 0.013, "Béton brut / maçonnerie (0,015)": 0.015,
           "Béton ancien (0,017)": 0.017, "Enrochements (0,030)": 0.030, "Terre propre (0,025)": 0.025,
           "Terre enherbée (0,035)": 0.035}
DEGR_W = {"Faïençage (fatigue)": 1.0, "Fissuration": 0.5, "Nid-de-poule": 1.2, "Ornières": 0.9,
          "Ressuage": 0.4, "Arrachement / désenrobage": 0.6, "Affaissement de rive": 0.9}
SEV = {"Faible": 0.4, "Moyenne": 0.7, "Forte": 1.0}
ZR_TAB = {50: 0.0, 75: -0.674, 80: -0.841, 85: -1.037, 90: -1.282, 95: -1.645, 99: -2.327}
V_TAB = [40, 50, 60, 70, 80, 90, 100, 110, 120]
F_TAB = [0.17, 0.16, 0.15, 0.14, 0.14, 0.13, 0.12, 0.11, 0.09]
D_DEP = {40: 285, 50: 345, 60: 407, 70: 482, 80: 541, 90: 605, 100: 670, 110: 728, 120: 792}
CLASSES_BETON = ["C20/25", "C25/30", "C30/37", "C35/45", "C40/50"]


def coerce(df, key):
    d = df.copy()
    for c in COLS[key]:
        if c not in d.columns:
            d[c] = None
    d = d[COLS[key]]
    for c in DATES.get(key, []):
        d[c] = pd.to_datetime(d[c], errors="coerce").dt.date
        d[c] = d[c].where(d[c].notna(), None)
    for c in NUMS.get(key, []):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.reset_index(drop=True)


# ===================== ÉDITEUR DE TABLEAUX (état fiable) =====================
def bump(key):
    S = st.session_state
    S[f"{key}__v"] = S.get(f"{key}__v", 0) + 1


def set_df(key, df):
    st.session_state[key] = df
    bump(key)


def add_rows(key, new):
    S = st.session_state
    set_df(key, pd.concat([S[key], coerce(new, key)], ignore_index=True))


def _apply_delta(key):
    S = st.session_state
    ver = S.get(f"{key}__v", 0)
    delta = S.get(f"ed_{key}_{ver}") or {}
    df = S[key].astype(object).reset_index(drop=True)
    for r, ch in (delta.get("edited_rows") or {}).items():
        r = int(r)
        if r < len(df):
            for c, v in ch.items():
                if c in df.columns:
                    df.iat[r, df.columns.get_loc(c)] = v
    for row in delta.get("added_rows") or []:
        df = pd.concat([df, pd.DataFrame([row], columns=df.columns)], ignore_index=True)
    dels = [int(i) for i in (delta.get("deleted_rows") or []) if int(i) < len(df)]
    if dels:
        df = df.drop(index=dels).reset_index(drop=True)
    S[key] = coerce(df, key) if key in COLS else df.infer_objects()
    S[f"{key}__v"] = ver + 1


def editor(key, config=None, dynamic=True):
    """Tableau éditable : S[key] reste la source de vérité (mise à jour par callback)."""
    S = st.session_state
    kw = dict(key=f"ed_{key}_{S.get(f'{key}__v', 0)}", column_config=config or {},
              num_rows="dynamic" if dynamic else "fixed", hide_index=True, on_change=_apply_delta, args=(key,))
    try:
        return st.data_editor(S[key], **WIDE, **kw)
    except TypeError:
        return st.data_editor(S[key], **kw)


# ===================== PLANNING (chemin critique) =====================
def cpm(df):
    d = df.dropna(subset=["Tâche"]).copy()
    d["Tâche"] = d["Tâche"].astype(str)
    d = d.drop_duplicates("Tâche").reset_index(drop=True)
    d["Durée (j)"] = pd.to_numeric(d["Durée (j)"], errors="coerce").fillna(0).clip(lower=0)
    names = d["Tâche"].tolist()
    dur = dict(zip(names, d["Durée (j)"]))
    preds = {n: [x.strip() for x in str(p).split(";") if x.strip() in dur and x.strip() != n]
             for n, p in zip(names, d["Prédécesseurs"].fillna(""))}
    order, state = [], {}

    def visit(n):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError(f"Boucle de dépendances autour de « {n} »")
        state[n] = 1
        for p in preds[n]:
            visit(p)
        state[n] = 2
        order.append(n)

    for n in names:
        visit(n)
    ES, EF = {}, {}
    for n in order:
        ES[n] = max([EF[p] for p in preds[n]], default=0.0)
        EF[n] = ES[n] + dur[n]
    T = max(EF.values(), default=0.0)
    succ = {n: [m for m in names if n in preds[m]] for n in names}
    LS, LF = {}, {}
    for n in reversed(order):
        LF[n] = min([LS[s] for s in succ[n]], default=T)
        LS[n] = LF[n] - dur[n]
    d["ES"] = d["Tâche"].map(ES)
    d["EF"] = d["Tâche"].map(EF)
    d["Marge (j)"] = d["Tâche"].map(lambda n: LS[n] - ES[n])
    d["Critique"] = d["Marge (j)"].abs() < 1e-9
    return d, T


# ===================== CALCULS : GÉOMÉTRIE =====================
def f_lat(V):
    return float(np.interp(V, V_TAB, F_TAB))


def rayon_min(V, e):
    return V ** 2 / (127.0 * (e + f_lat(V)))


def dist_arret(V, G=0.0, tr=2.5, a=3.4):
    """Distance d'arrêt (m). G pente en m/m (+ montée)."""
    return 0.278 * V * tr + V ** 2 / (254.0 * max(a / 9.81 + G, 0.05))


def devers_R(R, Rm, emax):
    if R <= Rm:
        return emax
    r = Rm / R
    return max(emax * (2 * r - r * r), 0.0)


def lmin_convexe(A, S, h1=1.08, h2=0.60):
    if A <= 0:
        return 0.0
    k = (math.sqrt(2 * h1) + math.sqrt(2 * h2)) ** 2
    L = A * S ** 2 / (100 * k)
    if L < S:
        L = 2 * S - 100 * k / A
    return max(L, 0.0)


def lmin_concave(A, S):
    if A <= 0:
        return 0.0
    L = A * S ** 2 / (120 + 3.5 * S)
    if L < S:
        L = 2 * S - (120 + 3.5 * S) / A
    return max(L, 0.0)


# ===================== CALCULS : TERRASSEMENTS =====================
def calc_terrassement(df, talus_d, talus_r, k):
    d = df.copy()
    for c in NUMS["profil"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["PK (m)", "Terrain (m)", "Projet (m)"]).sort_values("PK (m)").reset_index(drop=True)
    d["Largeur plateforme (m)"] = d["Largeur plateforme (m)"].fillna(10.0)
    d["h (m)"] = d["Projet (m)"] - d["Terrain (m)"]
    Ar, Ad = [], []
    for h, B in zip(d["h (m)"], d["Largeur plateforme (m)"]):
        if h > 0:
            Ar.append(h * (B + talus_r * h)); Ad.append(0.0)
        else:
            Ad.append(-h * (B - 0 + talus_d * -h)); Ar.append(0.0)
    d["Aire remblai (m²)"] = Ar
    d["Aire déblai (m²)"] = Ad
    rows, cum = [], 0.0
    ords = [0.0]
    for i in range(len(d) - 1):
        L = d["PK (m)"][i + 1] - d["PK (m)"][i]
        vd = (Ad[i] + Ad[i + 1]) / 2 * L
        vr = (Ar[i] + Ar[i + 1]) / 2 * L
        cum += vd * k - vr
        ords.append(cum)
        pente = (d["Projet (m)"][i + 1] - d["Projet (m)"][i]) / L * 100 if L > 0 else 0.0
        rows.append({"De PK": d["PK (m)"][i], "À PK": d["PK (m)"][i + 1], "Déblai (m³)": vd, "Remblai (m³)": vr,
                     "Pente projet (%)": pente})
    d["Ordonnée Bruckner (m³)"] = ords
    return d, pd.DataFrame(rows, columns=["De PK", "À PK", "Déblai (m³)", "Remblai (m³)", "Pente projet (%)"])


# ===================== CALCULS : TRAFIC / CHAUSSÉE =====================
def esal_calc(df, r, n, ddf, ldf):
    d = df.copy()
    for c in NUMS["trafic"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    d["CAM (ESAL/véh)"] = (d["Essieux simples"] * (d["Charge essieu simple (kN)"] / 80.0) ** 4
                           + d["Essieux tandem"] * (d["Charge tandem (kN)"] / 151.0) ** 4)
    d["ESAL/jour"] = d["CAM (ESAL/véh)"] * d["Véh/jour"]
    gf = float(n) if r == 0 else ((1 + r) ** n - 1) / r
    jour = float(d["ESAL/jour"].sum())
    return d, jour, gf, jour * 365 * gf * ddf * ldf


def mr_psi(cbr):
    return 1500.0 * cbr if cbr <= 10 else 3000.0 * cbr ** 0.65


def log_w18(SN, ZR, S0, dPSI, MR):
    return (ZR * S0 + 9.36 * math.log10(SN + 1) - 0.20
            + math.log10(dPSI / 2.7) / (0.40 + 1094 / (SN + 1) ** 5.19) + 2.32 * math.log10(MR) - 8.07)


def sn_required(W18, ZR, S0, dPSI, MR):
    target = math.log10(max(W18, 1.0))
    lo, hi = 0.1, 15.0
    if log_w18(hi, ZR, S0, dPSI, MR) < target:
        return float("nan")
    for _ in range(80):
        mid = (lo + hi) / 2
        if log_w18(mid, ZR, S0, dPSI, MR) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def min_thick_in(W18):
    for lim, ac, base in [(5e4, 1.0, 4.0), (1.5e5, 2.0, 4.0), (5e5, 2.5, 4.0), (2e6, 3.0, 6.0), (7e6, 3.5, 6.0)]:
        if W18 < lim:
            return ac, base
    return 4.0, 6.0


def aashto_design(W18, ZR, S0, dPSI, MR_sg, MR_ssb, MR_base, a1, a2, a3, m2, m3):
    s3 = sn_required(W18, ZR, S0, dPSI, MR_sg)
    s2 = sn_required(W18, ZR, S0, dPSI, MR_ssb)
    s1 = sn_required(W18, ZR, S0, dPSI, MR_base)
    if any(math.isnan(x) for x in (s1, s2, s3)):
        return None
    acmin, bmin = min_thick_in(W18)
    D1c = math.ceil(max(s1 / a1, acmin) * 2.54 * 2) / 2
    SN1 = a1 * D1c / 2.54
    D2c = math.ceil(max((s2 - SN1) / (a2 * m2), bmin) * 2.54)
    SN2 = SN1 + a2 * m2 * D2c / 2.54
    D3 = max((s3 - SN2) / (a3 * m3), 0.0)
    D3c = math.ceil(D3 * 2.54) if D3 > 0 else 0
    return {"SN1": s1, "SN2": s2, "SN3": s3, "D1": D1c, "D2": D2c, "D3": D3c}


def sn_provided(d1, d2, d3, a1, a2, a3, m2, m3):
    return (a1 * d1 + a2 * m2 * d2 + a3 * m3 * d3) / 2.54


def aashto_group(F, LL, PI):
    if F <= 35:
        if F <= 15 and PI <= 6:
            g = "A-1-a"
        elif F <= 25 and PI <= 6:
            g = "A-1-b"
        elif LL <= 40:
            g = "A-2-4" if PI <= 10 else "A-2-6"
        else:
            g = "A-2-5" if PI <= 10 else "A-2-7"
    else:
        if LL <= 40:
            g = "A-4" if PI <= 10 else "A-6"
        else:
            g = "A-5" if PI <= 10 else ("A-7-5" if PI <= LL - 30 else "A-7-6")
    t1 = max(min(F, 75) - 35, 0) * (0.2 + 0.005 * (LL - 40))
    t2 = 0.01 * (max(min(F, 55), 15) - 15) * (max(min(PI, 30), 10) - 10)
    if g in ("A-1-a", "A-1-b", "A-2-4", "A-2-5"):
        gi = 0
    elif g in ("A-2-6", "A-2-7"):
        gi = t2
    else:
        gi = t1 + t2
    return g, int(round(max(gi, 0)))


# ===================== CALCULS : HYDRAULIQUE =====================
def tc_kirpich(L, S):
    return 0.0195 * L ** 0.77 * S ** -0.385


def tc_passini(A_ha, L, S):
    return 60 * 0.108 * ((A_ha / 100) * (L / 1000)) ** (1 / 3) / math.sqrt(S)


def tc_ventura(A_ha, S):
    return 7.62 * math.sqrt((A_ha / 100) / S)


def sec_props(kind, y, b, m, H):
    if kind == "Rectangulaire":
        return b * y, b + 2 * y, b
    if kind == "Trapézoïdal":
        return (b + m * y) * y, b + 2 * y * math.sqrt(1 + m * m), b + 2 * m * y
    if kind == "Triangulaire":
        return m * y * y, 2 * y * math.sqrt(1 + m * m), 2 * m * y
    D = b
    y = min(max(y, 1e-6), D)
    th = 2 * math.acos(1 - 2 * y / D)
    return D * D / 8 * (th - math.sin(th)), D * th / 2, D * math.sin(th / 2)


def q_manning(kind, y, b, m, H, S, n):
    A, P, _ = sec_props(kind, y, b, m, H)
    if A <= 0 or P <= 0:
        return 0.0
    return A * (A / P) ** (2 / 3) * math.sqrt(S) / n


def hmax_of(kind, b, H):
    return b if kind.startswith("Circ") else H


def y_normal(kind, Q, b, m, H, S, n):
    ymax = 0.938 * b if kind.startswith("Circ") else H
    if q_manning(kind, ymax, b, m, H, S, n) < Q:
        return ymax, False
    lo, hi = 1e-5, ymax
    for _ in range(70):
        mid = (lo + hi) / 2
        if q_manning(kind, mid, b, m, H, S, n) < Q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, True


def hyd_status(ok, V, y, Hh, kind, vmin, vmax, rev, remp):
    if not ok:
        return "❌ Capacité insuffisante"
    if kind.startswith("Circ"):
        if y / Hh > remp:
            return "⚠️ Remplissage excessif"
    elif Hh - y < rev:
        return "⚠️ Revanche insuffisante"
    if V < vmin:
        return "⚠️ V faible (dépôts)"
    if V > vmax:
        return "⚠️ V forte (érosion)"
    return "✅ OK"


def width_at(kind, z, b, m, H):
    if kind == "Rectangulaire":
        return b
    if kind == "Trapézoïdal":
        return b + 2 * m * z
    if kind == "Triangulaire":
        return 2 * m * z
    z = min(max(z, 0), b)
    return b * math.sin(math.acos(1 - 2 * z / b))


def fig_section(kind, b, H, m, y=None):
    Hh = hmax_of(kind, b, H)
    zs = np.linspace(0, Hh, 60)
    w = np.array([width_at(kind, z, b, m, Hh) for z in zs])
    xs = np.concatenate([-w[::-1] / 2, w / 2, [-w[-1] / 2]])
    ys = np.concatenate([zs[::-1], zs, [zs[-1]]])
    fig = go.Figure()
    if y is not None and y > 0:
        zw = np.linspace(0, min(y, Hh), 40)
        ww = np.array([width_at(kind, z, b, m, Hh) for z in zw])
        fig.add_trace(go.Scatter(x=np.concatenate([-ww[::-1] / 2, ww / 2]), y=np.concatenate([zw[::-1], zw]),
                                 fill="toself", fillcolor="rgba(29,78,216,0.45)", line=dict(color=BLEU),
                                 name=f"Eau (y = {y:.2f} m)"))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=NOIR, width=4), name="Section"))
    fig.update_yaxes(scaleanchor="x", scaleratio=1, title="m")
    fig.update_layout(title="Section hydraulique")
    return fig


def reseau_calc(df, h):
    d = df.dropna(subset=["Tronçon"]).copy()
    d["Tronçon"] = d["Tronçon"].astype(str).str.strip()
    d = d.drop_duplicates("Tronçon").reset_index(drop=True)
    names = list(d["Tronçon"])
    idx = {n: i for i, n in enumerate(names)}
    ups = {n: [x.strip() for x in str(a).split(";") if x.strip() in idx and x.strip() != n]
           for n, a in zip(names, d["Amont"].fillna(""))}
    order, state = [], {}

    def visit(n):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError(n)
        state[n] = 1
        for u in ups[n]:
            visit(u)
        state[n] = 2
        order.append(n)

    try:
        for n in names:
            visit(n)
    except ValueError as ex:
        return None, f"Boucle dans le réseau autour de « {ex} »."
    res = {}
    for n in order:
        r = d.iloc[idx[n]]
        A0, C0 = fnum(r["Aire propre (ha)"]), fnum(r["C"], 0.8)
        L, S = max(fnum(r["Longueur (m)"], 10.0), 1.0), max(fnum(r["Pente (%)"], 1.0), 0.05) / 100
        kind = r["Section"] if r["Section"] in SECTIONS else "Rectangulaire"
        b, H, m = fnum(r["b ou D (m)"], 0.5), fnum(r["H (m)"], 0.5), fnum(r["Talus m"], 0.0)
        nm = max(fnum(r["n Manning"], 0.015), 0.008)
        A = A0 + sum(res[u]["A"] for u in ups[n])
        CA = C0 * A0 + sum(res[u]["CA"] for u in ups[n])
        Ce = CA / A if A > 0 else C0
        tc = max([res[u]["tc_end"] for u in ups[n]] + [h["t_ent"]])
        i = h["a"] * max(tc, 5.0) ** (-h["b"])
        Q = Ce * i * A / 360.0 * (1 + h["marge"])
        Hh = hmax_of(kind, b, H)
        y, ok = y_normal(kind, Q, b, m, H, S, nm)
        Ar, _, T = sec_props(kind, y, b, m, H)
        V = Q / Ar if Ar > 0 else 0.0
        Fr = V / math.sqrt(9.81 * Ar / T) if T > 0 and Ar > 0 else 0.0
        Qf = q_manning(kind, Hh if not kind.startswith("Circ") else 0.938 * b, b, m, H, S, nm)
        res[n] = {"A": A, "CA": CA, "tc_end": tc + (L / V / 60 if V > 0.05 else 0.0),
                  "row": {"Tronçon": n, "Aire cumulée (ha)": A, "C équivalent": Ce, "tc (min)": tc, "i (mm/h)": i,
                          "Q (L/s)": Q * 1000, "Capacité (L/s)": Qf * 1000, "y normal (m)": y, "V (m/s)": V,
                          "Froude": Fr, "Remplissage (%)": y / Hh * 100,
                          "Statut": hyd_status(ok, V, y, Hh, kind, h["vmin"], h["vmax"], h["rev"], h["remp"])}}
    return pd.DataFrame([res[n]["row"] for n in names]), None


def izzard_T(Q, n, Sx, S):
    return (Q * n / (0.376 * Sx ** (5 / 3) * math.sqrt(S))) ** (3 / 8)


def izzard_Q(T, n, Sx, S):
    return 0.376 / n * Sx ** (5 / 3) * math.sqrt(S) * T ** (8 / 3)


# ===================== CALCULS : BÉTON ARMÉ (caniveaux, dalots) =====================
def beton_props(classe):
    fck = float(str(classe).replace("C", "").split("/")[0])
    return dict(fck=fck, fcd=fck / 1.5, fctm=0.30 * fck ** (2 / 3))


def aire_barre(phi):
    return math.pi * phi ** 2 / 4.0


def flexion_rect(M_kNm, b, d, fck, fyk, dp=None):
    fcd, fyd = fck / 1.5, fyk / 1.15
    M = abs(M_kNm) * 1e6
    mu = M / (b * d ** 2 * fcd)
    res = dict(mu=mu, mu_lim=0.295, As=0.0, As2=0.0, double=False)
    if M == 0:
        return res
    if mu <= 0.295:
        xi = 1 - math.sqrt(1 - 2 * mu)
        res["As"] = M / (d * (1 - xi / 2) * fyd)
    else:
        dp = dp or 0.1 * d
        z_lim = d * (1 - 0.36 / 2)
        M_lim = 0.295 * b * d ** 2 * fcd
        res["As2"] = (M - M_lim) / ((d - dp) * fyd)
        res["As"] = M_lim / (z_lim * fyd) + res["As2"]
        res["double"] = True
    return res


def vrd_c(b, d, fck, As):
    rho = min(As / (b * d), 0.02)
    k = min(2.0, 1 + math.sqrt(200.0 / d))
    v = 0.18 / 1.5 * k * (100 * rho * fck) ** (1 / 3)
    return max(v, 0.035 * k ** 1.5 * math.sqrt(fck)) * b * d / 1e3


def as_min_flex(b, d, fck, fyk):
    return max(0.26 * 0.30 * fck ** (2 / 3) / fyk * b * d, 0.0013 * b * d)


def choisir_armature(As, h):
    """As en mm²/m ; h en mm. Retourne texte HA φ @ s."""
    if As <= 0:
        return "—"
    smax = min(3 * h, 400)
    for phi in (8, 10, 12, 14, 16, 20, 25):
        s = math.floor(1000 * aire_barre(phi) / As / 25) * 25
        if s >= 100:
            return f"HA{phi} @ {int(min(s, smax))}"
    return "HA25 @ 100 (section à augmenter)"


# ===================== CONTRÔLE QUALITÉ / ENTRETIEN =====================
def compaction_df(df):
    d = df.copy()
    for c in NUMS["compactage"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["Compactage (% OPM)"] = d["Densité sèche (t/m³)"] / d["OPM (t/m³)"] * 100
    d["Écart w (pts)"] = d["Teneur en eau (%)"] - d["w OPM (%)"]
    return d.dropna(subset=["Couche", "Compactage (% OPM)"])


def seuil_map(seuils, col):
    return dict(zip(seuils["Couche"], pd.to_numeric(seuils[col], errors="coerce")))


def compaction_summary(df, seuils):
    d, sm = compaction_df(df), seuil_map(seuils, "Compactage min (% OPM)")
    rows = []
    for cl, g in d.groupby("Couche"):
        v = g["Compactage (% OPM)"].values
        sv = fnum(sm.get(cl), 95.0)
        s = float(v.std(ddof=1)) if len(v) > 1 else float("nan")
        ok = v.mean() >= sv and v.min() >= sv - 2
        rows.append({"Couche": cl, "n": len(v), "Moyenne (% OPM)": round(v.mean(), 1), "Min (% OPM)": round(v.min(), 1),
                     "Écart-type": round(s, 2) if s == s else None, "Seuil": sv,
                     "Statut": "✅ Conforme" if ok else "❌ Non conforme"})
    return pd.DataFrame(rows, columns=["Couche", "n", "Moyenne (% OPM)", "Min (% OPM)", "Écart-type", "Seuil", "Statut"])


def cbr_summary(df, seuils):
    d = df.copy()
    d["CBR (%)"] = pd.to_numeric(d["CBR (%)"], errors="coerce")
    d = d.dropna(subset=["Couche", "CBR (%)"])
    sm = seuil_map(seuils, "CBR min (%)")
    rows = []
    for cl, g in d.groupby("Couche"):
        v = g["CBR (%)"].values
        s = float(v.std(ddof=1)) if len(v) > 1 else 0.0
        ck = v.mean() - 1.28 * s
        sv = fnum(sm.get(cl), 5.0)
        rows.append({"Couche": cl, "n": len(v), "CBR moyen": round(v.mean(), 1), "CBR min": round(v.min(), 1),
                     "CBR caractéristique": round(ck, 1), "Exigence": sv,
                     "Statut": "✅ Conforme" if ck >= sv else "❌ Non conforme"})
    return pd.DataFrame(rows, columns=["Couche", "n", "CBR moyen", "CBR min", "CBR caractéristique", "Exigence", "Statut"])


def degr_index(df, surf):
    d = df.dropna(subset=["Section", "Type"]).copy()
    d["Surface (m²)"] = pd.to_numeric(d["Surface (m²)"], errors="coerce").fillna(0.0)
    d["Déduction"] = (d["Type"].map(DEGR_W).fillna(0.5) * d["Sévérité"].map(SEV).fillna(0.7)
                      * d["Surface (m²)"] / max(surf, 1.0) * 100)
    g = d.groupby("Section", as_index=False).agg(**{"Surface dégradée (m²)": ("Surface (m²)", "sum"),
                                                     "Déduction": ("Déduction", "sum")})
    g["Indice d'état"] = (100 - g["Déduction"]).clip(0, 100)
    g["Classe"] = pd.cut(g["Indice d'état"], [-1, 40, 55, 70, 85, 101],
                         labels=["Mauvais", "Médiocre", "Moyen", "Bon", "Très bon"]).astype(str)
    return d, g


def metre_totals(df):
    d = df.copy()
    d["Quantité"], d["PU"] = num(d, "Quantité"), num(d, "PU")
    d["Total"] = d["Quantité"] * d["PU"]
    d["Lot"] = d["Lot"].fillna("Divers").astype(str)
    return d


# ===================== ÉTAT INITIAL =====================
def init_state():
    S = st.session_state
    if "init" in S:
        return
    today = date.today()
    rng = np.random.default_rng(7)
    S.projet = dict(nom="Route de desserte RN-12 — Lot 2", moa="Direction des Travaux Publics", lieu="",
                    categorie="Route départementale", longueur=2000.0, largeur=7.0, vitesse=80,
                    budget=3_200_000.0, debut=today - timedelta(days=60), fin=today + timedelta(days=300),
                    devise="€")
    # Relevés
    base = {"Densité in situ (% OPM)": (97.5, 1.5), "Température enrobé": (148, 9), "Épaisseur de couche": (6.1, 0.4),
            "Dévers mesuré": (2.5, 0.25), "Teneur en eau": (6.5, 0.8)}
    rows = []
    for i in range(15):
        p = list(base)[i % 5]
        mu, sd = base[p]
        rows.append({"Date": today - timedelta(days=30 - 2 * i), "PK (m)": 100.0 * (i % 8), "Paramètre": p,
                     "Valeur": round(float(mu + rng.normal(0, sd)), 2), "Unité": PARAMS[p],
                     "Opérateur": "Labo chantier", "Remarque": ""})
    S.releves = coerce(pd.DataFrame(rows), "releves")
    # Journal
    acts = ["Décapage et débroussaillage", "Terrassement déblais PK0–PK400", "Remblai et compactage",
            "Pose buses Ø800 PK350", "Réglage couche de forme", "Mise en œuvre fondation GNT"]
    S.journal = coerce(pd.DataFrame([{
        "Date": today - timedelta(days=10 - 2 * i), "Météo": METEO[i % 3], "Effectif": int(18 + rng.integers(0, 14)),
        "Activités": a, "Observations": "RAS" if i % 2 == 0 else "Arrêt 2 h (pluie)"} for i, a in enumerate(acts)]),
        "journal")
    # Compactage / CBR
    comp, cbr = [], []
    opm = [1.95, 2.05, 2.25, 2.30]
    wopt = [11.0, 9.0, 6.0, 5.5]
    mean_c = [96.5, 98.0, 99.0, 99.3]
    mean_b, sd_b = [9, 32, 52, 92], [1.5, 4, 6, 8]
    for li, layer in enumerate(LAYERS):
        for j in range(4):
            pk = 100.0 * j + float(rng.integers(0, 90))
            dt = today - timedelta(days=40 - 6 * li - j)
            comp.append({"Date": dt, "PK (m)": pk, "Couche": layer,
                         "Densité sèche (t/m³)": round(opm[li] * rng.normal(mean_c[li], 1.0) / 100, 3),
                         "OPM (t/m³)": opm[li], "Teneur en eau (%)": round(wopt[li] + rng.normal(0, 0.7), 1),
                         "w OPM (%)": wopt[li]})
            cbr.append({"Date": dt, "PK (m)": pk, "Couche": layer,
                        "CBR (%)": round(float(rng.normal(mean_b[li], sd_b[li])), 1)})
    S.compactage = coerce(pd.DataFrame(comp), "compactage")
    S.cbr = coerce(pd.DataFrame(cbr), "cbr")
    S.seuils = pd.DataFrame({"Couche": LAYERS, "Compactage min (% OPM)": [95.0, 97.0, 98.0, 98.0],
                             "CBR min (%)": [5.0, 20.0, 30.0, 80.0]})
    # Métré
    mt = [("01 Installation et dégagement", "Installation de chantier", "forfait", 1, 60000),
          ("01 Installation et dégagement", "Décapage et débroussaillage", "m²", 22000, 1.2),
          ("02 Terrassements", "Déblais", "m³", 8500, 6), ("02 Terrassements", "Remblais compactés", "m³", 7000, 8),
          ("02 Terrassements", "Mise en dépôt", "m³", 1500, 5), ("02 Terrassements", "Couche de forme", "m³", 4200, 22),
          ("03 Chaussée", "Fondation GNT", "m³", 4000, 26), ("03 Chaussée", "Base GNT", "m³", 3000, 30),
          ("03 Chaussée", "Imprégnation", "m²", 20000, 1.2), ("03 Chaussée", "Couche d'accrochage", "m²", 14000, 0.6),
          ("03 Chaussée", "Béton bitumineux BB", "t", 1974, 95),
          ("04 Assainissement", "Caniveaux béton", "ml", 3500, 85), ("04 Assainissement", "Buses Ø800", "ml", 120, 210),
          ("04 Assainissement", "Dalots", "ml", 40, 780), ("04 Assainissement", "Têtes d'ouvrage", "u", 8, 1500),
          ("04 Assainissement", "Avaloirs", "u", 24, 450), ("05 Signalisation", "Marquage au sol", "m²", 1100, 9),
          ("05 Signalisation", "Panneaux", "u", 40, 190), ("05 Signalisation", "Glissières de sécurité", "ml", 600, 55),
          ("06 Divers", "Essais et contrôle", "forfait", 1, 45000)]
    S.metre = coerce(pd.DataFrame(mt, columns=COLS["metre"]), "metre")
    # Planning
    tk = [("Installation de chantier", 10, "Entreprise", "", 100), ("Dégagement / décapage", 12, "Entreprise",
          "Installation de chantier", 100), ("Terrassements généraux", 40, "Terrassier", "Dégagement / décapage", 70),
          ("Ouvrages hydrauliques (buses, dalots)", 25, "Ouvrages", "Dégagement / décapage", 40),
          ("Caniveaux et fossés", 35, "Assainissement", "Terrassements généraux", 10),
          ("Couche de forme", 20, "Terrassier", "Terrassements généraux;Ouvrages hydrauliques (buses, dalots)", 0),
          ("Fondation GNT", 18, "Chaussée", "Couche de forme", 0), ("Base GNT", 15, "Chaussée", "Fondation GNT", 0),
          ("Imprégnation + accrochage", 5, "Chaussée", "Base GNT", 0), ("Béton bitumineux", 12, "Enrobés",
          "Imprégnation + accrochage", 0), ("Signalisation et équipements", 15, "Signalisation",
          "Béton bitumineux;Caniveaux et fossés", 0), ("Réception", 5, "MOE / MOA", "Signalisation et équipements", 0)]
    tdf = pd.DataFrame([{"Tâche": a, "Début": today, "Durée (j)": b, "Avancement (%)": e, "Responsable": c,
                         "Prédécesseurs": d} for a, b, c, d, e in tk])
    sched, _ = cpm(tdf)
    tdf["Début"] = [S.projet["debut"] + timedelta(days=int(v)) for v in sched["ES"]]
    S.taches = coerce(tdf, "taches")
    rk = [("Collision engins / circulation publique", "Installation", 3, 5, "Signalisation temporaire, homme-trafic"),
          ("Renversement d'engin (talus, remblai)", "Terrassement", 2, 5, "Plateforme stable, guidage"),
          ("Écrasement piéton / recul d'engins", "Terrassement", 3, 5, "Alarme de recul, zones piétonnes"),
          ("Brûlures / fumées de bitume", "Revêtement", 3, 3, "EPI, limitation de température"),
          ("Éboulement de tranchée (caniveaux, buses)", "Assainissement", 2, 5, "Blindage, talutage"),
          ("Poussières / bruit des compacteurs", "Terrassement", 4, 2, "Arrosage, protections auditives"),
          ("Arrachement de réseaux enterrés", "Terrassement", 2, 4, "DICT, détection, sondages")]
    S.risques = coerce(pd.DataFrame(rk, columns=COLS["risques"]), "risques")
    B = S.projet["budget"]
    S.ev = coerce(pd.DataFrame({"Mois": list(range(1, 9)),
                                "PV cumulé": [B * x for x in (.04, .12, .25, .42, .58, .74, .88, 1.0)],
                                "EV cumulée": [B * x for x in (.035, .11, .23, .38, .52)] + [np.nan] * 3,
                                "AC cumulé": [B * x for x in (.037, .115, .24, .40, .55)] + [np.nan] * 3}), "ev")
    pk = np.arange(0, 401, 20.0)
    S.profil = coerce(pd.DataFrame({"PK (m)": pk,
                                    "Terrain (m)": np.round(100 + 2.2 * np.sin(pk / 70) - 0.002 * pk, 2),
                                    "Projet (m)": np.round(100.2 - 0.0015 * pk + 0.3 * np.sin(pk / 150), 2),
                                    "Largeur plateforme (m)": 10.0}), "profil")
    S.reseau = coerce(pd.DataFrame([
        ("C1", 1.2, 0.70, 120, 1.0, "Trapézoïdal", 0.4, 0.5, 1.0, 0.015, ""),
        ("C2", 0.8, 0.65, 100, 1.2, "Trapézoïdal", 0.4, 0.5, 1.0, 0.015, "C1"),
        ("C3", 0.6, 0.90, 80, 0.8, "Rectangulaire", 0.5, 0.6, 0.0, 0.013, "C2"),
        ("C4", 1.5, 0.60, 150, 1.5, "Trapézoïdal", 0.5, 0.6, 1.0, 0.017, ""),
        ("B1", 0.2, 0.90, 25, 1.0, "Circulaire (buse)", 0.8, 0.8, 0.0, 0.013, "C3;C4")],
        columns=COLS["reseau"]), "reseau")
    S.trafic = coerce(pd.DataFrame([("Camion 2 essieux", 150, 2, 75, 0, 0), ("Camion 3 essieux", 60, 1, 70, 1, 160),
                                    ("Semi-remorque 5 essieux", 40, 1, 65, 2, 170)], columns=COLS["trafic"]), "trafic")
    S.degr = coerce(pd.DataFrame([
        ("PK 0+000–0+200", "Fissuration", "Moyenne", 35), ("PK 0+000–0+200", "Faïençage (fatigue)", "Faible", 20),
        ("PK 0+200–0+400", "Nid-de-poule", "Moyenne", 6), ("PK 0+200–0+400", "Faïençage (fatigue)", "Forte", 45),
        ("PK 0+200–0+400", "Ornières", "Moyenne", 60), ("PK 0+400–0+600", "Ressuage", "Faible", 30),
        ("PK 0+600–0+800", "Fissuration", "Faible", 15)], columns=COLS["degr"]), "degr")
    S.hydro = dict(a=300.0, b=0.56, T=10.0, t_ent=5.0, vmin=0.6, vmax=4.0, rev=0.10, remp=0.8, marge=0.0)
    S.tparams = dict(r=0.035, n=20, ddf=0.5, ldf=1.0)
    S.terr = dict(td=1.0, tr=1.5, k=0.9)
    S.idf = pd.DataFrame({"T (ans)": [2.0, 5.0, 10.0, 25.0, 50.0, 100.0], "a": [210.0, 260.0, 300.0, 350.0, 395.0, 440.0],
                          "b": [0.58, 0.57, 0.56, 0.55, 0.55, 0.54]})
    S.surfaces = pd.DataFrame({"Surface": ["Chaussée revêtue", "Accotements", "Talus et espaces verts", "Terrain naturel amont"],
                               "Aire (ha)": [1.4, 0.8, 1.2, 3.0], "C": [0.90, 0.60, 0.35, 0.30]})
    S.proctor = pd.DataFrame({"w (%)": [8.0, 10.0, 12.0, 14.0, 16.0], "γd (t/m³)": [1.95, 2.03, 2.07, 2.04, 1.97]})
    S.phases = pd.DataFrame({"Phase": ["A (axe principal)", "B (axe secondaire)", "C (tourne-à-gauche)"],
                             "Flux critique (uvp/h)": [450.0, 380.0, 150.0],
                             "Flux de saturation (uvp/h)": [1800.0, 1800.0, 1600.0]})
    S.couches = pd.DataFrame({"Couche": ["Couche de forme", "Fondation GNT", "Base GNT", "Béton bitumineux BB"],
                              "Épaisseur (cm)": [30.0, 20.0, 15.0, 6.0], "Largeur (m)": [10.0, 9.0, 8.0, 7.0],
                              "Unité": ["m³", "m³", "m³", "t"], "Densité (t/m³)": [2.0, 2.2, 2.25, 2.35],
                              "PU": [22.0, 26.0, 30.0, 95.0]})
    S.init = True


# ===================== PAGE : TABLEAU DE BORD =====================
def page_dashboard():
    S = st.session_state
    P = S.projet
    hero("🛣️ Tableau de bord du projet", f"{P['nom']} — {P['categorie']}")
    with st.expander("✏️ Informations générales du projet"):
        c1, c2, c3 = st.columns(3)
        P["nom"] = c1.text_input("Nom du projet", P["nom"])
        P["moa"] = c2.text_input("Maître d'ouvrage", P["moa"])
        P["lieu"] = c3.text_input("Localisation", P["lieu"])
        c1, c2, c3, c4 = st.columns(4)
        P["categorie"] = c1.selectbox("Catégorie de route", CATEGORIES, index=CATEGORIES.index(P["categorie"]))
        P["longueur"] = float(c2.number_input("Longueur du projet (m)", 50.0, 500000.0, float(P["longueur"]), 50.0))
        P["largeur"] = float(c3.number_input("Largeur de chaussée (m)", 3.0, 30.0, float(P["largeur"]), 0.5))
        vi = V_TAB.index(P["vitesse"]) if P["vitesse"] in V_TAB else 4
        P["vitesse"] = int(c4.selectbox("Vitesse de référence (km/h)", V_TAB, index=vi))
        c1, c2, c3, c4 = st.columns(4)
        P["budget"] = float(c1.number_input("Budget cible HT", 0.0, 1e10, float(P["budget"]), 10000.0))
        P["debut"] = c2.date_input("Début des travaux", P["debut"])
        P["fin"] = c3.date_input("Fin contractuelle", P["fin"])
        devs = ["€", "FCFA", "$", "MAD", "DZD"]
        P["devise"] = c4.selectbox("Devise", devs, index=devs.index(P["devise"]) if P["devise"] in devs else 0)
    dev = P["devise"]
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() > 0 else 0.0
    mt = metre_totals(S.metre)
    tot = float(mt["Total"].sum())
    comp = compaction_summary(S.compactage, S.seuils)
    rs, _ = reseau_calc(S.reseau, S.hydro)
    n_ok = int(rs["Statut"].str.startswith("✅").sum()) if rs is not None and len(rs) else 0
    n_tot = len(rs) if rs is not None else 0
    r = S.risques
    n_crit = int((num(r, "Probabilité") * num(r, "Gravité") >= 15).sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avancement global", f"{avanc:.1f} %")
    c2.metric("Estimation du métré HT", f"{fmt(tot, 0)} {dev}",
              f"{(tot - P['budget']) / P['budget'] * 100:+.1f} % vs budget" if P["budget"] else None, delta_color="inverse")
    c3.metric("Coût au km", f"{fmt(tot / (P['longueur'] / 1000), 0)} {dev}/km")
    c4.metric("Jours avant échéance", f"{(P['fin'] - date.today()).days} j")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Couches compactage conformes", f"{int((comp['Statut'] == '✅ Conforme').sum())} / {len(comp)}")
    c2.metric("Tronçons de caniveaux OK", f"{n_ok} / {n_tot}")
    c3.metric("Risques critiques (≥15)", n_crit)
    c4.metric("Linéaire", f"{P['longueur'] / 1000:.2f} km")
    g1, g2 = st.columns(2)
    with g1:
        tt = t.copy()
        tt["Avancement (%)"] = num(tt, "Avancement (%)")
        fig = px.bar(tt, x="Avancement (%)", y="Tâche", orientation="h", range_x=[0, 100], color="Avancement (%)",
                     color_continuous_scale=[[0, JAUNE_CLAIR], [1, NOIR]], title="Avancement par tâche")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(coloraxis_showscale=False)
        pplot(fig, 460)
    with g2:
        lots = mt.groupby("Lot", as_index=False)["Total"].sum()
        if len(lots) and lots["Total"].sum() > 0:
            pplot(px.pie(lots, names="Lot", values="Total", hole=0.5, title="Répartition du coût par lot",
                         color_discrete_sequence=[NOIR, JAUNE, ROUGE, BLEU, VERT, ORANGE, GRIS]), 460)
    d, _ = calc_terrassement(S.profil, S.terr["td"], S.terr["tr"], S.terr["k"])
    if len(d):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["PK (m)"], y=d["Terrain (m)"], name="Terrain naturel", line=dict(color=GRIS, width=3)))
        fig.add_trace(go.Scatter(x=d["PK (m)"], y=d["Projet (m)"], name="Ligne rouge (projet)",
                                 line=dict(color=ROUGE, width=4)))
        fig.update_layout(title="Profil en long", xaxis_title="PK (m)", yaxis_title="Altitude (m)")
        pplot(fig, 340)


# ===================== PAGE : COLLECTE =====================
def page_collecte():
    S = st.session_state
    hero("📥 Collecte de données de chantier", "Journal, relevés de contrôle par PK, import / fusion de fichiers")
    t1, t2, t3 = st.tabs(["📓 Journal de chantier", "📏 Relevés et mesures", "📎 Import / fusion"])
    with t1:
        with st.form("form_journal", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", date.today())
            m = c2.selectbox("Météo", METEO)
            e = c3.number_input("Effectif présent", 0, 1000, 25)
            act = st.text_area("Activités réalisées")
            obs = st.text_area("Incidents / observations")
            if st.form_submit_button("➕ Ajouter l'entrée"):
                add_rows("journal", pd.DataFrame([{"Date": d, "Météo": m, "Effectif": e, "Activités": act,
                                                   "Observations": obs}]))
                st.rerun()
        editor("journal", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                           "Météo": st.column_config.SelectboxColumn("Météo", options=METEO)})
        j = S.journal.copy()
        j["Effectif"] = pd.to_numeric(j["Effectif"], errors="coerce")
        j = j.dropna(subset=["Date", "Effectif"])
        if len(j):
            pplot(px.bar(j.sort_values("Date"), x="Date", y="Effectif", color="Météo", title="Effectif journalier",
                         color_discrete_sequence=PALETTE), 320)
    with t2:
        with st.form("form_releve", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d = c1.date_input("Date du relevé", date.today())
            pk = c2.number_input("PK (m)", 0.0, 1e6, 0.0, 10.0)
            p = c3.selectbox("Paramètre", list(PARAMS))
            v = c4.number_input("Valeur", value=0.0, step=0.1, format="%.2f")
            c1, c2 = st.columns(2)
            op = c1.text_input("Opérateur")
            rem = c2.text_input("Remarque")
            if st.form_submit_button("➕ Enregistrer le relevé"):
                add_rows("releves", pd.DataFrame([{"Date": d, "PK (m)": pk, "Paramètre": p, "Valeur": v,
                                                   "Unité": PARAMS[p], "Opérateur": op, "Remarque": rem}]))
                st.rerun()
        editor("releves", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                           "Paramètre": st.column_config.SelectboxColumn("Paramètre", options=list(PARAMS))})
        r = S.releves.copy()
        r["Valeur"] = pd.to_numeric(r["Valeur"], errors="coerce")
        r = r.dropna(subset=["Date", "Valeur", "Paramètre"])
        if len(r):
            sel = st.selectbox("Paramètre à analyser", sorted(r["Paramètre"].unique()))
            rr = r[r["Paramètre"] == sel].sort_values("Date")
            fig = px.line(rr, x="Date", y="Valeur", markers=True, title=f"{sel} — évolution",
                          color_discrete_sequence=[NOIR])
            lo, hi = TOLERANCES.get(sel, (None, None))
            for lim in (lo, hi):
                if lim is not None:
                    fig.add_hline(y=lim, line_dash="dash", line_color=ROUGE)
            pplot(fig, 340)
    with t3:
        key = st.selectbox("Jeu de données cible", list(LABELS), format_func=lambda k: LABELS[k])
        st.caption("Colonnes attendues : " + " | ".join(COLS[key]))
        up = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"])
        if up is not None:
            try:
                df = pd.read_csv(up, sep=None, engine="python") if up.name.lower().endswith(".csv") else pd.read_excel(up)
                manque = [c for c in COLS[key] if c not in df.columns]
                if manque:
                    st.error("Colonnes manquantes : " + ", ".join(manque))
                else:
                    df = coerce(df, key)
                    show_df(df.head(20))
                    mode = st.radio("Mode", ["Ajouter aux données existantes", "Remplacer les données"], horizontal=True)
                    if st.button("📥 Importer"):
                        set_df(key, pd.concat([S[key], df], ignore_index=True) if mode.startswith("Ajouter") else df)
                        st.rerun()
            except Exception as ex:
                st.error(f"Lecture impossible : {ex}")


# ===================== PAGE : GÉOMÉTRIE =====================
def fig_travers(nv, lw, acc, p_ch, p_acc, fh, fb, talus, ep):
    Lc = nv * lw / 2.0

    def ys(x):
        x = abs(x)
        return -p_ch * x if x <= Lc else -p_ch * Lc - p_acc * (x - Lc)

    xe = Lc + acc
    xr = [0, Lc, xe, xe + talus * fh, xe + talus * fh + fb, xe + 2 * talus * fh, xe + 2 * talus * fh + 2.0]
    yr = [0, ys(Lc), ys(xe), ys(xe) - fh, ys(xe) - fh, ys(xe), ys(xe)]
    X = [-x for x in xr[::-1]] + xr[1:]
    Y = yr[::-1] + yr[1:]
    fig = go.Figure()
    xs = np.linspace(-xe, xe, 81)
    top = np.array([ys(x) for x in xs])
    cum, cols = 0.0, [NOIR, JAUNE, "#F4A261", "#A8A29E"]
    for (nom, e), col in zip(ep, cols):
        t0, t1 = cum, cum + e / 100.0
        fig.add_trace(go.Scatter(x=np.concatenate([xs, xs[::-1]]), y=np.concatenate([top - t0, (top - t1)[::-1]]),
                                 fill="toself", fillcolor=col, line=dict(color=NOIR, width=1), name=f"{nom} ({e:g} cm)"))
        cum = t1
    fig.add_trace(go.Scatter(x=X, y=Y, mode="lines", line=dict(color=ROUGE, width=3), name="Surface"))
    fig.update_yaxes(scaleanchor="x", scaleratio=1, title="m")
    fig.update_layout(title="Profil en travers type")
    return fig


def page_geometrie():
    P = st.session_state.projet
    hero("🧭 Géométrie routière", "Vitesse • rayons • dévers • clothoïdes • visibilité • profil en travers")
    t1, t2, t3, t4 = st.tabs(["🎯 Vitesse, rayons, dévers", "↪️ Courbe en plan", "👁️ Visibilité, courbes verticales",
                              "📏 Profil en travers"])
    vi = V_TAB.index(P["vitesse"]) if P["vitesse"] in V_TAB else 4
    with t1:
        c1, c2, c3 = st.columns(3)
        V = c1.selectbox("Vitesse de référence V (km/h)", V_TAB, index=vi, key="g_V")
        emax = c2.slider("Dévers maximal (%)", 4.0, 10.0, 7.0, 0.5) / 100
        G = c3.slider("Pente longitudinale (%)", -8.0, 8.0, 0.0, 0.5, key="g_G") / 100
        Rm = rayon_min(V, emax)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Frottement transversal f", f"{f_lat(V):.3f}")
        c2.metric("Rayon minimal Rm", f"{Rm:.0f} m")
        c3.metric("Distance d'arrêt", f"{dist_arret(V, G):.0f} m")
        c4.metric("Visibilité de dépassement", f"{D_DEP[V]} m")
        rows = [{"V (km/h)": v, "f": f_lat(v), "R min (m)": round(rayon_min(v, emax)),
                 "D arrêt (m)": round(dist_arret(v)), "D dépassement (m)": D_DEP[v]} for v in V_TAB]
        show_df(pd.DataFrame(rows))
        Rs = np.linspace(Rm, 8 * Rm, 60)
        fig = px.line(x=Rs, y=[devers_R(R, Rm, emax) * 100 for R in Rs], title="Dévers en fonction du rayon",
                      labels={"x": "Rayon (m)", "y": "Dévers (%)"}, color_discrete_sequence=[NOIR])
        fig.add_hline(y=2.5, line_dash="dash", line_color=ROUGE, annotation_text="dévers minimal 2,5 %")
        pplot(fig, 320)
    with t2:
        Rm = rayon_min(V, emax)
        c1, c2, c3 = st.columns(3)
        R = c1.number_input("Rayon R (m)", 30.0, 5000.0, 300.0, 10.0)
        dl = c1.number_input("Angle de déviation Δ (°)", 1.0, 179.0, 60.0, 1.0)
        bd = c2.number_input("Largeur pivotante (m)", 2.0, 10.0, 3.5, 0.25)
        rampe = c2.number_input("Rampe de dévers relative max (%)", 0.2, 2.0, 0.8, 0.1)
        e = max(devers_R(R, Rm, emax), 0.025)
        L_dev = (e + 0.025) * bd / (rampe / 100)
        L_min = max(L_dev, 0.556 * V, R / 9)
        A_min = math.sqrt(R * L_min)
        A = c3.slider("Paramètre A de clothoïde (m)", float(round(R / 3)), float(round(R)),
                      float(min(round(max(R / 3, A_min)), round(R))), 5.0)
        Lc = A ** 2 / R
        th = Lc / (2 * R)
        dr = math.radians(dl)
        T = R * math.tan(dr / 2)
        Ts = (R + Lc ** 2 / (24 * R)) * math.tan(dr / 2) + Lc / 2 - Lc ** 3 / (240 * R ** 2)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dévers adopté", f"{e * 100:.1f} %")
        c2.metric("Longueur mini de raccordement", f"{L_min:.0f} m")
        c3.metric("Longueur de clothoïde L", f"{Lc:.0f} m")
        c4.metric("Tangente (avec clothoïde)", f"{Ts:.1f} m")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tangente (arc seul)", f"{T:.1f} m")
        c2.metric("Développement arc", f"{R * dr:.1f} m")
        c3.metric("Flèche / externe E", f"{R * (1 / math.cos(dr / 2) - 1):.1f} m")
        c4.metric("Arc circulaire restant", f"{math.degrees(dr - 2 * th):.1f} °")
        verdict(Lc >= L_min, "Longueur de clothoïde suffisante.", "Clothoïde trop courte : augmenter A.")
        verdict(dr - 2 * th >= 0, "Arc circulaire central conservé.", "Δ trop faible pour cette clothoïde : réduire A.")
        phi = np.linspace(0, dr, 60)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=R * np.sin(phi), y=R * (1 - np.cos(phi)), name="Arc", line=dict(color=NOIR, width=4)))
        fig.add_trace(go.Scatter(x=[0, T, R * math.sin(dr)], y=[0, 0, R * (1 - math.cos(dr))], name="Tangentes",
                                 line=dict(color=ROUGE, dash="dash")))
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
        fig.update_layout(title="Schéma de la courbe (sans clothoïde)")
        pplot(fig, 380)
    with t3:
        c1, c2, c3 = st.columns(3)
        g1 = c1.number_input("Pente amont g1 (%)", -10.0, 10.0, 2.0, 0.1)
        g2 = c2.number_input("Pente aval g2 (%)", -10.0, 10.0, -3.0, 0.1)
        pvi = c3.number_input("Altitude du PVI (m)", 0.0, 3000.0, 100.0, 0.5)
        Sa = dist_arret(V, min(g1, g2, 0.0) / 100)
        A = abs(g2 - g1)
        convex = g2 < g1
        Lm = lmin_convexe(A, Sa) if convex else lmin_concave(A, Sa)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Type", "Convexe (sommet)" if convex else "Concave (creux)")
        c2.metric("Différence algébrique A", f"{A:.1f} %")
        c3.metric("L minimale", f"{Lm:.0f} m")
        c4.metric("K = L/A", f"{Lm / A:.0f}" if A > 0 else "—")
        L = st.number_input("Longueur adoptée L (m)", 20.0, 2000.0, float(max(round(Lm / 10) * 10, 60.0)), 10.0)
        x = np.linspace(0, L, 41)
        yb = pvi - g1 / 100 * L / 2
        z = yb + g1 / 100 * x + (g2 - g1) / 100 / (2 * L) * x ** 2
        fig = px.line(x=x, y=z, title="Courbe verticale (parabole)", labels={"x": "Abscisse (m)", "y": "Altitude (m)"},
                      color_discrete_sequence=[NOIR])
        pplot(fig, 320)
        verdict(L >= Lm, "Visibilité d'arrêt assurée.", "L inférieure au minimum : visibilité insuffisante.")
    with t4:
        c1, c2, c3 = st.columns(3)
        nv = c1.selectbox("Nombre de voies", [2, 4], key="g_nv")
        lw = c1.number_input("Largeur d'une voie (m)", 2.5, 4.0, float(P["largeur"] / 2), 0.05)
        acc = c2.number_input("Largeur d'accotement (m)", 0.0, 4.0, 1.5, 0.25)
        pch = c2.number_input("Pente transversale chaussée (%)", 1.5, 4.0, 2.5, 0.1) / 100
        pac = c2.number_input("Pente transversale accotement (%)", 2.0, 8.0, 4.0, 0.5) / 100
        fh = c3.number_input("Profondeur du fossé (m)", 0.2, 1.5, 0.5, 0.05)
        fb = c3.number_input("Largeur du fond de fossé (m)", 0.0, 2.0, 0.5, 0.1)
        tal = c3.number_input("Talus du fossé (H/V)", 0.5, 3.0, 1.5, 0.25)
        ep = [("Roulement BB", st.number_input("Roulement (cm)", 3.0, 15.0, 6.0, 0.5)),
              ("Base GNT", st.number_input("Base (cm)", 10.0, 30.0, 15.0, 1.0)),
              ("Fondation GNT", st.number_input("Fondation (cm)", 10.0, 40.0, 20.0, 1.0)),
              ("Forme", st.number_input("Couche de forme (cm)", 0.0, 60.0, 30.0, 5.0))]
        pplot(fig_travers(nv, lw, acc, pch, pac, fh, fb, tal, ep), 420)
        larg = nv * lw
        emprise = larg + 2 * (acc + 2 * tal * fh + fb + 1.0)
        c1, c2, c3 = st.columns(3)
        c1.metric("Largeur de chaussée", f"{larg:.2f} m")
        c2.metric("Plateforme", f"{larg + 2 * acc:.2f} m")
        c3.metric("Emprise approximative", f"{emprise:.1f} m")


# ===================== PAGE : PROFIL EN LONG =====================
def page_profil():
    S = st.session_state
    hero("⛰️ Profil en long et cubatures", "Aires déblai/remblai • volumes par moyenne des aires • diagramme de Bruckner")
    c1, c2, c3 = st.columns(3)
    S.terr["td"] = float(c1.number_input("Talus de déblai (H/V)", 0.25, 3.0, float(S.terr["td"]), 0.25))
    S.terr["tr"] = float(c2.number_input("Talus de remblai (H/V)", 0.5, 3.0, float(S.terr["tr"]), 0.25))
    S.terr["k"] = float(c3.number_input("Coefficient de réemploi (déblai → remblai)", 0.5, 1.3, float(S.terr["k"]), 0.05))
    note("Saisir les PK, l'altitude du terrain naturel, celle de la ligne rouge (projet) et la largeur de plateforme. "
         "Les sections mixtes (déblai et remblai simultanés) sont assimilées à leur signe dominant.")
    editor("profil")
    d, v = calc_terrassement(S.profil, S.terr["td"], S.terr["tr"], S.terr["k"])
    if len(d) < 2:
        st.info("Saisir au moins deux profils.")
        return
    vd, vr = float(v["Déblai (m³)"].sum()), float(v["Remblai (m³)"].sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Déblai total", f"{fmt(vd, 0)} m³")
    c2.metric("Remblai total", f"{fmt(vr, 0)} m³")
    solde = vd * S.terr["k"] - vr
    c3.metric("Solde (+ dépôt / − emprunt)", f"{fmt(solde, 0)} m³")
    c4.metric("Pente max du projet", f"{v['Pente projet (%)'].abs().max():.2f} %")
    verdict(v["Pente projet (%)"].abs().max() <= 8, "Pentes longitudinales ≤ 8 %.", "Pente > 8 % : à justifier.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["PK (m)"], y=d["Terrain (m)"], name="Terrain", line=dict(color=GRIS, width=3)))
    fig.add_trace(go.Scatter(x=d["PK (m)"], y=d["Projet (m)"], name="Projet", line=dict(color=ROUGE, width=4)))
    fig.update_layout(title="Profil en long", xaxis_title="PK (m)", yaxis_title="Altitude (m)")
    pplot(fig, 340)
    g1, g2 = st.columns(2)
    with g1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=d["PK (m)"], y=d["Aire déblai (m²)"], name="Déblai", marker_color=JAUNE))
        fig.add_trace(go.Bar(x=d["PK (m)"], y=-d["Aire remblai (m²)"], name="Remblai", marker_color=NOIR))
        fig.update_layout(title="Aires des profils (m²)", barmode="relative")
        pplot(fig, 340)
    with g2:
        fig = px.line(d, x="PK (m)", y="Ordonnée Bruckner (m³)", markers=True, title="Diagramme de Bruckner",
                      color_discrete_sequence=[NOIR])
        fig.add_hline(y=0, line_color=ROUGE, line_dash="dash")
        pplot(fig, 340)
    show_df(v.round(2))


# ===================== PAGE : SOLS ET TERRASSEMENT =====================
def page_sols():
    S = st.session_state
    hero("🌍 Sols et terrassement", "Proctor • classification AASHTO • rendement des engins")
    t1, t2, t3 = st.tabs(["🧪 Proctor", "🔬 Classification du sol", "🚜 Engins de terrassement"])
    with t1:
        editor("proctor")
        w = pd.to_numeric(S.proctor["w (%)"], errors="coerce")
        g = pd.to_numeric(S.proctor["γd (t/m³)"], errors="coerce")
        m = w.notna() & g.notna()
        w, g = w[m].values, g[m].values
        Gs = st.number_input("Densité des grains Gs", 2.4, 3.0, 2.68, 0.01)
        if len(w) >= 3:
            a, b, c = np.polyfit(w, g, 2)
            if a < 0:
                wo = -b / (2 * a)
                go_ = float(np.polyval([a, b, c], wo))
                e = Gs / go_ - 1
                c1, c2, c3 = st.columns(3)
                c1.metric("Teneur en eau optimale", f"{wo:.1f} %")
                c2.metric("Densité sèche max (OPM)", f"{go_:.3f} t/m³")
                c3.metric("Saturation à l'optimum", f"{wo / 100 * Gs / e * 100:.0f} %")
                X = st.slider("Objectif de compactage (% OPM)", 90.0, 100.0, 95.0, 0.5)
                disc = b * b - 4 * a * (c - X / 100 * go_)
                if disc >= 0:
                    r1, r2 = sorted([(-b + s * math.sqrt(disc)) / (2 * a) for s in (1, -1)])
                    st.info(f"Fenêtre de teneur en eau pour {X:g} % OPM : de {r1:.1f} % à {r2:.1f} %.")
                ww = np.linspace(w.min() - 1, w.max() + 3, 60)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=w, y=g, mode="markers", name="Essais", marker=dict(size=12, color=NOIR)))
                fig.add_trace(go.Scatter(x=ww, y=np.polyval([a, b, c], ww), name="Courbe ajustée",
                                         line=dict(color=JAUNE, width=4)))
                fig.add_trace(go.Scatter(x=ww, y=Gs / (1 + ww / 100 * Gs), name="Saturation 100 %",
                                         line=dict(color=BLEU, dash="dash")))
                fig.update_layout(title="Courbe Proctor", xaxis_title="w (%)", yaxis_title="γd (t/m³)")
                pplot(fig, 380)
            else:
                st.warning("L'ajustement n'a pas de maximum : revoir les points.")
        else:
            st.info("Saisir au moins 3 points.")
    with t2:
        c1, c2, c3 = st.columns(3)
        F = c1.number_input("Passant à 0,075 mm (%)", 0.0, 100.0, 40.0, 1.0)
        LL = c2.number_input("Limite de liquidité LL (%)", 0.0, 120.0, 35.0, 1.0)
        PI = c3.number_input("Indice de plasticité IP (%)", 0.0, 80.0, 12.0, 1.0)
        grp, gi = aashto_group(F, LL, PI)
        qual = {"A-1": "Excellent à bon", "A-2-4": "Bon", "A-2-5": "Bon", "A-2-6": "Moyen", "A-2-7": "Moyen",
                "A-4": "Passable", "A-5": "Médiocre", "A-6": "Médiocre", "A-7": "Médiocre à mauvais"}
        q = qual.get(grp[:3] if grp.startswith("A-1") else grp, qual.get(grp[:3], "Médiocre à mauvais"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Groupe AASHTO", grp)
        c2.metric("Indice de groupe", gi)
        c3.metric("Qualité comme plateforme", q)
        note("Classification simplifiée (AASHTO M145) : à confirmer par les essais complets d'identification.")
    with t3:
        c1, c2, c3 = st.columns(3)
        Vol = c1.number_input("Volume à déplacer (m³ en place)", 100.0, 5e6, 8500.0, 100.0)
        god = c1.number_input("Capacité du godet (m³)", 0.5, 8.0, 1.8, 0.1)
        cyc = c1.number_input("Temps de cycle de la pelle (s)", 10.0, 60.0, 25.0, 1.0)
        kr = c2.number_input("Coefficient de remplissage", 0.5, 1.2, 0.9, 0.05)
        ef = c2.number_input("Efficacité (min/h)", 30.0, 60.0, 50.0, 5.0)
        fo = c2.number_input("Foisonnement (%)", 0.0, 50.0, 25.0, 5.0) / 100
        cap = c3.number_input("Capacité d'un camion (m³ foisonnés)", 5.0, 30.0, 15.0, 1.0)
        dk = c3.number_input("Distance de transport (km)", 0.1, 30.0, 2.0, 0.1)
        vc = c3.number_input("Vitesse moyenne aller-retour (km/h)", 10.0, 60.0, 25.0, 5.0)
        hj = st.slider("Heures de travail par jour", 4.0, 12.0, 8.0, 0.5)
        Qf = 3600 / cyc * god * kr * ef / 60
        Qp = Qf / (1 + fo)
        tl = cap / Qf * 60
        cy = tl + 2 * dk / vc * 60 + 5
        nc = math.ceil(cy / tl)
        jours = Vol / (Qp * hj)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rendement pelle", f"{Qp:.0f} m³/h")
        c2.metric("Cycle camion", f"{cy:.1f} min")
        c3.metric("Camions nécessaires", nc)
        c4.metric("Durée estimée", f"{jours:.1f} j")


# ===================== PAGE : TRAFIC =====================
def page_trafic():
    S = st.session_state
    hero("🚛 Trafic", "Projection • charge d'essieux (ESAL) • carrefour à feux (Webster)")
    t1, t2, t3 = st.tabs(["📈 Projection et capacité", "⚖️ Essieux équivalents (ESAL)", "🚦 Carrefour à feux"])
    with t1:
        c1, c2, c3 = st.columns(3)
        tm = c1.number_input("TMJA à la mise en service (véh/j, 2 sens)", 100, 200000, 3500, 100)
        pl = c1.slider("Part de poids lourds (%)", 0.0, 60.0, 12.0, 0.5)
        r = c2.number_input("Croissance annuelle (%)", 0.0, 15.0, 3.5, 0.5) / 100
        n = int(c2.number_input("Durée de calcul (années)", 5, 40, 20, 1))
        k = c3.slider("Part de l'heure de pointe (% du TMJA)", 6.0, 16.0, 10.0, 0.5) / 100
        ds = c3.slider("Répartition directionnelle (%)", 50.0, 80.0, 60.0, 5.0) / 100
        E = c3.number_input("Équivalent uvp d'un poids lourd", 1.0, 6.0, 2.5, 0.5)
        cap = c1.number_input("Capacité d'une voie (uvp/h)", 800.0, 2400.0, 1700.0, 100.0)
        yrs = np.arange(0, n + 1)
        T = tm * (1 + r) ** yrs
        vc = T * k * ds * (1 + pl / 100 * (E - 1)) / cap
        c1, c2, c3 = st.columns(3)
        c1.metric(f"TMJA année {n}", f"{T[-1]:,.0f} véh/j".replace(",", " "))
        c2.metric("Poids lourds année 0", f"{tm * pl / 100:,.0f} PL/j".replace(",", " "))
        c3.metric("Rapport débit / capacité final", f"{vc[-1]:.2f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=yrs, y=T, name="TMJA", line=dict(color=NOIR, width=4)))
        fig.add_trace(go.Scatter(x=yrs, y=T * pl / 100, name="Poids lourds", line=dict(color=JAUNE, width=4)))
        fig.update_layout(title="Projection du trafic", xaxis_title="Année")
        pplot(fig, 330)
        fig = px.line(x=yrs, y=vc, labels={"x": "Année", "y": "v/c"}, title="Rapport débit / capacité (sens chargé)",
                      color_discrete_sequence=[NOIR])
        fig.add_hline(y=0.8, line_dash="dash", line_color=ROUGE, annotation_text="seuil 0,8")
        pplot(fig, 300)
    with t2:
        tp = S.tparams
        note("Charges en kN. Essieu de référence : 80 kN (simple) / 151 kN (tandem), loi de puissance 4.")
        editor("trafic")
        c1, c2, c3, c4 = st.columns(4)
        tp["r"] = float(c1.number_input("Croissance PL (%)", 0.0, 15.0, tp["r"] * 100, 0.5)) / 100
        tp["n"] = int(c2.number_input("Durée de calcul PL (ans)", 5, 40, int(tp["n"]), 1))
        tp["ddf"] = float(c3.slider("Répartition directionnelle", 0.3, 1.0, float(tp["ddf"]), 0.05))
        tp["ldf"] = float(c4.slider("Répartition par voie", 0.5, 1.0, float(tp["ldf"]), 0.05))
        d, jour, gf, w18 = esal_calc(S.trafic, tp["r"], tp["n"], tp["ddf"], tp["ldf"])
        c1, c2, c3 = st.columns(3)
        c1.metric("ESAL par jour (2 sens)", f"{jour:,.0f}".replace(",", " "))
        c2.metric("Facteur de croissance", f"{gf:.2f}")
        c3.metric("W18 de calcul", f"{w18:,.0f}".replace(",", " "))
        show_df(d[["Type de véhicule", "Véh/jour", "CAM (ESAL/véh)", "ESAL/jour"]].round(2))
        if len(d):
            pplot(px.bar(d, x="Type de véhicule", y="ESAL/jour", title="Contribution de chaque classe",
                         color_discrete_sequence=[JAUNE]), 300)
    with t3:
        editor("phases")
        ph = S.phases.copy()
        q = pd.to_numeric(ph["Flux critique (uvp/h)"], errors="coerce").fillna(0)
        s = pd.to_numeric(ph["Flux de saturation (uvp/h)"], errors="coerce").fillna(1800).replace(0, 1800)
        lp = st.number_input("Temps perdu par phase (s)", 2.0, 10.0, 4.0, 0.5)
        L = lp * len(ph)
        Y = float((q / s).sum())
        if len(ph) == 0 or Y >= 0.95:
            st.error("Carrefour saturé (Y ≥ 0,95) : ajouter des voies ou revoir les phases.")
        else:
            C0 = (1.5 * L + 5) / (1 - Y)
            C = math.ceil(C0 / 5) * 5
            ph["Vert effectif (s)"] = (C - L) * (q / s) / Y
            ph["Degré de saturation"] = q / (s * ph["Vert effectif (s)"] / C)
            c1, c2, c3 = st.columns(3)
            c1.metric("Y = Σ q/s", f"{Y:.2f}")
            c2.metric("Cycle optimal (Webster)", f"{C0:.0f} s")
            c3.metric("Cycle retenu", f"{C} s")
            show_df(ph.round(2))
            pplot(px.bar(ph, x="Phase", y="Vert effectif (s)", title="Temps de vert effectif",
                         color_discrete_sequence=[VERT]), 300)


# ===================== PAGE : CHAUSSÉE =====================
def page_chaussee():
    S = st.session_state
    tp = S.tparams
    hero("🛣️ Dimensionnement de la chaussée", "Méthode AASHTO 93 • nombre structural SN • épaisseurs par couche • durée de vie")
    _, _, _, w_auto = esal_calc(S.trafic, tp["r"], tp["n"], tp["ddf"], tp["ldf"])
    cb = S.cbr.copy()
    cb["CBR (%)"] = pd.to_numeric(cb["CBR (%)"], errors="coerce")
    cbm = cb[cb["Couche"] == "Remblai"]["CBR (%)"].mean()
    cbr_def = float(min(max(round(fnum(cbm, 8.0), 1), 2.0), 40.0))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Trafic et fiabilité")
        wm = st.number_input("W18 manuel (0 = calcul automatique)", 0.0, 1e9, 0.0, 10000.0)
        W18 = max(wm if wm > 0 else w_auto, 1e4)
        R = st.selectbox("Fiabilité (%)", list(ZR_TAB), index=4)
        S0 = st.slider("Écart-type global S0", 0.35, 0.50, 0.45, 0.01)
        pt = st.slider("Indice de service final pt", 1.5, 3.0, 2.5, 0.1)
    with c2:
        st.markdown("#### Sol support")
        cbr = st.number_input("CBR de la plateforme (%)", 2.0, 40.0, cbr_def, 0.5)
        MRsg = mr_psi(cbr)
        MRssb = st.number_input("Module sous-fondation (psi)", 5000.0, 40000.0, 15000.0, 1000.0)
        MRb = st.number_input("Module base (psi)", 10000.0, 60000.0, 30000.0, 1000.0)
    with c3:
        st.markdown("#### Coefficients structuraux")
        a1 = st.number_input("a1 béton bitumineux", 0.2, 0.6, 0.42, 0.01)
        a2 = st.number_input("a2 base GNT", 0.05, 0.25, 0.14, 0.01)
        a3 = st.number_input("a3 fondation GNT", 0.04, 0.2, 0.11, 0.01)
        m2 = st.slider("m2 (drainage base)", 0.6, 1.4, 1.0, 0.05)
        m3 = st.slider("m3 (drainage fondation)", 0.6, 1.4, 1.0, 0.05)
    dPSI = 4.2 - pt
    ZR = ZR_TAB[R]
    des = aashto_design(W18, ZR, S0, dPSI, MRsg, MRssb, MRb, a1, a2, a3, m2, m3)
    if des is None:
        st.error("Trafic trop élevé pour la méthode : revoir les hypothèses.")
        return
    cl = ("Très faible" if W18 < 5e4 else "Faible" if W18 < 5e5 else "Moyen" if W18 < 2e6 else "Fort" if W18 < 7e6
          else "Très fort" if W18 < 3e7 else "Exceptionnel")
    pf = ("Très mauvaise (S0)" if cbr < 3 else "Mauvaise (S1)" if cbr < 5 else "Moyenne (S2)" if cbr < 10
          else "Bonne (S3)" if cbr < 15 else "Très bonne (S4)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("W18 de calcul", f"{W18:,.0f}".replace(",", " "))
    c2.metric("Classe de trafic", cl)
    c3.metric("Plateforme", pf)
    c4.metric("SN requis (sol)", f"{des['SN3']:.2f}")
    st.subheader("Épaisseurs minimales calculées")
    show_df(pd.DataFrame({"Couche": ["Béton bitumineux", "Base GNT", "Fondation GNT"],
                          "Épaisseur mini (cm)": [des["D1"], des["D2"], des["D3"]]}))
    st.subheader("Structure retenue")
    c1, c2, c3 = st.columns(3)
    d1 = c1.number_input("Béton bitumineux (cm)", 0.0, 40.0, float(des["D1"]), 0.5)
    d2 = c2.number_input("Base GNT (cm)", 0.0, 60.0, float(des["D2"]), 1.0)
    d3 = c3.number_input("Fondation GNT (cm)", 0.0, 80.0, float(des["D3"]), 1.0)
    SNp = sn_provided(d1, d2, d3, a1, a2, a3, m2, m3)
    wall = 10 ** log_w18(SNp, ZR, S0, dPSI, MRsg)
    yearly = max(esal_calc(S.trafic, tp["r"], 1, tp["ddf"], tp["ldf"])[3] / 1.0, 1.0)
    r = tp["r"]
    life = wall / yearly if r == 0 else math.log(1 + wall * r / yearly) / math.log(1 + r)
    c1, c2, c3 = st.columns(3)
    c1.metric("SN fourni", f"{SNp:.2f}")
    c2.metric("ESAL admissible", f"{wall:,.0f}".replace(",", " "))
    c3.metric("Durée de vie estimée", f"{life:.1f} ans")
    verdict(SNp >= des["SN3"], "Structure suffisante vis-à-vis du sol support.", "SN fourni insuffisant : épaissir la structure.")
    fig = go.Figure()
    for nom, e, col in [("Béton bitumineux", d1, NOIR), ("Base GNT", d2, JAUNE), ("Fondation GNT", d3, "#F4A261")]:
        fig.add_trace(go.Bar(x=["Structure"], y=[e], name=f"{nom} ({e:g} cm)", marker_color=col))
    fig.update_layout(barmode="stack", title="Coupe de chaussée", yaxis_title="Épaisseur (cm)")
    fig.update_yaxes(autorange="reversed")
    pplot(fig, 340)
    cs = np.linspace(3, 30, 15)
    fig = go.Figure()
    for wv in (5e5, 2e6, 1e7):
        fig.add_trace(go.Scatter(x=cs, y=[sn_required(wv, ZR, S0, dPSI, mr_psi(c)) for c in cs], name=f"W18 = {wv:.0e}",
                                 mode="lines"))
    fig.update_layout(title="SN requis selon le CBR", xaxis_title="CBR (%)", yaxis_title="SN")
    pplot(fig, 320)
    note("AASHTO 93 : log W18 = ZR·S0 + 9,36·log(SN+1) − 0,2 + log(ΔPSI/2,7)/(0,4 + 1094/(SN+1)^5,19) + 2,32·log MR − 8,07.")


# ===================== PAGE : HYDROLOGIE =====================
def page_hydro():
    S = st.session_state
    h = S.hydro
    hero("🌧️ Hydrologie", "Pluie de projet (Montana) • temps de concentration • méthode rationnelle • bassin de rétention")
    t1, t2, t3 = st.tabs(["☔ Pluie de projet", "💧 Débit de bassin versant", "🏞️ Bassin de rétention"])
    with t1:
        note("Coefficients a, b d'exemple : à remplacer par ceux de la station pluviométrique locale. i (mm/h) = a · t^(−b), t en minutes.")
        editor("idf")
        idf = S.idf.copy()
        for c in idf.columns:
            idf[c] = pd.to_numeric(idf[c], errors="coerce")
        idf = idf.dropna()
        if len(idf) == 0:
            st.warning("Renseigner au moins une période de retour.")
            return
        Ts = [float(x) for x in idf["T (ans)"]]
        sel = st.selectbox("Période de retour de projet", Ts, index=Ts.index(10.0) if 10.0 in Ts else 0,
                           format_func=lambda v: f"{v:g} ans")
        row = idf[idf["T (ans)"] == sel].iloc[0]
        h["a"], h["b"], h["T"] = float(row["a"]), float(row["b"]), float(sel)
        ts = np.array([5, 10, 15, 30, 60, 120, 240, 360])
        fig = go.Figure()
        for _, r_ in idf.iterrows():
            fig.add_trace(go.Scatter(x=ts, y=r_["a"] * ts ** (-r_["b"]), name=f"T = {r_['T (ans)']:g} ans", mode="lines+markers"))
        fig.update_layout(title="Courbes intensité – durée – fréquence", xaxis_title="Durée (min)", yaxis_title="i (mm/h)",
                          xaxis_type="log")
        pplot(fig, 360)
        show_df(pd.DataFrame({"Durée (min)": ts, "Intensité (mm/h)": np.round(h["a"] * ts ** (-h["b"]), 1),
                              "Hauteur (mm)": np.round(h["a"] * ts ** (-h["b"]) * ts / 60, 1)}))
    with t2:
        editor("surfaces", dynamic=True)
        sf = S.surfaces.copy()
        A_s = pd.to_numeric(sf["Aire (ha)"], errors="coerce").fillna(0)
        C_s = pd.to_numeric(sf["C"], errors="coerce").fillna(0)
        A = float(A_s.sum())
        Ceq = float((A_s * C_s).sum() / A) if A > 0 else 0.0
        c1, c2, c3 = st.columns(3)
        L = c1.number_input("Plus long chemin hydraulique (m)", 20.0, 20000.0, 450.0, 10.0)
        pente = c2.number_input("Pente moyenne (%)", 0.1, 30.0, 2.0, 0.1) / 100
        meth = c3.selectbox("Formule de temps de concentration", ["Kirpich", "Passini", "Ventura", "Valeur imposée"])
        if A <= 0:
            st.warning("Surface nulle.")
            return
        tc = {"Kirpich": lambda: tc_kirpich(L, pente), "Passini": lambda: tc_passini(A, L, pente),
              "Ventura": lambda: tc_ventura(A, pente), "Valeur imposée": lambda: 15.0}[meth]()
        if meth == "Valeur imposée":
            tc = st.number_input("tc imposé (min)", 5.0, 600.0, 15.0, 1.0)
        tc = max(tc, 5.0)
        i = h["a"] * tc ** (-h["b"])
        Q = Ceq * i * A / 360.0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Surface totale", f"{A:.2f} ha")
        c2.metric("Coefficient C équivalent", f"{Ceq:.2f}")
        c3.metric("tc / intensité", f"{tc:.1f} min / {i:.0f} mm/h")
        c4.metric(f"Débit de pointe T={h['T']:g} ans", f"{Q * 1000:.0f} L/s")
        fig = px.line(x=[0, tc, tc * 2.67], y=[0, Q * 1000, 0], title="Hydrogramme triangulaire simplifié",
                      labels={"x": "Temps (min)", "y": "Q (L/s)"}, color_discrete_sequence=[NOIR])
        pplot(fig, 300)
    with t3:
        c1, c2, c3 = st.columns(3)
        A = c1.number_input("Surface du bassin versant (ha)", 0.1, 500.0, 5.0, 0.5, key="v_A")
        Cb = c2.number_input("Coefficient de ruissellement", 0.1, 1.0, 0.7, 0.05, key="v_C")
        qs = c3.number_input("Débit de fuite admissible (L/s/ha)", 1.0, 50.0, 10.0, 1.0)
        ts = np.array([5, 10, 15, 30, 60, 120, 180, 360, 720], dtype=float)
        vin = 10 * Cb * A * h["a"] * ts ** (-h["b"]) * ts / 60
        vout = qs * A * ts * 60 / 1000
        vol = vin - vout
        i0 = int(np.argmax(vol))
        c1, c2 = st.columns(2)
        c1.metric("Volume utile du bassin", f"{max(vol[i0], 0):.0f} m³")
        c2.metric("Durée critique", f"{ts[i0]:.0f} min")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ts, y=vin, name="Volume entrant", line=dict(color=NOIR, width=3)))
        fig.add_trace(go.Scatter(x=ts, y=vout, name="Volume évacué", line=dict(color=JAUNE, width=3)))
        fig.update_layout(title="Méthode des pluies", xaxis_title="Durée (min)", yaxis_title="m³")
        pplot(fig, 330)


# ===================== PAGE : CANIVEAUX =====================
def page_caniveaux():
    S = st.session_state
    h = S.hydro
    hero("〰️ Caniveaux, fossés et ouvrages hydrauliques", "Manning • réseau de tronçons • caniveau de chaussée • buses et dalots")
    t1, t2, t3, t4 = st.tabs(["📐 Dimensionner une section", "🕸️ Réseau de tronçons", "🛣️ Caniveau de chaussée et avaloirs",
                              "🌉 Ouvrage de traversée"])
    with t1:
        c1, c2, c3 = st.columns(3)
        kind = c1.selectbox("Forme de la section", SECTIONS, index=1)
        mat = c1.selectbox("Matériau", list(MANNING), index=1)
        Ql = c2.number_input("Débit de projet (L/s)", 1.0, 50000.0, 150.0, 10.0)
        Sp = c2.number_input("Pente (%)", 0.05, 15.0, 1.0, 0.05) / 100
        b = c3.number_input("Largeur du fond b ou diamètre D (m)", 0.1, 5.0, 0.5, 0.05)
        H = c3.number_input("Hauteur utile H (m)", 0.1, 4.0, 0.6, 0.05)
        m = c3.number_input("Talus m (H/V)", 0.0, 4.0, 1.0, 0.25)
        n = MANNING[mat]
        Q = Ql / 1000
        Hh = hmax_of(kind, b, H)
        y, ok = y_normal(kind, Q, b, m, H, Sp, n)
        A, _, T = sec_props(kind, y, b, m, H)
        V = Q / A if A > 0 else 0.0
        Fr = V / math.sqrt(9.81 * A / T) if T > 0 and A > 0 else 0.0
        Qf = q_manning(kind, 0.938 * b if kind.startswith("Circ") else H, b, m, H, Sp, n)
        stt = hyd_status(ok, V, y, Hh, kind, h["vmin"], h["vmax"], h["rev"], h["remp"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hauteur normale y", f"{y:.3f} m")
        c2.metric("Vitesse", f"{V:.2f} m/s")
        c3.metric("Froude", f"{Fr:.2f}", "torrentiel" if Fr > 1 else "fluvial")
        c4.metric("Capacité à pleine section", f"{Qf * 1000:.0f} L/s")
        verdict(stt.startswith("✅"), "Section satisfaisante.", stt.replace("❌ ", "").replace("⚠️ ", ""))
        pplot(fig_section(kind, b, H, m, y), 340)
        if kind.startswith("Circ"):
            cands = [(d, d) for d in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5)]
        elif kind == "Triangulaire":
            cands = [(b, hh) for hh in (0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0)]
        else:
            cands = [(bb, H) for bb in (0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0)]
        rows = []
        for bb, hh in cands:
            yy, okk = y_normal(kind, Q, bb, m, hh, Sp, n)
            AA, _, _ = sec_props(kind, yy, bb, m, hh)
            VV = Q / AA if AA > 0 else 0.0
            rows.append({"Dimension (m)": f"D {bb}" if kind.startswith("Circ") else f"b {bb} × H {hh}",
                         "y normal (m)": round(yy, 3), "V (m/s)": round(VV, 2),
                         "Statut": hyd_status(okk, VV, yy, hmax_of(kind, bb, hh), kind, h["vmin"], h["vmax"], h["rev"],
                                              h["remp"])})
        st.markdown("**Dimensions courantes pour ce débit**")
        show_df(pd.DataFrame(rows))
    with t2:
        with st.expander("Paramètres hydrologiques et critères"):
            c1, c2, c3, c4 = st.columns(4)
            h["t_ent"] = float(c1.number_input("Temps d'entrée (min)", 3.0, 30.0, float(h["t_ent"]), 1.0))
            h["vmin"] = float(c2.number_input("V mini (m/s)", 0.2, 1.5, float(h["vmin"]), 0.1))
            h["vmax"] = float(c3.number_input("V maxi (m/s)", 1.0, 8.0, float(h["vmax"]), 0.5))
            h["rev"] = float(c4.number_input("Revanche mini (m)", 0.0, 0.5, float(h["rev"]), 0.05))
            h["remp"] = float(c1.slider("Remplissage max buses", 0.5, 1.0, float(h["remp"]), 0.05))
            h["marge"] = float(c2.slider("Marge de sécurité sur Q (%)", 0, 30, int(h["marge"] * 100)) / 100)
            st.caption(f"Pluie : a = {h['a']:g}, b = {h['b']:g} (T = {h['T']:g} ans) — modifiable dans « Hydrologie ».")
        note("Colonne « Amont » : noms des tronçons qui se déversent dans celui-ci, séparés par « ; ». "
             "Sections : Rectangulaire, Trapézoïdal, Triangulaire, Circulaire (buse).")
        editor("reseau", {"Section": st.column_config.SelectboxColumn("Section", options=SECTIONS)})
        rs, err = reseau_calc(S.reseau, h)
        if err:
            st.error(err)
        elif rs is not None and len(rs):
            n_ok = int(rs["Statut"].str.startswith("✅").sum())
            st.metric("Tronçons satisfaisants", f"{n_ok} / {len(rs)}")
            show_df(rs.round(2))
            fig = go.Figure()
            fig.add_trace(go.Bar(x=rs["Tronçon"], y=rs["Q (L/s)"], name="Débit de projet", marker_color=NOIR))
            fig.add_trace(go.Bar(x=rs["Tronçon"], y=rs["Capacité (L/s)"], name="Capacité", marker_color=JAUNE))
            fig.update_layout(barmode="group", title="Débit de projet et capacité par tronçon")
            pplot(fig, 340)
    with t3:
        c1, c2, c3 = st.columns(3)
        Sx = c1.number_input("Pente transversale Sx (%)", 1.0, 6.0, 2.5, 0.5) / 100
        Sl = c1.number_input("Pente longitudinale (%)", 0.2, 10.0, 1.0, 0.1, key="iz_S") / 100
        ng = c1.number_input("n de Manning", 0.010, 0.030, 0.016, 0.001, format="%.3f")
        W = c2.number_input("Largeur drainée (m)", 3.0, 30.0, 8.5, 0.5)
        Cg = c2.number_input("Coefficient de ruissellement", 0.5, 1.0, 0.9, 0.05, key="iz_C")
        ig = c2.number_input("Intensité (mm/h)", 20.0, 300.0, float(min(max(round(h["a"] * 10 ** (-h["b"]) + 40, 0), 20.0), 300.0)), 5.0)
        Tadm = c3.number_input("Largeur d'écoulement admissible (m)", 0.5, 5.0, 2.5, 0.25)
        Ls = c3.number_input("Longueur drainée avant avaloir (m)", 5.0, 300.0, 60.0, 5.0)
        q_lin = Cg * ig * W / 3.6e6
        Q = q_lin * Ls
        Tc = izzard_T(Q, ng, Sx, Sl)
        Qadm = izzard_Q(Tadm, ng, Sx, Sl)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Débit à l'avaloir", f"{Q * 1000:.1f} L/s")
        c2.metric("Largeur d'écoulement", f"{Tc:.2f} m")
        c3.metric("Capacité à T admissible", f"{Qadm * 1000:.1f} L/s")
        c4.metric("Espacement maxi des avaloirs", f"{Qadm / q_lin:.0f} m")
        verdict(Tc <= Tadm, "Largeur d'écoulement admissible respectée.", "Ecoulement trop large : rapprocher les avaloirs.")
        ss = np.linspace(0.3, 6, 25)
        pplot(px.line(x=ss, y=[izzard_Q(Tadm, ng, Sx, s / 100) / q_lin for s in ss],
                      labels={"x": "Pente longitudinale (%)", "y": "Espacement (m)"},
                      title="Espacement maximal des avaloirs", color_discrete_sequence=[NOIR]), 300)
    with t4:
        c1, c2, c3 = st.columns(3)
        Qo = c1.number_input("Débit de projet (L/s)", 10.0, 50000.0, 800.0, 50.0, key="ov_Q") / 1000
        So = c2.number_input("Pente de l'ouvrage (%)", 0.2, 10.0, 1.0, 0.1, key="ov_S") / 100
        no = c3.number_input("n de Manning de l'ouvrage", 0.010, 0.020, 0.013, 0.001, format="%.3f", key="ov_n")
        rows = []
        opts = [("Buse Ø600", "Circulaire (buse)", 0.6, 0.6), ("Buse Ø800", "Circulaire (buse)", 0.8, 0.8),
                ("Buse Ø1000", "Circulaire (buse)", 1.0, 1.0), ("Buse Ø1200", "Circulaire (buse)", 1.2, 1.2),
                ("Buse Ø1500", "Circulaire (buse)", 1.5, 1.5), ("Dalot 1,0×1,0", "Rectangulaire", 1.0, 1.0),
                ("Dalot 1,5×1,0", "Rectangulaire", 1.5, 1.0), ("Dalot 2,0×1,5", "Rectangulaire", 2.0, 1.5),
                ("Dalot 2,0×2,0", "Rectangulaire", 2.0, 2.0), ("Dalot 3,0×2,0", "Rectangulaire", 3.0, 2.0)]
        for nom, kd, bb, hh in opts:
            Af = math.pi * bb ** 2 / 4 if kd.startswith("Circ") else bb * hh
            Pf = math.pi * bb if kd.startswith("Circ") else 2 * (bb + hh)
            Qf = Af * (Af / Pf) ** (2 / 3) * math.sqrt(So) / no
            HW = (Qo / (0.6 * Af)) ** 2 / (2 * 9.81) + hh / 2
            rows.append({"Ouvrage": nom, "Q pleine section (L/s)": round(Qf * 1000), "V pleine (m/s)": round(Qf / Af, 2),
                         "Q/Qf": round(Qo / Qf, 2), "HW/D (orifice)": round(HW / hh, 2),
                         "Adapté": "✅" if Qo / Qf <= 0.8 and HW / hh <= 1.2 else "❌"})
        show_df(pd.DataFrame(rows))
        note("Contrôle simplifié (écoulement en pleine section et charge à l'entrée par la formule de l'orifice) : "
             "à compléter par la vérification en régime d'entrée et de sortie.")


# ===================== PAGE : CANIVEAU BÉTON ARMÉ =====================
def page_caniveau_ba():
    hero("🧱 Caniveau couvert en béton armé", "Dalle de couverture sous roue • piédroits sous poussée • radier • quantités par mètre linéaire")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Géométrie")
        B = c1.number_input("Largeur intérieure B (m)", 0.3, 3.0, 0.6, 0.05)
        H = c1.number_input("Hauteur intérieure H (m)", 0.3, 3.0, 0.8, 0.05)
        tp = c1.number_input("Épaisseur piédroits (cm)", 10.0, 50.0, 15.0, 1.0)
        tr = c1.number_input("Épaisseur radier (cm)", 10.0, 50.0, 15.0, 1.0)
        td = c1.number_input("Épaisseur dalle (cm)", 10.0, 50.0, 15.0, 1.0)
        hr = c1.number_input("Recouvrement (m)", 0.0, 2.0, 0.20, 0.05)
    with c2:
        st.markdown("#### Matériaux et sol")
        cl = c2.selectbox("Classe de béton", CLASSES_BETON, index=1)
        fyk = c2.selectbox("Acier fyk (MPa)", [400, 500], index=1)
        cc = c2.number_input("Enrobage (mm)", 20.0, 60.0, 30.0, 5.0)
        gam = c2.number_input("γ remblai (kN/m³)", 14.0, 22.0, 18.0, 0.5)
        phs = c2.number_input("φ remblai (°)", 20.0, 40.0, 30.0, 1.0)
        qadm = c2.number_input("Contrainte admissible du sol (kPa)", 50.0, 500.0, 150.0, 10.0)
    with c3:
        st.markdown("#### Charges")
        Pw = c3.number_input("Charge de roue (kN)", 20.0, 150.0, 65.0, 5.0)
        dy = c3.number_input("Coefficient dynamique", 1.0, 1.5, 1.2, 0.05)
        qs = c3.number_input("Surcharge latérale (kPa)", 0.0, 30.0, 10.0, 1.0)
    pr = beton_props(cl)
    fck = pr["fck"]
    Ka = math.tan(math.radians(45 - phs / 2)) ** 2
    Bext = B + 2 * tp / 100
    # Dalle
    L = B + tp / 100
    G = td / 100 * 25 + hr * gam
    surf = (0.25 + 2 * hr) * (0.60 + 2 * hr)
    qv = max(Pw * dy / surf, 5.0)
    w = 1.35 * G + 1.5 * qv
    Md, Vd = w * L ** 2 / 8, w * L / 2
    # Piédroits
    Hc = H + (td + tr) / 200
    pG, pQ, dG = Ka * gam * hr, Ka * qs, Ka * gam * Hc
    Mp = 1.35 * (pG * Hc ** 2 / 8 + dG * Hc ** 2 / 15) + 1.5 * pQ * Hc ** 2 / 8
    Vp = 1.35 * (5 / 8 * pG * Hc + 0.4 * dG * Hc) + 1.5 * 5 / 8 * pQ * Hc
    # Radier
    pnet = (1.35 * (G * Bext + 2 * tp / 100 * H * 25) + 1.5 * qv * Bext) / Bext
    Lr = B + tp / 100
    Mr, Vr = pnet * Lr ** 2 / 10, pnet * Lr / 2
    ser = ((G + qv) * Bext + 2 * tp / 100 * H * 25 + tr / 100 * Bext * 25) / Bext
    rows, as_list = [], {}
    for nom, M, V, h in [("Dalle de couverture", Md, Vd, td), ("Piédroits", Mp, Vp, tp), ("Radier", Mr, Vr, tr)]:
        d = h * 10 - cc - 5
        f = flexion_rect(M, 1000.0, d, fck, fyk)
        asr = max(f["As"], as_min_flex(1000.0, d, fck, fyk))
        vrd = vrd_c(1000.0, d, fck, max(asr, 100.0))
        as_list[nom] = asr
        rows.append({"Élément": nom, "M_Ed (kN·m/m)": round(M, 2), "V_Ed (kN/m)": round(V, 1), "d (mm)": round(d),
                     "As (cm²/m)": round(asr / 100, 2), "Armature principale": choisir_armature(asr, h * 10),
                     "Répartition": choisir_armature(0.2 * asr, h * 10),
                     "Tranchant": "✅" if V <= vrd else "❌ épaissir", "μ": round(f["mu"], 3)})
    show_df(pd.DataFrame(rows))
    c1, c2, c3 = st.columns(3)
    c1.metric("Charge de roue répartie", f"{qv:.0f} kPa")
    c2.metric("Contrainte sur le sol", f"{ser:.0f} kPa")
    c3.metric("Coefficient Ka", f"{Ka:.3f}")
    verdict(ser <= qadm, "Contrainte au sol admissible.", "Contrainte au sol excessive : élargir le radier.")
    bet = Bext * td / 100 + Bext * tr / 100 + 2 * tp / 100 * H
    acier = 0.00785 * 1.15 * 1.2 * (as_list["Dalle de couverture"] * Bext + as_list["Radier"] * Bext
                                     + 2 * as_list["Piédroits"] * Hc)
    c1, c2, c3 = st.columns(3)
    c1.metric("Béton par mètre linéaire", f"{bet:.3f} m³/ml")
    c2.metric("Acier par mètre linéaire", f"{acier:.1f} kg/ml")
    c3.metric("Ratio d'acier", f"{acier / bet:.0f} kg/m³")
    fig = go.Figure()
    Ht = H + (td + tr) / 100
    for x0, y0, x1, y1 in [(0, 0, Bext, tr / 100), (0, tr / 100, tp / 100, tr / 100 + H),
                           (Bext - tp / 100, tr / 100, Bext, tr / 100 + H), (0, tr / 100 + H, Bext, Ht)]:
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=JAUNE, line=dict(color=NOIR, width=2))
    fig.update_xaxes(visible=False, range=[-0.2, Bext + 0.2])
    fig.update_yaxes(visible=False, scaleanchor="x", range=[-0.1, Ht + hr + 0.1])
    fig.add_shape(type="line", x0=-0.1, x1=Bext + 0.1, y0=Ht + hr, y1=Ht + hr, line=dict(color=GRIS, dash="dot"))
    fig.update_layout(title="Coupe du caniveau couvert")
    pplot(fig, 340)
    note("Modèle simplifié : dalle sur appuis simples, piédroits articulés en tête / encastrés en pied, radier semi-continu. "
         "Vérifier le poinçonnement sous roue, l'ancrage des armatures et les effets de la nappe.")


# ===================== PAGE : QUALITÉ =====================
def page_qualite():
    S = st.session_state
    hero("🔬 Contrôle qualité des travaux", "Compactage • portance CBR • synthèse des relevés de contrôle")
    st.markdown("##### Seuils de réception (modifiables)")
    editor("seuils", dynamic=False)
    t1, t2, t3 = st.tabs(["🧱 Compactage", "📊 Portance CBR", "📋 Relevés de contrôle"])
    with t1:
        editor("compactage", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                              "Couche": st.column_config.SelectboxColumn("Couche", options=LAYERS)})
        d = compaction_df(S.compactage)
        sm = compaction_summary(S.compactage, S.seuils)
        st.subheader("Conformité par couche")
        show_df(sm)
        if len(d):
            fig = px.scatter(d, x="PK (m)", y="Compactage (% OPM)", color="Couche", color_discrete_sequence=PALETTE,
                             title="Compactage mesuré par PK")
            fig.update_traces(marker=dict(size=12, line=dict(width=2, color=NOIR)))
            for _, r in S.seuils.iterrows():
                fig.add_hline(y=fnum(r["Compactage min (% OPM)"], 95.0), line_dash="dot", line_color=GRIS,
                              annotation_text=str(r["Couche"]))
            pplot(fig, 380)
            show_df(d[["Date", "PK (m)", "Couche", "Compactage (% OPM)", "Écart w (pts)"]].round(2))
    with t2:
        editor("cbr", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                       "Couche": st.column_config.SelectboxColumn("Couche", options=LAYERS)})
        cs = cbr_summary(S.cbr, S.seuils)
        show_df(cs)
        c = S.cbr.copy()
        c["CBR (%)"] = pd.to_numeric(c["CBR (%)"], errors="coerce")
        c = c.dropna(subset=["CBR (%)", "Couche"])
        if len(c):
            pplot(px.box(c, x="Couche", y="CBR (%)", points="all", color="Couche", color_discrete_sequence=PALETTE,
                         title="Distribution du CBR par couche"), 360)
    with t3:
        r = S.releves.copy()
        r["Valeur"] = pd.to_numeric(r["Valeur"], errors="coerce")
        rows = []
        for p, g in r.dropna(subset=["Valeur", "Paramètre"]).groupby("Paramètre"):
            lo, hi = TOLERANCES.get(p, (None, None))
            v = g["Valeur"]
            mask = pd.Series(False, index=v.index)
            if lo is not None:
                mask |= v < lo
            if hi is not None:
                mask |= v > hi
            rows.append({"Paramètre": p, "n": len(v), "Moyenne": round(v.mean(), 2), "Min": round(v.min(), 2),
                         "Max": round(v.max(), 2), "Tolérance": f"{lo if lo is not None else '—'} / {hi if hi is not None else '—'}",
                         "Hors tolérance": int(mask.sum())})
        show_df(pd.DataFrame(rows))


# ===================== PAGE : ENTRETIEN =====================
def page_entretien():
    S = st.session_state
    dev = S.projet["devise"]
    hero("🩺 Auscultation et entretien", "Relevé de dégradations • indice d'état • stratégie d'entretien")
    note("Indice d'état simplifié = 100 − Σ (poids du défaut × gravité × % de surface dégradée).")
    editor("degr", {"Type": st.column_config.SelectboxColumn("Type", options=list(DEGR_W)),
                    "Sévérité": st.column_config.SelectboxColumn("Sévérité", options=list(SEV))})
    surf = st.number_input("Surface de chaque section auscultée (m²)", 100.0, 1e6, 1400.0, 100.0)
    d, g = degr_index(S.degr, surf)
    if g.empty:
        st.info("Aucune dégradation saisie.")
        return
    actions = {"Très bon": ("Aucune action", 0.0), "Bon": ("Entretien courant (colmatage, PATA)", 3.0),
               "Moyen": ("Enduit superficiel / couche mince", 8.0), "Médiocre": ("Purges + renforcement BB 5-6 cm", 22.0),
               "Mauvais": ("Reconstruction / renforcement lourd", 60.0)}
    g["Action recommandée"] = g["Classe"].map(lambda c: actions[c][0])
    g["Coût indicatif"] = g["Classe"].map(lambda c: actions[c][1]) * surf
    c1, c2, c3 = st.columns(3)
    idx_moy = g["Indice d'état"].mean()
    c1.metric("Indice moyen", f"{idx_moy:.0f} / 100")
    c2.metric("Sections à traiter", int((g["Classe"].isin(["Médiocre", "Mauvais"])).sum()))
    c3.metric("Coût indicatif total", f"{fmt(g['Coût indicatif'].sum(), 0)} {dev}")
    show_df(g.round(1))
    pplot(px.bar(g, x="Section", y="Indice d'état", color="Classe", range_y=[0, 100], title="Indice d'état par section",
                 color_discrete_map={"Très bon": VERT, "Bon": "#8BC34A", "Moyen": JAUNE, "Médiocre": ORANGE, "Mauvais": ROUGE}), 340)
    pplot(px.bar(d, x="Section", y="Surface (m²)", color="Type", title="Surfaces dégradées par type",
                 color_discrete_sequence=PALETTE), 320)
    iri = S.releves[S.releves["Paramètre"] == "IRI"]["Valeur"]
    if len(iri):
        st.info(f"IRI moyen relevé : {pd.to_numeric(iri, errors='coerce').mean():.2f} m/km.")


# ===================== PAGE : SIGNALISATION =====================
def page_signal():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("🚧 Signalisation et équipements", "Marquage • panneaux • glissières • bornes — quantités et coûts")
    c1, c2, c3 = st.columns(3)
    L = c1.number_input("Longueur équipée (m)", 100.0, 500000.0, float(P["longueur"]), 100.0)
    la = c1.number_input("Largeur ligne axiale (m)", 0.05, 0.3, 0.10, 0.01)
    lr = c1.number_input("Largeur ligne de rive (m)", 0.05, 0.3, 0.10, 0.01)
    gl = c2.slider("Part équipée de glissières (%, par côté)", 0.0, 50.0, 15.0, 1.0)
    pd_ = c2.number_input("Panneaux de danger par km", 0.0, 20.0, 4.0, 1.0)
    pp_ = c2.number_input("Panneaux de prescription par km", 0.0, 20.0, 3.0, 1.0)
    pi_ = c3.number_input("Panneaux d'indication par km", 0.0, 20.0, 2.0, 1.0)
    cons = c3.number_input("Consommation de peinture (kg/m²)", 0.3, 1.5, 0.7, 0.1)
    km = L / 1000
    s_axe = L * 3 / 13 * la
    s_rive = 2 * L * lr
    items = [("Marquage axial discontinu (T1)", "m²", s_axe, 9.0), ("Marquage de rive continu", "m²", s_rive, 9.0),
             ("Panneaux de signalisation", "u", math.ceil(km * (pd_ + pp_ + pi_)), 190.0),
             ("Glissières de sécurité", "ml", L * gl / 100 * 2, 55.0),
             ("Bornes kilométriques", "u", math.ceil(km) + 1, 60.0),
             ("Balises de virage", "u", math.ceil(L / 40 * 0.1), 25.0)]
    rows, cols = [], st.columns(3)
    for i, (nom, u, q, pu0) in enumerate(items):
        pu = cols[i % 3].number_input(f"PU {nom} ({dev}/{u})", 0.0, 1e5, pu0, 1.0, key=f"sg_pu{i}")
        rows.append({"Désignation": nom, "Unité": u, "Quantité": round(q, 1), "PU": pu, "Total": round(q * pu, 0)})
    df = pd.DataFrame(rows)
    show_df(df)
    c1, c2 = st.columns(2)
    c1.metric("Peinture nécessaire", f"{(s_axe + s_rive) * cons:.0f} kg")
    c2.metric("Total équipements", f"{fmt(df['Total'].sum(), 0)} {dev}")
    if st.button("➕ Envoyer au bordereau"):
        new = pd.DataFrame([("05 Signalisation", r["Désignation"], r["Unité"], r["Quantité"], r["PU"]) for _, r in df.iterrows()],
                           columns=COLS["metre"])
        add_rows("metre", new)
        st.rerun()


# ===================== PAGE : HSE =====================
def page_hse():
    S = st.session_state
    hero("🦺 Santé, sécurité et risques", "Matrice de criticité • plan de maîtrise • indicateurs d'accidentologie")
    t1, t2 = st.tabs(["⚠️ Matrice des risques", "📈 Indicateurs"])
    with t1:
        editor("risques")
        r = S.risques.dropna(subset=["Risque"]).copy()
        r["Probabilité"] = pd.to_numeric(r["Probabilité"], errors="coerce").fillna(1).clip(1, 5).astype(int)
        r["Gravité"] = pd.to_numeric(r["Gravité"], errors="coerce").fillna(1).clip(1, 5).astype(int)
        r["Score"] = r["Probabilité"] * r["Gravité"]
        r["Niveau"] = pd.cut(r["Score"], [0, 4, 9, 14, 25], labels=["🟢 Faible", "🟡 Modéré", "🟠 Élevé", "🔴 Critique"]).astype(str)
        counts = np.zeros((5, 5), dtype=int)
        for _, x in r.iterrows():
            counts[x["Probabilité"] - 1, x["Gravité"] - 1] += 1
        sc = np.array([[(p + 1) * (g + 1) for g in range(5)] for p in range(5)])
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Heatmap(z=sc, x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5], text=counts, texttemplate="%{text}",
                                       colorscale=[[0, VERT], [0.25, JAUNE], [0.55, ORANGE], [1, ROUGE]], showscale=False))
            fig.update_layout(title="Matrice de criticité", xaxis_title="Gravité", yaxis_title="Probabilité")
            pplot(fig, 400)
        with c2:
            show_df(r[["Risque", "Phase", "Score", "Niveau", "Mesure de maîtrise"]].sort_values("Score", ascending=False))
    with t2:
        c1, c2, c3 = st.columns(3)
        hrs = c1.number_input("Heures travaillées (cumul)", 1000.0, 1e8, 85000.0, 1000.0)
        acc = c2.number_input("Accidents avec arrêt", 0, 500, 1)
        jp = c3.number_input("Jours d'arrêt perdus", 0, 100000, 24)
        c1, c2 = st.columns(2)
        c1.metric("Taux de fréquence TF", f"{acc * 1e6 / hrs:.1f}")
        c2.metric("Taux de gravité TG", f"{jp * 1e3 / hrs:.2f}")
        note("TF = accidents avec arrêt × 10⁶ / heures travaillées — TG = jours perdus × 10³ / heures travaillées.")


# ===================== PAGE : MÉTRÉ =====================
def page_metre():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("🧮 Métré et estimation des coûts", "Bordereau • quantités de chaussée • caniveaux • synthèse")
    t1, t2, t3, t4 = st.tabs(["📋 Bordereau", "🛣️ Quantités de chaussée", "〰️ Quantités de caniveaux", "💶 Synthèse"])
    with t1:
        editor("metre", {"Unité": st.column_config.SelectboxColumn("Unité", options=["m³", "m²", "ml", "kg", "t", "u", "forfait", "j"])})
        st.metric("Total HT du bordereau", f"{fmt(metre_totals(S.metre)['Total'].sum(), 0)} {dev}")
    with t2:
        c1, c2 = st.columns(2)
        L = c1.number_input("Longueur de chaussée (m)", 50.0, 500000.0, float(P["longueur"]), 50.0, key="mc_L")
        kg = c2.number_input("Imprégnation / accrochage (kg/m²)", 0.2, 2.0, 0.6, 0.1)
        editor("couches", {"Unité": st.column_config.SelectboxColumn("Unité", options=["m³", "t"])})
        cq = S.couches.copy()
        for c in ["Épaisseur (cm)", "Largeur (m)", "Densité (t/m³)", "PU"]:
            cq[c] = pd.to_numeric(cq[c], errors="coerce").fillna(0)
        cq["Volume (m³)"] = L * cq["Largeur (m)"] * cq["Épaisseur (cm)"] / 100
        cq["Tonnage (t)"] = cq["Volume (m³)"] * cq["Densité (t/m³)"]
        cq["Quantité"] = np.where(cq["Unité"] == "t", cq["Tonnage (t)"], cq["Volume (m³)"])
        cq["Total"] = cq["Quantité"] * cq["PU"]
        show_df(cq.round(1))
        c1, c2, c3 = st.columns(3)
        c1.metric("Total chaussée", f"{fmt(cq['Total'].sum(), 0)} {dev}")
        c2.metric("Émulsion d'accrochage", f"{L * float(cq['Largeur (m)'].iloc[-1] if len(cq) else 0) * kg / 1000:.1f} t")
        d, v = calc_terrassement(S.profil, S.terr["td"], S.terr["tr"], S.terr["k"])
        c3.metric("Déblai / remblai du profil saisi", f"{fmt(v['Déblai (m³)'].sum(), 0)} / {fmt(v['Remblai (m³)'].sum(), 0)} m³")
        if st.button("➕ Envoyer les couches au bordereau"):
            new = pd.DataFrame([("03 Chaussée", r["Couche"], r["Unité"], round(r["Quantité"], 1), r["PU"])
                                for _, r in cq.iterrows()], columns=COLS["metre"])
            add_rows("metre", new)
            st.rerun()
    with t3:
        c1, c2, c3 = st.columns(3)
        Lc = c1.number_input("Longueur de caniveau (ml)", 10.0, 100000.0, 1000.0, 10.0)
        B = c1.number_input("Largeur intérieure (m)", 0.2, 3.0, 0.6, 0.05, key="mq_B")
        H = c1.number_input("Hauteur intérieure (m)", 0.2, 3.0, 0.8, 0.05, key="mq_H")
        e = c2.number_input("Épaisseur des parois (cm)", 8.0, 40.0, 15.0, 1.0)
        ra = c2.number_input("Ratio d'acier (kg/m³)", 40.0, 200.0, 100.0, 5.0)
        ov = c2.number_input("Largeur de fouille en plus (m)", 0.2, 2.0, 0.6, 0.1)
        pb = c3.number_input(f"Béton ({dev}/m³)", 0.0, 1e4, 280.0, 10.0)
        pa = c3.number_input(f"Acier ({dev}/kg)", 0.0, 100.0, 1.7, 0.1)
        pf = c3.number_input(f"Fouille ({dev}/m³)", 0.0, 500.0, 8.0, 1.0)
        Be, He = B + 2 * e / 100, H + 2 * e / 100
        vb = Be * He - B * H
        fouille = (Be + ov) * (He + 0.1)
        qty = pd.DataFrame([{"Poste": "Béton armé", "Unité": "m³", "Quantité": vb * Lc, "PU": pb},
                            {"Poste": "Acier HA", "Unité": "kg", "Quantité": vb * Lc * ra, "PU": pa},
                            {"Poste": "Fouille", "Unité": "m³", "Quantité": fouille * Lc, "PU": pf},
                            {"Poste": "Béton de propreté", "Unité": "m³", "Quantité": (Be + 0.2) * 0.05 * Lc, "PU": pb * 0.7}])
        qty["Total"] = qty["Quantité"] * qty["PU"]
        show_df(qty.round(1))
        c1, c2 = st.columns(2)
        c1.metric("Coût au mètre linéaire", f"{qty['Total'].sum() / Lc:.0f} {dev}/ml")
        c2.metric("Coût total caniveaux", f"{fmt(qty['Total'].sum(), 0)} {dev}")
        if st.button("➕ Envoyer les caniveaux au bordereau"):
            new = pd.DataFrame([("04 Assainissement", f"Caniveau BA — {r['Poste']}", r["Unité"], round(r["Quantité"], 1), r["PU"])
                                for _, r in qty.iterrows()], columns=COLS["metre"])
            add_rows("metre", new)
            st.rerun()
    with t4:
        mt = metre_totals(S.metre)
        c1, c2, c3 = st.columns(3)
        ale = c1.slider("Aléas (%)", 0, 20, 5)
        fg = c2.slider("Frais généraux et bénéfice (%)", 0, 30, 12)
        tva = c3.slider("TVA (%)", 0.0, 25.0, 20.0, 0.5)
        ht = float(mt["Total"].sum())
        ht2 = ht * (1 + ale / 100) * (1 + fg / 100)
        ttc = ht2 * (1 + tva / 100)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("HT brut", fmt(ht, 0))
        c2.metric("HT avec aléas et FG", fmt(ht2, 0))
        c3.metric("Total TTC", f"{fmt(ttc, 0)} {dev}")
        c4.metric("TTC au km", f"{fmt(ttc / (P['longueur'] / 1000), 0)}")
        lots = mt.groupby("Lot", as_index=False)["Total"].sum().sort_values("Total")
        fig = px.bar(lots, x="Total", y="Lot", orientation="h", title="Coût par lot", color_discrete_sequence=[JAUNE])
        fig.update_traces(marker_line_color=NOIR, marker_line_width=2)
        pplot(fig, 380)


# ===================== PAGE : PLANNING =====================
def page_planning():
    S = st.session_state
    P = S.projet
    hero("📅 Planning et chemin critique", "Gantt • calage automatique • marges • avancement réel")
    note("Prédécesseurs : noms de tâches séparés par « ; ».")
    editor("taches", {"Début": st.column_config.DateColumn("Début", format="DD/MM/YYYY")})
    mode = st.radio("Calendrier", ["Dates saisies", "Calage automatique selon prédécesseurs"], horizontal=True)
    try:
        d, T = cpm(S.taches)
    except ValueError as ex:
        st.error(str(ex))
        return
    d["Avancement (%)"] = pd.to_numeric(d["Avancement (%)"], errors="coerce").fillna(0).clip(0, 100)
    if mode.startswith("Calage"):
        d["Début_"] = [pd.Timestamp(P["debut"]) + pd.Timedelta(days=float(v)) for v in d["ES"]]
    else:
        d["Début_"] = pd.to_datetime(d["Début"], errors="coerce").fillna(pd.Timestamp(P["debut"]))
    d["Fin_"] = d["Début_"] + pd.to_timedelta(d["Durée (j)"], unit="D")
    today = pd.Timestamp(date.today())
    d["Statut"] = [("Terminé" if a >= 100 else "En retard" if f < today else "En cours" if s <= today else "À venir")
                   for a, f, s in zip(d["Avancement (%)"], d["Fin_"], d["Début_"])]
    if mode.startswith("Calage") and st.button("💾 Appliquer ces dates au tableau"):
        tt = S.taches.copy()
        mp = dict(zip(d["Tâche"], d["Début_"].dt.date))
        tt["Début"] = [mp.get(n, x) for n, x in zip(tt["Tâche"], tt["Début"])]
        set_df("taches", tt)
        st.rerun()
    fig = px.timeline(d, x_start="Début_", x_end="Fin_", y="Tâche", color="Statut",
                      color_discrete_map={"Terminé": VERT, "En cours": JAUNE, "En retard": ROUGE, "À venir": "#C9C5AA"},
                      title="Diagramme de Gantt")
    fig.update_yaxes(autorange="reversed")
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper", line=dict(color=ROUGE, width=2, dash="dash"))
    pplot(fig, 140 + 32 * len(d))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Durée (chemin critique)", f"{T:.0f} j")
    c2.metric("Fin prévue", (pd.Timestamp(P["debut"]) + pd.Timedelta(days=T)).strftime("%d/%m/%Y"))
    c3.metric("Tâches en retard", int((d["Statut"] == "En retard").sum()))
    c4.metric("Tâches critiques", int(d["Critique"].sum()))
    out = d[["Tâche", "Responsable", "Durée (j)", "Avancement (%)", "Marge (j)", "Critique", "Statut"]].copy()
    out["Critique"] = out["Critique"].map({True: "🔴 Oui", False: "—"})
    show_df(out)


# ===================== PAGE : COÛTS (EVM) =====================
def page_cout():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("💰 Suivi des coûts — valeur acquise", "PV, EV, AC • CPI, SPI • prévision à l'achèvement")
    bac = st.number_input(f"Budget à l'achèvement BAC ({dev})", 0.0, 1e10, float(P["budget"]), 10000.0)
    note("Saisir les valeurs cumulées par mois : valeur planifiée (PV), acquise (EV) et coût réel (AC).")
    editor("ev")
    ev = S.ev.copy()
    for c in COLS["ev"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.dropna(subset=["Mois"]).sort_values("Mois")
    last = ev.dropna(subset=["EV cumulée", "AC cumulé", "PV cumulé"])
    if last.empty:
        st.info("Renseigner au moins un mois complet.")
        return
    r = last.iloc[-1]
    PV, EV, AC = float(r["PV cumulé"]), float(r["EV cumulée"]), float(r["AC cumulé"])
    CPI = EV / AC if AC else float("nan")
    SPI = EV / PV if PV else float("nan")
    EAC = bac / CPI if CPI else float("nan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPI (coût)", f"{CPI:.2f}", "sous budget" if CPI >= 1 else "dépassement", delta_color="normal" if CPI >= 1 else "inverse")
    c2.metric("SPI (délai)", f"{SPI:.2f}", "en avance" if SPI >= 1 else "en retard", delta_color="normal" if SPI >= 1 else "inverse")
    c3.metric("CV = EV − AC", f"{fmt(EV - AC, 0)} {dev}")
    c4.metric("SV = EV − PV", f"{fmt(EV - PV, 0)} {dev}")
    c1, c2, c3 = st.columns(3)
    c1.metric("EAC (prévision finale)", f"{fmt(EAC, 0)} {dev}")
    c2.metric("ETC (reste à dépenser)", f"{fmt(EAC - AC, 0)} {dev}")
    c3.metric("VAC (écart final)", f"{fmt(bac - EAC, 0)} {dev}")
    fig = go.Figure()
    for col, color in [("PV cumulé", GRIS), ("EV cumulée", JAUNE), ("AC cumulé", ROUGE)]:
        fig.add_trace(go.Scatter(x=ev["Mois"], y=ev[col], name=col, mode="lines+markers", line=dict(color=color, width=4)))
    fig.add_hline(y=bac, line_dash="dot", line_color=NOIR, annotation_text="BAC")
    fig.update_layout(title="Courbes en S", xaxis_title="Mois", yaxis_title=dev)
    pplot(fig, 400)


# ===================== PAGE : EXPORT =====================
def build_excel():
    S = st.session_state
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({"Clé": list(S.projet), "Valeur": [str(v) for v in S.projet.values()]}).to_excel(xw, sheet_name="Projet", index=False)
        for k in COLS:
            S[k].to_excel(xw, sheet_name=LABELS[k][:31], index=False)
        metre_totals(S.metre).to_excel(xw, sheet_name="Metre avec totaux", index=False)
    return buf.getvalue()


def build_rapport():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() else 0.0
    mt = metre_totals(S.metre)
    L = [f"# Rapport de synthèse — {P['nom']}", f"*Édité le {date.today().strftime('%d/%m/%Y')}*", "",
         "## Projet", f"- Maître d'ouvrage : {P['moa']}", f"- Catégorie : {P['categorie']} — {P['longueur'] / 1000:.2f} km — V = {P['vitesse']} km/h",
         f"- Période : {P['debut']} → {P['fin']}", "", "## Avancement", f"- Avancement global pondéré : **{avanc:.1f} %**", "",
         "## Coûts", f"- Estimation du métré HT : **{mt['Total'].sum():,.0f} {dev}**".replace(",", " "),
         f"- Budget cible : {P['budget']:,.0f} {dev}".replace(",", " "), "", "## Compactage"]
    comp = compaction_summary(S.compactage, S.seuils)
    L += [f"- {x['Couche']} : moyenne {x['Moyenne (% OPM)']} % OPM, min {x['Min (% OPM)']} % → {x['Statut']}" for _, x in comp.iterrows()] or ["- Aucun essai."]
    rs, _ = reseau_calc(S.reseau, S.hydro)
    L += ["", "## Réseau de caniveaux"]
    if rs is not None:
        L += [f"- {x['Tronçon']} : Q = {x['Q (L/s)']:.0f} L/s, V = {x['V (m/s)']:.2f} m/s → {x['Statut']}" for _, x in rs.iterrows()]
    L += ["", "---", "*Généré par GC Route & Caniveaux Pro — résultats indicatifs à valider par un ingénieur.*"]
    return "\n".join(L)


def page_export():
    S = st.session_state
    hero("📤 Export, rapport et sauvegarde", "Classeur Excel • rapport de synthèse • restauration")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Classeur Excel complet", build_excel(), "projet_route.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rap = build_rapport()
    c2.download_button("⬇️ Rapport de synthèse (Markdown)", rap.encode("utf-8"), "rapport_route.md", "text/markdown")
    with st.expander("👁️ Aperçu du rapport", expanded=True):
        st.markdown(rap)
    cols = st.columns(4)
    for i, k in enumerate(COLS):
        cols[i % 4].download_button(f"⬇️ {LABELS[k]}", S[k].to_csv(index=False).encode("utf-8-sig"), f"{k}.csv", "text/csv", key=f"csv_{k}")
    up = st.file_uploader("Restaurer un classeur exporté", type=["xlsx"])
    if up is not None and st.button("♻️ Restaurer les données"):
        try:
            sheets = pd.read_excel(up, sheet_name=None)
            inv = {v[:31]: k for k, v in LABELS.items()}
            for nom, df in sheets.items():
                if nom in inv:
                    set_df(inv[nom], coerce(df, inv[nom]))
            st.success("Données restaurées.")
            st.rerun()
        except Exception as ex:
            st.error(f"Restauration impossible : {ex}")
    if st.button("🗑️ Recharger les données de démonstration"):
        for k in list(S.keys()):
            del S[k]
        st.rerun()


# ===================== NAVIGATION =====================
PAGES = {
    "🏠 Tableau de bord": page_dashboard,
    "📥 Collecte et journal": page_collecte,
    "🧭 Géométrie routière": page_geometrie,
    "⛰️ Profil en long et cubatures": page_profil,
    "🌍 Sols et terrassement": page_sols,
    "🚛 Trafic": page_trafic,
    "🛣️ Dimensionnement chaussée": page_chaussee,
    "🌧️ Hydrologie": page_hydro,
    "〰️ Caniveaux et ouvrages": page_caniveaux,
    "🧱 Caniveau béton armé": page_caniveau_ba,
    "🔬 Contrôle qualité": page_qualite,
    "🩺 Auscultation et entretien": page_entretien,
    "🚧 Signalisation": page_signal,
    "🦺 HSE et risques": page_hse,
    "🧮 Métré et coûts": page_metre,
    "📅 Planning": page_planning,
    "💰 Suivi des coûts (EVM)": page_cout,
    "📤 Export et rapport": page_export,
}


def main():
    init_state()
    with st.sidebar:
        st.markdown("<div class='brand'>🛣️ GC Route & Caniveaux</div>", unsafe_allow_html=True)
        choix = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
        st.markdown("---")
        st.caption(f"Projet : {st.session_state.projet['nom']}")
        st.caption("Résultats indicatifs — validation par un ingénieur / BET requise.")
    PAGES[choix]()


if __name__ == "__main__":
    main()
