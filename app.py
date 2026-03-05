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
    """
    Mantém a lógica existente:
    - Recalcula N_frentes
    - Mantém N_produtos_total como está na base
    """
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
    """
    1 linha por cliente + (Pedra, Responsável) por cliente
    """
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

if "resp_list" not in st.session_state:
    st.session_state.resp_list = []

if "pedra_list" not in st.session_state:
    st.session_state.pedra_list = []

# -----------------------------
# Header
# -----------------------------
st.title("CT - Entregas - Clientes por frentes / produtos — Ciclo 25–26")
st.caption("KPIs + indicadores + tabela. Use os filtros para recortes por cliente/responsável/pedra.")

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
        st.session_state.resp_list = []
        st.session_state.pedra_list = []
        st.success("Base padrão carregada.")

    if uploaded is not None and colB.button("Usar base enviada"):
        dfu = load_uploaded_df(uploaded)
        validate_df(dfu)
        st.session_state.df_cached = ensure_metrics(dfu)
        st.session_state.client_list = []
        st.session_state.resp_list = []
        st.session_state.pedra_list = []
        st.success("Base enviada carregada.")

    st.divider()
    mode = st.radio("Visão do visual:", ["Frentes", "Produtos", "Pedra"], horizontal=True)

# -----------------------------
# Data
# -----------------------------
df = st.session_state.df_cached
clients = client_table(df)

if clients.empty:
    st.error("Não há clientes válidos para analisar (verifique a base).")
    st.stop()

# Ranking de pedras (ajuste se sua hierarquia for diferente)
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
        metric_range = st.slider(
            "Frentes (de… até…)",
            min_value=min_fr, max_value=max_fr,
            value=(min_fr, max_fr),
            key="range_frentes"
        )
    elif mode == "Produtos":
        metric_range = st.slider(
            "Produtos (de… até…)",
            min_value=min_pr, max_value=max_pr,
            value=(min_pr, max_pr),
            key="range_produtos"
        )
    else:
        metric_range = st.slider(
            "Pedra (precisão) (de… até…)",
            min_value=min_pe, max_value=max_pe,
            value=(min_pe, max_pe),
            key="range_pedra"
        )

    top_n = st.slider(
        "Top N clientes no visual",
        min_value=10,
        max_value=min(200, len(clients)),
        value=min(60, len(clients)),
        key="top_n"
    )

    st.divider()
    st.subheader("Filtro por lista de clientes (global)")
    all_client_opts = sorted(clients["Empresa relacionada - Nomes"].astype(str).unique().tolist())
    st.multiselect(
        "Selecione clientes (opcional)",
        options=all_client_opts,
        key="client_list"
    )

    st.divider()
    st.subheader("Filtro por responsável (global)")
    all_resp_opts = sorted(clients["G1 Responsável"].dropna().astype(str).unique().tolist())
    st.multiselect(
        "Selecione responsável (opcional)",
        options=all_resp_opts,
        key="resp_list"
    )

    st.divider()
    st.subheader("Filtro por Pedra (global)")
    all_pedra_opts = sorted(clients["Pedra"].dropna().astype(str).unique().tolist())
    st.multiselect(
        "Selecione Pedra (opcional)",
        options=all_pedra_opts,
        key="pedra_list"
    )

# -----------------------------
# Aplicar filtros (faixa + listas) + definir métrica/cor
# -----------------------------
if mode == "Frentes":
    base_filtered = clients[clients["N_frentes"].between(metric_range[0], metric_range[1])].copy()
    value_col = "N_frentes"
    color_col = "N_frentes"
    subtitle = "Tamanho do bloco = Nº de frentes"

elif mode == "Produtos":
    base_filtered = clients[clients["N_produtos"].between(metric_range[0], metric_range[1])].copy()
    value_col = "N_produtos"
    color_col = "N_produtos"
    subtitle = "Tamanho do bloco = Nº de produtos"

else:  # Pedra
    base_filtered = clients[clients["Pedra_rank"].between(metric_range[0], metric_range[1])].copy()
    value_col = "Pedra_rank"
    color_col = "Pedra_rank"
    subtitle = "Tamanho do bloco = Precisão da pedra"

