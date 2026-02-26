import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Clientes x Frentes | Ciclo 25–26", layout="wide")

REQUIRED_COLS = [
    "Empresa relacionada - Nomes",
    "Frente de Negócio",
    "Produto Principal",
    "N_produtos_total",
]

# -----------------------------
# Data helpers
# -----------------------------
def load_default_df() -> pd.DataFrame:
    DEFAULT_FILE = "Clientes_25-26_frentes_padronizado.xlsx"
    DEFAULT_SHEET = "Brasil_Latam"

def load_default_df() -> pd.DataFrame:
    return pd.read_excel(DEFAULT_FILE, sheet_name=DEFAULT_SHEET)

def load_uploaded_df(uploaded_file) -> pd.DataFrame:
    return pd.read_excel(uploaded_file, sheet_name="Brasil_Latam")

def validate_df(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")

def ensure_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Recalcula frentes por cliente (distinct)
    - Usa N_produtos_total como fonte (max por cliente)
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

    out = df.merge(fr, on="Empresa relacionada - Nomes", how="left").merge(pr, on="Empresa relacionada - Nomes", how="left")
    return out

def client_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    1 linha por cliente
    """
    out = (
        df.groupby("Empresa relacionada - Nomes")
        .agg(
            N_frentes=("N_frentes_calc", "max"),
            N_produtos=("N_produtos_total_calc", "max"),
        )
        .reset_index()
    )

    out["N_frentes"] = pd.to_numeric(out["N_frentes"], errors="coerce")
    out["N_produtos"] = pd.to_numeric(out["N_produtos"], errors="coerce")
    out = out.dropna(subset=["N_frentes", "N_produtos"])
    out["N_frentes"] = out["N_frentes"].astype(int)
    out["N_produtos"] = out["N_produtos"].astype(int)
    return out

def bar_with_labels(df_counts: pd.DataFrame, xcol: str, ycol: str, xlabel: str):
    fig = px.bar(df_counts, x=xcol, y=ycol, text=ycol)
    fig.update_traces(textposition="outside", cliponaxis=False)

    # Eixo X visível (mais claro)
    fig.update_xaxes(
        visible=True,
        title_text=xlabel,
        tickmode="linear",
        showgrid=False,
        zeroline=False,
    )

    # Eixo Y escondido (mantém limpo; números já estão nos rótulos)
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

# -----------------------------
# Header
# -----------------------------
st.title("CT - Entregas - Clientes por frentes / produtos — Ciclo 25–26")
st.caption("KPIs + indicadores + tabela. Use o filtro de lista para recortes por cliente.")

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
        st.success("Base padrão carregada.")

    if uploaded is not None and colB.button("Usar base enviada"):
        dfu = load_uploaded_df(uploaded)
        validate_df(dfu)
        st.session_state.df_cached = ensure_metrics(dfu)
        st.session_state.client_list = []
        st.success("Base enviada carregada.")

    st.divider()
    mode = st.radio("Visão do visual:", ["Frentes", "Produtos"], horizontal=True)

# -----------------------------
# Data
# -----------------------------
df = st.session_state.df_cached
clients = client_table(df)

if clients.empty:
    st.error("Não há clientes válidos para analisar (verifique a base).")
    st.stop()

min_fr, max_fr = int(clients["N_frentes"].min()), int(clients["N_frentes"].max())
min_pr, max_pr = int(clients["N_produtos"].min()), int(clients["N_produtos"].max())

with st.sidebar:
    st.subheader("Filtros (faixa)")
    if mode == "Frentes":
        metric_range = st.slider(
            "Frentes (de… até…)",
            min_value=min_fr, max_value=max_fr,
            value=(min_fr, max_fr),
            key="range_frentes"
        )
    else:
        metric_range = st.slider(
            "Produtos (de… até…)",
            min_value=min_pr, max_value=max_pr,
            value=(min_pr, max_pr),
            key="range_produtos"
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
    all_client_opts = sorted(clients["Empresa relacionada - Nomes"].tolist())
    st.multiselect(
        "Selecione clientes (opcional)",
        options=all_client_opts,
        key="client_list"
    )

# -----------------------------
# Aplicar filtros (faixa + lista)
# -----------------------------
if mode == "Frentes":
    base_filtered = clients[clients["N_frentes"].between(metric_range[0], metric_range[1])].copy()
    value_col = "N_frentes"
    subtitle = "Tamanho do bloco = Nº de frentes"
else:
    base_filtered = clients[clients["N_produtos"].between(metric_range[0], metric_range[1])].copy()
    value_col = "N_produtos"
    subtitle = "Tamanho do bloco = Nº de produtos"

if st.session_state.client_list:
    base_filtered = base_filtered[base_filtered["Empresa relacionada - Nomes"].isin(st.session_state.client_list)].copy()

if base_filtered.empty:
    st.warning("Com esses filtros, não há clientes para exibir. Ajuste a faixa ou a lista.")
    st.stop()

# -----------------------------
# Visual principal (Treemap)
# -----------------------------
st.subheader("Visual principal")
st.caption(subtitle)

clients_view = base_filtered.sort_values(value_col, ascending=False).head(top_n).reset_index(drop=True)

fig = px.treemap(
    clients_view,
    path=["Empresa relacionada - Nomes"],
    values=value_col,
    color=value_col,
    color_continuous_scale="Reds",
    custom_data=["Empresa relacionada - Nomes", "N_frentes", "N_produtos"],
)

fig.update_traces(
    textinfo="label+value",
    hovertemplate="<b>%{customdata[0]}</b><br>Frentes: %{customdata[1]}<br>Produtos: %{customdata[2]}<extra></extra>",
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

df_filtered = df.merge(
    base_filtered[["Empresa relacionada - Nomes"]],
    on="Empresa relacionada - Nomes",
    how="inner"
)


st.dataframe(df_filtered, use_container_width=True)
