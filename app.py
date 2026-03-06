import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Clientes x Frentes | Ciclo 25–26", layout="wide")

REQUIRED_COLS = [
    "Empresa relacionada - Nomes",
    "Frente de Negócio",
    "Produto Principal",
    "N_produtos_total",
    "G1 Responsável",
    "Pedra",
    "Farol",
]

DEFAULT_FILE = "Clientes_25-26_frentes_padronizado.xlsx"
DEFAULT_SHEET = "Brasil_Latam"

# -----------------------------
# Data helpers
# -----------------------------
def load_default_df() -> pd.DataFrame:
    return pd.read_excel(DEFAULT_FILE, sheet_name=DEFAULT_SHEET)

def load_uploaded_df(uploaded_file) -> pd.DataFrame:
    return pd.read_excel(uploaded_file, sheet_name=DEFAULT_SHEET)

def validate_df(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

def ensure_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    fr = (
        df.groupby("Empresa relacionada - Nomes")["Frente de Negócio"]
        .nunique()
        .rename("N_frentes_calc")
        .reset_index()
    )

    pr = (
        df.groupby("Empresa relacionada - Nomes")["N_produtos_total"]
        .max()
        .rename("N_produtos_total_calc")
        .reset_index()
    )

    out = df.merge(fr, on="Empresa relacionada - Nomes", how="left").merge(
        pr, on="Empresa relacionada - Nomes", how="left"
    )
    return out

def client_table(df: pd.DataFrame) -> pd.DataFrame:
    def first_non_null(s):
        s = s.dropna().astype(str)
        s = [x.strip() for x in s if x.strip() != ""]
        return s[0] if s else None

    out = (
        df.groupby("Empresa relacionada - Nomes")
        .agg(
            N_frentes=("N_frentes_calc", "max"),
            N_produtos=("N_produtos_total_calc", "max"),
            Pedra=("Pedra", first_non_null),
            Farol=("Farol", first_non_null),
            **{"G1 Responsável": ("G1 Responsável", first_non_null)},
        )
        .reset_index()
    )

    out["N_frentes"] = pd.to_numeric(out["N_frentes"], errors="coerce")
    out["N_produtos"] = pd.to_numeric(out["N_produtos"], errors="coerce")
    out = out.dropna(subset=["N_frentes", "N_produtos"])
    out["N_frentes"] = out["N_frentes"].astype(int)
    out["N_produtos"] = out["N_produtos"].astype(int)

    out["Pedra"] = out["Pedra"].fillna("Sem Pedra")
    out["G1 Responsável"] = out["G1 Responsável"].fillna("Sem Responsável")
    out["Farol"] = out["Farol"].fillna("Sem Farol")

    return out

def bar_with_labels(df_counts: pd.DataFrame, xcol: str, ycol: str, xlabel: str):
    fig = px.bar(df_counts, x=xcol, y=ycol, text=ycol)
    fig.update_traces(textposition="outside", cliponaxis=False)

    fig.update_xaxes(
        visible=True,
        title_text=xlabel,
        tickmode="linear",
        showgrid=False,
        zeroline=False,
    )
    fig.update_yaxes(visible=False, showgrid=False, zeroline=False)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    return fig

# -----------------------------
# Session state
# -----------------------------
if "df_cached" not in st.session_state:
    df0 = load_default_df()
    validate_df(df0)
    st.session_state.df_cached = ensure_metrics(df0)

if "client_list" not in st.session_state:
    st.session_state.client_list = []

# NOVO
if "client_exclude_list" not in st.session_state:
    st.session_state.client_exclude_list = []

if "resp_list" not in st.session_state:
    st.session_state.resp_list = []

if "pedra_list" not in st.session_state:
    st.session_state.pedra_list = []

if "farol_list" not in st.session_state:
    st.session_state.farol_list = []

# -----------------------------
# Header
# -----------------------------
st.title("CT - Entregas - Clientes por frentes / produtos — Ciclo 25–26")
st.caption("KPIs + indicadores + tabela. Use os filtros para recortes.")

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("Base de dados")
    uploaded = st.file_uploader("Substituir base (Excel .xlsx)", type=["xlsx"])
    colA, colB = st.columns(2)

    if colA.button("Usar base padrão"):
        df0 = load_default_df()
        validate_df(df0)
        st.session_state.df_cached = ensure_metrics(df0)
        st.session_state.client_list = []
        st.session_state.client_exclude_list = []
        st.session_state.resp_list = []
        st.session_state.pedra_list = []
        st.session_state.farol_list = []
        st.success("Base padrão carregada.")

    if uploaded is not None and colB.button("Usar base enviada"):
        dfu = load_uploaded_df(uploaded)
        validate_df(dfu)
        st.session_state.df_cached = ensure_metrics(dfu)
        st.session_state.client_list = []
        st.session_state.client_exclude_list = []
        st.session_state.resp_list = []
        st.session_state.pedra_list = []
        st.session_state.farol_list = []
        st.success("Base enviada carregada.")

    st.divider()
    mode = st.radio("Visão do visual:", ["Frentes", "Produtos", "Pedra"], horizontal=True)

# -----------------------------
# Data
# -----------------------------
df = st.session_state.df_cached
clients = client_table(df)

if clients.empty:
    st.error("Não há clientes válidos para analisar.")
    st.stop()

# ranking pedras
pedra_rank = {
    "Diamante": 5,
    "Ouro": 4,
    "Rubi": 4,
    "Prata": 3,
    "Bronze": 2,
    "Safira": 2,
    "Sem Pedra": 1
}
clients["Pedra_rank"] = clients["Pedra"].map(pedra_rank).fillna(1)

min_fr, max_fr = int(clients["N_frentes"].min()), int(clients["N_frentes"].max())
min_pr, max_pr = int(clients["N_produtos"].min()), int(clients["N_produtos"].max())
min_pe, max_pe = int(clients["Pedra_rank"].min()), int(clients["Pedra_rank"].max())

with st.sidebar:

    st.subheader("Filtros (faixa)")
    if mode == "Frentes":
        metric_range = st.slider("Frentes", min_fr, max_fr, (min_fr, max_fr))
    elif mode == "Produtos":
        metric_range = st.slider("Produtos", min_pr, max_pr, (min_pr, max_pr))
    else:
        metric_range = st.slider("Pedra", min_pe, max_pe, (min_pe, max_pe))

    top_n = st.slider("Top N clientes", 10, min(200, len(clients)), min(60, len(clients)))

    st.divider()
    st.subheader("Filtro por clientes")
    all_client_opts = sorted(clients["Empresa relacionada - Nomes"].astype(str).unique().tolist())
    st.multiselect("Selecionar clientes", options=all_client_opts, key="client_list")

    # NOVO
    st.subheader("Filtro inverso por clientes (remover da visão)")
    st.multiselect(
        "Clientes a remover",
        options=all_client_opts,
        key="client_exclude_list"
    )

    st.divider()
    st.subheader("Filtro por responsável")
    all_resp_opts = sorted(clients["G1 Responsável"].dropna().astype(str).unique().tolist())
    st.multiselect("Responsável", options=all_resp_opts, key="resp_list")

    st.divider()
    st.subheader("Filtro por Pedra")
    all_pedra_opts = sorted(clients["Pedra"].dropna().astype(str).unique().tolist())
    st.multiselect("Pedra", options=all_pedra_opts, key="pedra_list")

    st.divider()
    st.subheader("Filtro por Farol")
    all_farol_opts = sorted(clients["Farol"].dropna().astype(str).unique().tolist())
    st.multiselect("Farol", options=all_farol_opts, key="farol_list")

# -----------------------------
# Aplicar filtros
# -----------------------------
if mode == "Frentes":
    base_filtered = clients[clients["N_frentes"].between(metric_range[0], metric_range[1])].copy()
    value_col = "N_frentes"
elif mode == "Produtos":
    base_filtered = clients[clients["N_produtos"].between(metric_range[0], metric_range[1])].copy()
    value_col = "N_produtos"
else:
    base_filtered = clients[clients["Pedra_rank"].between(metric_range[0], metric_range[1])].copy()
    value_col = "Pedra_rank"

if st.session_state.client_list:
    base_filtered = base_filtered[
        base_filtered["Empresa relacionada - Nomes"].isin(st.session_state.client_list)
    ]

# NOVO filtro inverso
if st.session_state.client_exclude_list:
    base_filtered = base_filtered[
        ~base_filtered["Empresa relacionada - Nomes"].isin(st.session_state.client_exclude_list)
    ]

if st.session_state.resp_list:
    base_filtered = base_filtered[
        base_filtered["G1 Responsável"].isin(st.session_state.resp_list)
    ]

if st.session_state.pedra_list:
    base_filtered = base_filtered[
        base_filtered["Pedra"].isin(st.session_state.pedra_list)
    ]

if st.session_state.farol_list:
    base_filtered = base_filtered[
        base_filtered["Farol"].isin(st.session_state.farol_list)
    ]

if base_filtered.empty:
    st.warning("Nenhum cliente encontrado com esses filtros.")
    st.stop()

# -----------------------------
# Treemap
# -----------------------------
st.subheader("Visual principal")

clients_view = (
    base_filtered
    .sort_values(["Pedra", value_col], ascending=[True, False])
    .head(top_n)
)

blue_scale = [
    "#EAF3FF",
    "#B9D7FF",
    "#6FAEFF",
    "#2F7DE1",
    "#0B4F9C"
]

fig = px.treemap(
    clients_view,
    path=["Empresa relacionada - Nomes"],
    values=value_col,
    color=value_col,
    color_continuous_scale=blue_scale,
    custom_data=["Empresa relacionada - Nomes", "N_frentes", "N_produtos", "Pedra", "G1 Responsável"],
)

fig.update_traces(
    textinfo="label+value",
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Pedra: %{customdata[3]}<br>"
        "Responsável: %{customdata[4]}<br>"
        "Frentes: %{customdata[1]}<br>"
        "Produtos: %{customdata[2]}"
        "<extra></extra>"
    ),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()

# -----------------------------
# KPIs
# -----------------------------
st.subheader("KPIs")

total_clients = base_filtered.shape[0]
clients_2p_frentes = int((base_filtered["N_frentes"] >= 2).sum())
clients_2p_produtos = int((base_filtered["N_produtos"] >= 2).sum())
max_fr = int(base_filtered["N_frentes"].max())
max_pr = int(base_filtered["N_produtos"].max())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Clientes", total_clients)
k2.metric("Clientes ≥2 frentes", clients_2p_frentes)
k3.metric("Clientes ≥2 produtos", clients_2p_produtos)
k4.metric("Máximo", f"{max_fr} frentes | {max_pr} produtos")

st.divider()

# -----------------------------
# Tabela
# -----------------------------
st.subheader("Tabela")

df_filtered = df.merge(
    base_filtered[["Empresa relacionada - Nomes"]],
    on="Empresa relacionada - Nomes",
    how="inner"
)

st.dataframe(df_filtered, use_container_width=True)

