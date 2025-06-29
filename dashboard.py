import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
import unicodedata

# --- Configuração da Página ---
st.set_page_config(
    page_title="Painel Estratégico | Gabinete Índia Armelau",
    page_icon="📈",
    layout="wide",
)

# --- Ocultar Elementos da Interface ---
st.markdown("""
    <style>
        header, footer {visibility: hidden !important;}
        #MainMenu {visibility: hidden !important;}
        div[data-testid="stDecoration"] {visibility: hidden !important;}
    </style>
""", unsafe_allow_html=True)

# --- Funções de Apoio ---
def normalize_text(text):
    if not isinstance(text, str): return ''
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').upper()

@st.cache_data
def carregar_dados_projecao():
    arquivo_base = 'base_de_dados_eleitoral.xlsx'
    if not os.path.exists(arquivo_base):
        st.error(f"Arquivo '{arquivo_base}' não encontrado! Execute 'gerar_simulacao.py' primeiro.")
        st.stop()
    df = pd.read_excel(arquivo_base)
    for col in ['Votos_2022', 'Votos_2026']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['Cabo_Eleitoral'] = df['Cabo_Eleitoral'].fillna('').astype(str)
    df['Municipio_ID'] = df['Municipio'].apply(normalize_text)
    return df

@st.cache_data
def carregar_geojson():
    url = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-33-mun.json"
    try:
        geojson_data = requests.get(url).json()
        for feature in geojson_data['features']:
            feature['properties']['id'] = normalize_text(feature['properties']['name'])
        return geojson_data
    except Exception as e:
        st.error(f"Não foi possível carregar o mapa. Verifique sua conexão. Erro: {e}")
        return None

# --- Carregamento Inicial e Cálculos ---
df = carregar_dados_projecao()
geojson = carregar_geojson()
df['Crescimento_Votos'] = (df['Votos_2026'] - df['Votos_2022']).astype(int)
df['Crescimento_Percentual'] = (df['Crescimento_Votos'] / df['Votos_2022'].replace(0, 1)) * 100

# --- PAINEL PRINCIPAL ---
st.title("Painel de Análise Eleitoral Estratégica")
st.markdown("Comparativo de Votação: **2022 vs. Projeção 2026**")
st.divider()

# Métricas Globais
st.subheader("Resumo Geral da Projeção")
total_votos_2022, total_votos_2026 = df['Votos_2022'].sum(), df['Votos_2026'].sum()
crescimento_consolidado, crescimento_percentual_consolidado = total_votos_2026 - total_votos_2022, (total_votos_2026 - total_votos_2022) / total_votos_2022 * 100
col1, col2, col3 = st.columns(3)
col1.metric("Total Votos 2022", f"{total_votos_2022:,.0f}".replace(",", "."))
col2.metric("Projeção Total 2026", f"{total_votos_2026:,.0f}".replace(",", "."), f"{crescimento_percentual_consolidado:.2f}%")
col3.metric("Crescimento Consolidado", f"{crescimento_consolidado:,.0f}".replace(",", "."))
st.divider()

# --- MAPA INTERATIVO E DINÂMICO ---
st.subheader("Análise Geográfica da Projeção")

# <<< MELHORIA: Menu de seleção para a métrica do mapa >>>
map_metric_options = {
    'Crescimento (%)': 'Crescimento_Percentual',
    'Votos (Projeção 2026)': 'Votos_2026',
    'Votos (2022)': 'Votos_2022',
    'Crescimento (Absoluto)': 'Crescimento_Votos'
}
selected_metric_label = st.selectbox("Visualizar mapa por:", list(map_metric_options.keys()))
selected_metric_col = map_metric_options[selected_metric_label]

filtro_mapa_cabos = st.checkbox("Destacar no mapa apenas municípios com Cabo Eleitoral")
df_mapa = df[df['Cabo_Eleitoral'].notna() & (df['Cabo_Eleitoral'] != '')] if filtro_mapa_cabos else df