if st.session_state.client_list:
    base_filtered = base_filtered[base_filtered["Empresa relacionada - Nomes"].isin(st.session_state.client_list)].copy()

if st.session_state.resp_list:
    base_filtered = base_filtered[base_filtered["G1 Responsável"].isin(st.session_state.resp_list)].copy()

if st.session_state.pedra_list:
    base_filtered = base_filtered[base_filtered["Pedra"].isin(st.session_state.pedra_list)].copy()

if base_filtered.empty:
    st.warning("Com esses filtros, não há clientes para exibir. Ajuste a faixa ou as listas.")
    st.stop()

# -----------------------------
# Visual principal (Treemap) — visão preservada (por cliente)
# cores douradas por intensidade da métrica
# -----------------------------
st.subheader("Visual principal")
st.caption(subtitle)

clients_view = (
    base_filtered
    .sort_values(["Pedra", value_col], ascending=[True, False])
    .head(top_n)
    .reset_index(drop=True)
)

gold_scale = [
    "#FFF7CC",  # dourado claro
    "#FFE08A",
    "#FFD24D",
    "#FFC000",
    "#D4A017"   # dourado intenso
]

fig = px.treemap(
    clients_view,
    path=["Empresa relacionada - Nomes"],
    values=value_col,
    color=color_col,
    color_continuous_scale=gold_scale,
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

fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=520)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# -----------------------------
# KPIs
# -----------------------------
st.subheader("KPIs")

total_clients = base_filtered.shape[0]
clients_2p_frentes = int((base_filtered["N_frentes"] >= 2).sum())
clients_2p_produtos = int((base_filtered["N_produtos"] >= 2).sum())
max_fr = int(base_filtered["N_frentes"].max()) if total_clients else 0
max_pr = int(base_filtered["N_produtos"].max()) if total_clients else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Clientes (no recorte)", f"{total_clients}")
k2.metric("Clientes com ≥2 frentes", f"{clients_2p_frentes}", f"{clients_2p_frentes/total_clients:.0%}" if total_clients else None)
k3.metric("Clientes com ≥2 produtos", f"{clients_2p_produtos}", f"{clients_2p_produtos/total_clients:.0%}" if total_clients else None)
k4.metric("Máximos no recorte", f"{max_fr} frentes | {max_pr} produtos")

st.divider()

# -----------------------------
# Indicadores
# -----------------------------
st.subheader("Indicadores")

cA, cB = st.columns(2)
with cA:
    st.markdown("**Distribuição: nº de frentes por cliente**")
    fr_dist = base_filtered["N_frentes"].value_counts().sort_index().reset_index()
    fr_dist.columns = ["N_frentes", "Clientes"]
    st.plotly_chart(bar_with_labels(fr_dist, "N_frentes", "Clientes", "Nº de frentes"), use_container_width=True)

with cB:
    st.markdown("**Distribuição: nº de produtos por cliente**")
    pr_dist = base_filtered["N_produtos"].value_counts().sort_index().reset_index()
    pr_dist.columns = ["N_produtos", "Clientes"]
    st.plotly_chart(bar_with_labels(pr_dist, "N_produtos", "Clientes", "Nº de produtos"), use_container_width=True)

st.divider()

# -----------------------------
# Tabela
# -----------------------------
st.subheader("Tabela (réplica da base)")

# filtra linhas da base original pelos clientes filtrados
df_filtered = df.merge(
    base_filtered[["Empresa relacionada - Nomes"]],
    on="Empresa relacionada - Nomes",
    how="inner"
)

# aplica filtros de responsável/pedra diretamente nas linhas (consistência total)
if st.session_state.resp_list:
    df_filtered = df_filtered[df_filtered["G1 Responsável"].isin(st.session_state.resp_list)].copy()

if st.session_state.pedra_list:
    df_filtered = df_filtered[df_filtered["Pedra"].isin(st.session_state.pedra_list)].copy()

st.dataframe(df_filtered, use_container_width=True)


