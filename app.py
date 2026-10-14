import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Interativo Completo", layout="wide")

st.title("📊 Dashboard de Atendimentos - Versão 4.1 (Tags Unificadas)")

def calcular_tempo_medio(serie_tempo):
    try:
        td = pd.to_timedelta(serie_tempo)
        media = td.mean()
        total_segundos = int(media.total_seconds())
        horas, resto = divmod(total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02d}h {minutos:02d}m {segundos:02d}s"
    except:
        return "N/A"

st.sidebar.title("Configurações")
st.sidebar.markdown("Faça o upload do seu ficheiro aqui:")

ficheiro_carregado = st.sidebar.file_uploader("", type=['csv'])

if ficheiro_carregado is not None:
    try:
        # Lendo os dados
        df = pd.read_csv(ficheiro_carregado, sep=';', encoding='utf-8-sig', on_bad_lines='skip')
        
        # --- LIMPEZA E UNIFICAÇÃO DE TAGS ---
        # 1. Transforma em texto
        # 2. Converte tudo para maiúsculas (upper)
        # 3. Remove espaços no início e no fim (strip)
        # 4. Remove aspas duplas que vieram do sistema (replace)
        if 'Tag' in df.columns:
            df['Tag'] = df['Tag'].astype(str).str.upper().str.strip().str.replace('"', '')
            # O Python transforma células vazias na palavra "NAN", vamos removê-la para não sujar o gráfico
            df['Tag'] = df['Tag'].replace('NAN', pd.NA)
        
        # Filtro de Status
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filtro Geral")
        lista_status = df['Status'].dropna().unique().tolist()
        status_selecionado = st.sidebar.multiselect("Selecione o Status:", options=lista_status, default=lista_status)
        
        df_base = df[df['Status'].isin(status_selecionado)]
        
        st.markdown("### 1. Desempenho por Agente")
        st.info("💡 **Dica:** Clique na barra de um Agente para ver as suas Tags, Classificações e Tempos Médios logo abaixo!")
        
        agentes = df_base['Agente'].value_counts().head(10).reset_index()
        agentes.columns = ['Agente', 'Quantidade']
        
        fig_agentes = px.bar(agentes, x='Quantidade', y='Agente', orientation='h', color='Quantidade')
        
        eventos = st.plotly_chart(fig_agentes, use_container_width=True, on_select="rerun")
        
        agentes_clicados = []
        if "selection" in eventos and "points" in eventos["selection"]:
            for ponto in eventos["selection"]["points"]:
                agentes_clicados.append(ponto["y"])
                
        if len(agentes_clicados) > 0:
            df_final = df_base[df_base['Agente'].isin(agentes_clicados)]
            st.success(f"A mostrar resultados detalhados para: {', '.join(agentes_clicados)}")
        else:
            df_final = df_base
        
        st.divider()
        
        st.markdown("### 2. Indicadores Chave")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total de Atendimentos", df_final.shape[0])
        col2.metric("Quantidade de Agentes", df_final['Agente'].nunique())
        col3.metric("Quantidade de Serviços", df_final['Serviço'].nunique())
        
        tempo_medio = calcular_tempo_medio(df_final['Tempo de Atendimento'])
        col4.metric("⏱️ Tempo Médio de Atend.", tempo_medio)
        
        st.divider()
        
        st.markdown("### 3. Análise Detalhada de Atendimentos")
        
        colA, colB = st.columns(2)
        
        with colA:
            classificacoes = df_final['Classificação'].value_counts().head(10).reset_index()
            classificacoes.columns = ['Classificação', 'Quantidade']
            fig_class = px.bar(classificacoes, x='Quantidade', y='Classificação', orientation='h', 
                               title="Top 10 Classificações", color='Quantidade', color_continuous_scale='teal')
            st.plotly_chart(fig_class, use_container_width=True)
            
        with colB:
            servicos = df_final['Serviço'].value_counts().head(10).reset_index()
            servicos.columns = ['Serviço', 'Quantidade']
            fig_servicos = px.bar(servicos, x='Quantidade', y='Serviço', orientation='h', 
                                  title="Top 10 Serviços", color='Quantidade', color_continuous_scale='blues')
            st.plotly_chart(fig_servicos, use_container_width=True)
            
        colC, colD = st.columns(2)
        
        with colC:
            tags = df_final['Tag'].dropna().value_counts().head(10).reset_index()
            tags.columns = ['Tag', 'Quantidade']
            fig_tags = px.pie(tags, values='Quantidade', names='Tag', title="Distribuição das Top 10 Tags (Unificadas)")
            st.plotly_chart(fig_tags, use_container_width=True)
            
        with colD:
            status_grafico = df_final['Status'].value_counts().reset_index()
            status_grafico.columns = ['Status', 'Quantidade']
            fig_status = px.pie(status_grafico, values='Quantidade', names='Status', title="Proporção de Status")
            st.plotly_chart(fig_status, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao ler o ficheiro. Detalhe: {e}")
else:
    st.info("👈 Por favor, carregue o ficheiro CSV no menu ao lado para iniciar.")
    df['Tag'] = df['Tag'].astype(str).str.upper().str.strip().str.replace('"', '')
df['Tag'] = df['Tag'].replace('NAN', pd.NA)