if geojson:
    fig_map = px.choropleth_mapbox(
        df_mapa,
        geojson=geojson,
        locations='Municipio_ID',
        featureidkey="properties.id",
        color=selected_metric_col, # Cor dinâmica baseada na seleção
        color_continuous_scale="Viridis", # Uma escala de cores neutra
        mapbox_style="carto-positron",
        zoom=7.5, center={"lat": -22.25, "lon": -42.70}, opacity=0.6,
        hover_name='Municipio',
        custom_data=['Votos_2022', 'Votos_2026', 'Crescimento_Votos', 'Crescimento_Percentual', 'Cabo_Eleitoral']
    )
    fig_map.update_traces(hovertemplate="<br>".join([
        "<b>%{hovertext}</b>", "Cabo Eleitoral: %{customdata[4]}", "Votos 2022: %{customdata[0]:,}", "Projeção 2026: %{customdata[1]:,}", "Crescimento (Absoluto): %{customdata[2]:,}", "Crescimento (%): %{customdata[3]:.2f}%"
    ]))
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar=dict(title=selected_metric_label))
    st.plotly_chart(fig_map, use_container_width=True)
st.divider()

# --- Destaques, Gráficos e Tabela (sem alterações) ---
st.subheader("Destaques da Projeção")
col1, col2 = st.columns(2)
with col1:
    st.markdown("📈 **Top 5 Maiores Crescimentos (Absoluto)**")
    st.dataframe(df.nlargest(5, 'Crescimento_Votos')[['Municipio', 'Crescimento_Votos']], use_container_width=True, hide_index=True, column_config={"Municipio": "Município", "Crescimento_Votos": "Crescimento"})
with col2:
    st.markdown("📉 **Top 5 Maiores Quedas (Absoluto)**")
    st.dataframe(df.nsmallest(5, 'Crescimento_Votos')[['Municipio', 'Crescimento_Votos']], use_container_width=True, hide_index=True, column_config={"Municipio": "Município", "Crescimento_Votos": "Queda"})
st.divider()

st.subheader("Análise Gráfica Comparativa")
tipo_grafico = st.radio("Selecione o tipo de visualização:", ('Barras', 'Linhas'), horizontal=True)
df_melted = df.melt(id_vars=['Municipio'], value_vars=['Votos_2022', 'Votos_2026'], var_name='Ano', value_name='Total de Votos')
if tipo_grafico == 'Barras':
    fig = px.bar(df_melted[df_melted['Municipio'].isin(df.nlargest(20, 'Votos_2022')['Municipio'])], x='Municipio', y='Total de Votos', color='Ano', barmode='group', title='Comparativo de Votos nos 20 Principais Municípios')
else:
    fig = px.line(df_melted, x='Municipio', y='Total de Votos', color='Ano', title='Distribuição de Votos por Todos os Municípios')
fig.update_layout(legend_title_text='Eleição', xaxis_title="Município", yaxis_title="Quantidade de Votos")
st.plotly_chart(fig, use_container_width=True)
st.divider()

st.subheader("Análise Detalhada por Município")
filtro_tabela_cabos = st.checkbox("Mostrar na tabela apenas municípios com Cabo Eleitoral")
df_tabela = df[df['Cabo_Eleitoral'].notna() & (df['Cabo_Eleitoral'] != '')] if filtro_tabela_cabos else df
df_tabela_display = df_tabela.drop(columns=['Municipio_ID'], errors='ignore')
def estilo_crescimento(s):
    return ['color: green; font-weight: bold;' if v > 0.01 else 'color: red;' if v < -0.01 else '' for v in s]
st.dataframe(
    df_tabela_display.style.apply(estilo_crescimento, subset=['Crescimento_Percentual']).format(formatter="{:,.0f}", na_rep='-').format({'Crescimento_Percentual': '{:.2f}%'}),
    use_container_width=True,
    column_config={"Municipio": "Município", "Votos_2022": "Votos 2022", "Votos_2026": "Projeção 2026", "Cabo_Eleitoral": "Cabo Eleitoral", "Crescimento_Votos": "Crescimento (Absoluto)", "Crescimento_Percentual": "Crescimento (%)"},
    hide_index=True
)
