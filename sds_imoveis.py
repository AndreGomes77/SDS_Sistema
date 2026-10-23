import datetime
from io import BytesIO
import os
import sqlite3
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# CONFIGURAÇÃO DE SEGURANÇA (CHAVE DEFINIDA)
# ---------------------------------------------------------
CHAVE_MESTRA_CEO = "SDS2026#ADM"

# Configuração da Página
st.set_page_config(
    page_title="SDS Imóveis - Gestão e Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------
# APLICANDO A IDENTIDADE VISUAL E RESPONSIVIDADE (CSS)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --azul-marinho: #1B263B;
        --dourado: #C5A059;
        --cinza-claro: #F8FAFC;
        --branco: #FFFFFF;
        --texto-escuro: #333333;
    }

    .stApp {
        background-color: var(--cinza-claro);
        color: var(--texto-escuro);
    }

    [data-testid="stSidebar"] {
        background-color: var(--azul-marinho);
        color: var(--branco);
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label {
        color: var(--branco) !important;
    }

    h1, h2, h3 {
        color: var(--azul-marinho);
        font-family: 'Helvetica Neue', sans-serif;
    }

    div[data-testid="stMetric"] {
        background-color: var(--branco);
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid var(--dourado);
        margin-bottom: 10px;
    }
    div[data-testid="stMetric"] label {
        color: #666666 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: var(--azul-marinho) !important;
    }

    .stButton>button {
        background-color: var(--dourado);
        color: white;
        border-radius: 5px;
        border: none;
        font-weight: bold;
        width: 100%;
        padding: 10px;
    }
    .stButton>button:hover {
        background-color: #b08d4c;
        color: white;
    }

    /* Ajustes Responsivos para Celular */
    @media (max-width: 768px) {
        .stApp {
            padding: 5px;
        }
        h1 {
            font-size: 22px !important;
        }
        h2 {
            font-size: 18px !important;
        }
        div[data-testid="stMetric"] {
            padding: 10px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# ---------------------------------------------------------
def init_db():
  conn = sqlite3.connect("sds_imoveis.db")
  cursor = conn.cursor()

  # Tabela de Demandas
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS demandas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            adquirente TEXT NOT NULL,
            numero_imovel TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            status TEXT NOT NULL,
            prazo DATE NOT NULL,
            valor REAL DEFAULT 0.0,
            taxa_desc REAL DEFAULT 0.0,
            pagamento TEXT DEFAULT 'Pendente',
            tipo_imovel TEXT DEFAULT 'Caixa',
            parceria TEXT DEFAULT 'Não',
            parceiro_nome TEXT DEFAULT '',
            pct_sds REAL DEFAULT 100.0,
            status_parceiro TEXT DEFAULT 'Pendente'
        )
    """)

  # Garantir atualizações de colunas na tabela demandas de forma segura
  cursor.execute("PRAGMA table_info(demandas)")
  colunas = [coluna[1] for coluna in cursor.fetchall()]

  colunas_para_adicionar = {
      "adquirente": "TEXT DEFAULT ''",
      "numero_imovel": "TEXT DEFAULT ''",
      "taxa_desc": "REAL DEFAULT 0.0",
      "tipo_imovel": "TEXT DEFAULT 'Caixa'",
      "parceria": "TEXT DEFAULT 'Não'",
      "parceiro_nome": "TEXT DEFAULT ''",
      "pct_sds": "REAL DEFAULT 100.0",
      "status_parceiro": "TEXT DEFAULT 'Pendente'",
  }

  for col, tipo in colunas_para_adicionar.items():
    if col not in colunas:
      try:
        cursor.execute(f"ALTER TABLE demandas ADD COLUMN {col} {tipo}")
      except sqlite3.OperationalError:
        pass

  # Tabela de Utilizadores
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilizadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            cargo TEXT NOT NULL
        )
    """)

  # Tabela de Gastos da Empresa
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL DEFAULT 0.0,
            data_gasto DATE NOT NULL,
            status TEXT DEFAULT 'Pago'
        )
    """)

  # Tabela de Pagamentos de Funcionários
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS pagamentos_equipe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario TEXT NOT NULL,
            mes INTEGER NOT NULL,
            ano INTEGER NOT NULL,
            salario_base REAL DEFAULT 0.0,
            transporte REAL DEFAULT 0.0,
            almoco REAL DEFAULT 0.0,
            bonus REAL DEFAULT 0.0,
            descontos REAL DEFAULT 0.0,
            total_calculado REAL DEFAULT 0.0,
            status_pagamento TEXT DEFAULT 'Pendente',
            data_registro DATE NOT NULL
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM utilizadores")
  if cursor.fetchone()[0] == 0:
    cursor.execute(
        """
            INSERT INTO utilizadores (usuario, senha, cargo) 
            VALUES (?, ?, ?)
        """,
        ("admin", "admin123", "CEO / Administração"),
    )

  conn.commit()
  conn.close()


init_db()


def carregar_dados():
  conn = sqlite3.connect("sds_imoveis.db")
  df = pd.read_sql("SELECT * FROM demandas", conn)
  conn.close()
  if not df.empty:
    df["prazo"] = pd.to_datetime(df["prazo"])
    df["Ano"] = df["prazo"].dt.year
    df["Mês"] = df["prazo"].dt.month
    df["adquirente"] = df["adquirente"].fillna("")
    df["numero_imovel"] = df["numero_imovel"].fillna("")
    df["taxa_desc"] = df["taxa_desc"].fillna(0.0)
    df["tipo_imovel"] = df["tipo_imovel"].fillna("Caixa")
    df["parceria"] = df["parceria"].fillna("Não")
    df["parceiro_nome"] = df["parceiro_nome"].fillna("")
    df["pct_sds"] = df["pct_sds"].fillna(100.0)
    if "status_parceiro" not in df.columns:
      df["status_parceiro"] = "Pendente"
    df["status_parceiro"] = df["status_parceiro"].fillna("Pendente")

    df["valor_liquido"] = df["valor"] * (1 - df["taxa_desc"] / 100.0)
    df["lucro_SDS"] = df["valor_liquido"] * (df["pct_sds"] / 100.0)
    df["Lucro_Parceiro (R$)"] = df["valor_liquido"] - df["lucro_SDS"]
  return df


def carregar_gastos():
  conn = sqlite3.connect("sds_imoveis.db")
  df_g = pd.read_sql("SELECT * FROM gastos", conn)
  conn.close()
  if not df_g.empty:
    df_g["data_gasto"] = pd.to_datetime(df_g["data_gasto"])
    df_g["Ano"] = df_g["data_gasto"].dt.year
    df_g["Mês"] = df_g["data_gasto"].dt.month
  return df_g


def carregar_pagamentos_equipe():
  conn = sqlite3.connect("sds_imoveis.db")
  df_p = pd.read_sql("SELECT * FROM pagamentos_equipe", conn)
  conn.close()
  return df_p


# ---------------------------------------------------------
# SISTEMA DE LOGIN E SESSÃO
# ---------------------------------------------------------
if "autenticado" not in st.session_state:
  st.session_state["autenticado"] = False
  st.session_state["usuario"] = ""
  st.session_state["cargo"] = ""

if not st.session_state["autenticado"]:
  st.markdown(
      "<h1 style='text-align: center; color: #1B263B;'>🏢 SDS Imóveis -"
      " Acesso Restrito</h1>",
      unsafe_allow_html=True,
  )

  aba_login, aba_registo, aba_esqueci = st.tabs([
      "Entrar",
      "Registrar Novo Colaborador",
      "Esqueci a Senha",
  ])

  with aba_login:
    st.subheader("Iniciar Sessão")
    with st.form("form_login"):
      user_input = st.text_input("Utilizador")
      senha_input = st.text_input("Senha", type="password")
      btn_login = st.form_submit_button("Entrar")

      if btn_login:
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cargo FROM utilizadores WHERE usuario = ? AND senha = ?",
            (user_input, senha_input),
        )
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
          st.session_state["autenticado"] = True
          st.session_state["usuario"] = user_input
          st.session_state["cargo"] = resultado[0]
          st.success("Login efetuado com sucesso!")
          st.rerun()
        else:
          st.error("Utilizador ou senha incorretos.")

  with aba_registo:
    st.subheader("Registrar Novo Colaborador")
    with st.form("form_registo"):
      novo_user = st.text_input("Escolha um Nome de Utilizador")
      nova_senha = st.text_input("Escolha uma Senha", type="password")
      novo_cargo = st.selectbox(
          "Cargo Pretendido", ["Corretor", "Funcionário", "CEO / Administração"]
      )

      chave_adm_input = st.text_input(
          "Chave de Segurança ADM (Obrigatório apenas para CEO /"
          " Administração)",
          type="password",
          help="Exigida para liberar privilégios de diretoria.",
      )

      btn_reg = st.form_submit_button("Registrar Conta")

      if btn_reg:
        if novo_user and nova_senha:
          if novo_cargo == "CEO / Administração":
            if chave_adm_input != CHAVE_MESTRA_CEO:
              st.error(
                  "⛔ Chave de Segurança ADM incorreta! Registro de CEO /"
                  " Administração bloqueado."
              )
              st.stop()

          try:
            conn = sqlite3.connect("sds_imoveis.db")
            cursor = conn.cursor()
            cursor.execute(
                """
                            INSERT INTO utilizadores (usuario, senha, cargo) 
                            VALUES (?, ?, ?)
                        """,
                (novo_user, nova_senha, novo_cargo),
            )
            conn.commit()
            conn.close()
            st.success("Registro efetuado com sucesso! Faça login.")
          except sqlite3.IntegrityError:
            st.error("Este nome de utilizador já existe.")
        else:
          st.error("Preencha todos os campos obrigatórios.")

  with aba_esqueci:
    st.subheader("Redefinir / Esqueci a Senha")
    with st.form("form_esqueci_senha"):
      user_rec = st.text_input("Informe seu Nome de Utilizador")
      nova_senha_rec = st.text_input("Digite a Nova Senha", type="password")
      confirma_senha_rec = st.text_input(
          "Confirme a Nova Senha", type="password"
      )
      btn_rec = st.form_submit_button("Redefinir Senha")

      if btn_rec:
        if user_rec and nova_senha_rec and confirma_senha_rec:
          if nova_senha_rec == confirma_senha_rec:
            conn = sqlite3.connect("sds_imoveis.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM utilizadores WHERE usuario = ?", (user_rec,)
            )
            if cursor.fetchone():
              cursor.execute(
                  "UPDATE utilizadores SET senha = ? WHERE usuario = ?",
                  (nova_senha_rec, user_rec),
              )
              conn.commit()
              conn.close()
              st.success("Senha redefinida com sucesso!")
            else:
              conn.close()
              st.error("Usuário não encontrado.")
          else:
            st.error("As senhas não coincidem.")
        else:
          st.error("Preencha todos os campos.")

  st.stop()

# ---------------------------------------------------------
# APLICAÇÃO PRINCIPAL (APÓS LOGIN)
# ---------------------------------------------------------
logo_encontrada = False
for nome_logo in ["logo_sds.png", "logo_sds.png.jpeg", "logo_sds.jpeg"]:
  if os.path.exists(nome_logo):
    st.sidebar.image(nome_logo, use_container_width=True)
    logo_encontrada = True
    break

if not logo_encontrada:
  st.sidebar.markdown(
      "<h2 style='text-align: center; color: #C5A059;'>🏢 SDS Imóveis</h2>",
      unsafe_allow_html=True,
  )

st.sidebar.markdown(f"**Utilizador:** {st.session_state['usuario']}")
st.sidebar.markdown(f"**Cargo:** {st.session_state['cargo']}")
st.sidebar.markdown("---")

# Restrição do Menu pelo Cargo
if st.session_state["cargo"] == "CEO / Administração":
  opcoes_menu = [
      "Dashboard",
      "Gestão de Demanda",
      "Faturamento",
      "🤝 Controle de Repasse a Parceiros",
      "💸 Gestão de Gastos",
      "👔 Pagamentos de Funcionários",
      "Relatórios",
      "👥 Gerenciar Usuários",
      "🧮 Calculadora",
  ]
else:
  opcoes_menu = ["Dashboard", "Gestão de Demanda", "🧮 Calculadora"]

menu = st.sidebar.selectbox("Navegação", opcoes_menu)

# ---------------------------------------------------------
# CALCULADORA RÁPIDA NA BARRA LATERAL
# ---------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("🧮 Calculadora Rápida", expanded=False):
  calc_v1 = st.number_input("Valor (R$)", min_value=0.0, step=100.0, key="c_v1")
  calc_p = st.number_input(
      "Porcentagem (%)", min_value=0.0, max_value=100.0, step=1.0, key="c_p"
  )
  operacao = st.radio(
      "Operação", ["Calcular %", "Descontar %", "Somar %"], key="c_op"
  )

  if operacao == "Calcular %":
    res_c = calc_v1 * (calc_p / 100.0)
    st.info(f"**Resultado:** R$ {res_c:,.2f}")
  elif operacao == "Descontar %":
    res_c = calc_v1 * (1 - calc_p / 100.0)
    st.info(f"**Resultado Líquido:** R$ {res_c:,.2f}")
  else:
    res_c = calc_v1 * (1 + calc_p / 100.0)
    st.info(f"**Resultado com Adicional:** R$ {res_c:,.2f}")

st.sidebar.markdown("---")
if st.sidebar.button("Terminar Sessão (Logout)"):
  st.session_state["autenticado"] = False
  st.rerun()

meses_nomes = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}

# ---------------------------------------------------------
# 1. DASHBOARD
# ---------------------------------------------------------
if menu == "Dashboard":
  st.title("📊 Painel de Controle - SDS Imóveis")
  st.write(
      "Visão geral das demandas, indicadores e desempenho da imobiliária."
  )

  df = carregar_dados()

  if not df.empty:
    total_demandas = len(df)
    pendentes = len(df[df["status"] == "Pendente"])
    concluidas = len(df[df["status"] == "Concluída"])
    atrasadas = len(df[df["status"] == "Atrasada"])

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    col1.metric("Total de Demandas", total_demandas)
    col2.metric("Pendentes", pendentes)
    col3.metric("Concluídas", concluidas)
    col4.metric("Atrasadas", atrasadas)

    st.markdown("---")

    anos_disponiveis = sorted(df["Ano"].dropna().unique(), reverse=True)
    ano_grafico = st.selectbox(
        "Selecione o Ano para o Gráfico de Desempenho", anos_disponiveis
    )

    df_ano_dash = df[df["Ano"] == ano_grafico]

    dados_grafico = []
    for m in range(1, 13):
      df_mes = df_ano_dash[df_ano_dash["Mês"] == m]
      recebido_mes = df_mes[df_mes["pagamento"] == "Recebido"][
          "lucro_SDS"
      ].sum()
      pendente_mes = df_mes[df_mes["pagamento"] == "Pendente"][
          "lucro_SDS"
      ].sum()
      dados_grafico.append({
          "Mês": meses_nomes[m],
          "Recebido SDS (R$)": recebido_mes,
          "Pendente SDS (R$)": pendente_mes,
      })

    df_chart = pd.DataFrame(dados_grafico)
    df_chart.set_index("Mês", inplace=True)

    st.subheader(f"📈 Desempenho Financeiro SDS ({ano_grafico})")
    st.bar_chart(df_chart)

    st.markdown("---")
    st.subheader("Demandas Recentes")
    st.dataframe(df.tail(5), use_container_width=True)
  else:
    st.info("Nenhuma demanda cadastrada no banco de dados ainda.")

# ---------------------------------------------------------
# 2. GESTÃO DE DEMANDAS
# ---------------------------------------------------------
elif menu == "Gestão de Demanda":
  st.title("🛠️ Gestão de Demandas")

  with st.form("form_demanda", clear_on_submit=True):
    st.subheader("Cadastrar Nova Demanda (ou Demanda Retroativa)")
    col1, col2 = st.columns(2)
    with col1:
      adquirente = st.text_input("Nome do Adquirente")
      numero_imovel = st.text_input("Número do Imóvel / CHB")
      responsavel = st.text_input("Responsável SDS")
    with col2:
      tipo_imovel = st.selectbox(
          "Tipo de Imóvel", ["Caixa", "Tenda", "Novo", "Usado", "Outros"], index=0
      )
      status = st.selectbox(
          "Status", ["Pendente", "Em Andamento", "Concluída", "Atrasada"]
      )
      prazo = st.date_input("Data / Prazo de Entrega", datetime.date.today())

    st.markdown("**💰 Valores e Taxas / Tratamento Contábil**")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
      valor = st.number_input(
          "Valor Bruto / Comissão Total (R$)", min_value=0.0, format="%.2f"
      )
    with col_v2:
      taxa_desc = st.number_input(
          "Taxa / Desconto (%) (Ex: 14.45)",
          min_value=0.0,
          max_value=100.0,
          value=0.0,
          step=0.05,
      )

    st.markdown("**🤝 Informações de Parceria e Divisão de Lucro**")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
      parceria = st.selectbox("Possui Parceria?", ["Não", "Sim"])
    with col_p2:
      parceiro_nome = st.text_input(
          "Nome do Parceiro / Imobiliária",
          disabled=(parceria == "Não"),
          placeholder="Ex: Corretor X",
      )
    with col_p3:
      pct_sds = st.number_input(
          "% de Lucro da SDS Imóveis",
          min_value=0.0,
          max_value=100.0,
          value=100.0 if parceria == "Não" else 50.0,
          step=5.0,
      )

    pagamento = st.selectbox("Status do Pagamento", ["Pendente", "Recebido"])

    submit = st.form_submit_button("Salvar Demanda")

    if submit:
      if adquirente and numero_imovel and responsavel:
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()

        # Inserção Dinâmica para Evitar Erros de Colunas Ausentes no SQLite
        cursor.execute("PRAGMA table_info(demandas)")
        cols_existentes = [col[1] for col in cursor.fetchall()]

        dados_insercao = {
            "adquirente": adquirente,
            "numero_imovel": numero_imovel,
            "responsavel": responsavel,
            "status": status,
            "prazo": str(prazo),
            "valor": valor,
            "taxa_desc": taxa_desc,
            "pagamento": pagamento,
            "tipo_imovel": tipo_imovel,
            "parceria": parceria,
            "parceiro_nome": parceiro_nome if parceria == "Sim" else "",
            "pct_sds": pct_sds,
            "status_parceiro": "Pendente",
        }

        # Filtra apenas colunas que realmente existem na tabela atual
        cols_validas = [k for k in dados_insercao.keys() if k in cols_existentes]
        valores_validos = [dados_insercao[k] for k in cols_validas]

        campos_sql = ", ".join(cols_validas)
        placeholders = ", ".join(["?"] * len(cols_validas))

        sql_query = (
            f"INSERT INTO demandas ({campos_sql}) VALUES ({placeholders})"
        )
        cursor.execute(sql_query, valores_validos)

        conn.commit()
        conn.close()
        st.success("Demanda cadastrada com sucesso!")
        st.rerun()
      else:
        st.error(
            "Preencha os campos obrigatórios (Adquirente, Número do Imóvel e"
            " Responsável)."
        )

  st.markdown("---")

  st.subheader("Demandas Cadastradas")
  df = carregar_dados()

  if not df.empty:
    st.markdown("🔍 **Pesquisador Rápido de Demandas**")
    termo_busca = st.text_input(
        "Buscar por Adquirente ou Número do Imóvel / CHB",
        placeholder="Digite o nome do adquirente ou o número do imóvel...",
    )

    col_f1, col_f2 = st.columns(2)
    with col_f1:
      filtro_tipo = st.selectbox(
          "Filtrar por Categoria",
          ["Todos", "Caixa", "Tenda", "Novo", "Usado", "Outros"],
      )
    with col_f2:
      filtro_parc = st.selectbox(
          "Filtrar por Parceria", ["Todos", "Sim", "Não"]
      )

    df_exibir = df.copy()

    if termo_busca.strip():
      df_exibir = df_exibir[
          df_exibir["adquirente"]
          .str.contains(termo_busca, case=False, na=False)
          | df_exibir["numero_imovel"]
          .str.contains(termo_busca, case=False, na=False)
      ]

    if filtro_tipo != "Todos":
      df_exibir = df_exibir[df_exibir["tipo_imovel"] == filtro_tipo]
    if filtro_parc != "Todos":
      df_exibir = df_exibir[df_exibir["parceria"] == filtro_parc]

    cols_view = [
        "id",
        "adquirente",
        "numero_imovel",
        "responsavel",
        "tipo_imovel",
        "parceiro_nome",
        "status",
        "valor",
        "taxa_desc",
        "valor_liquido",
        "lucro_SDS",
        "pagamento",
    ]
    st.dataframe(df_exibir[cols_view], use_container_width=True)

    st.markdown("---")
    st.subheader("📝 Editar ou Excluir Demanda")

    id_selecionado = st.selectbox(
        "Selecione o ID da Demanda para Editar ou Excluir", df["id"].tolist()
    )

    demanda_sel = df[df["id"] == id_selecionado].iloc[0]

    with st.expander(
        f"Clique para Editar os Dados da Demanda ID {id_selecionado}",
        expanded=True,
    ):
      with st.form("form_editar_demanda"):
        col_e1, col_e2 = st.columns(2)
        with col_e1:
          edit_adquirente = st.text_input(
              "Adquirente", value=str(demanda_sel["adquirente"])
          )
          edit_numero_imovel = st.text_input(
              "Número do Imóvel", value=str(demanda_sel["numero_imovel"])
          )
          edit_responsavel = st.text_input(
              "Responsável SDS", value=str(demanda_sel["responsavel"])
          )

        with col_e2:
          tipos_list = ["Caixa", "Tenda", "Novo", "Usado", "Outros"]
          edit_tipo_imovel = st.selectbox(
              "Tipo de Imóvel",
              tipos_list,
              index=tipos_list.index(demanda_sel["tipo_imovel"])
              if demanda_sel["tipo_imovel"] in tipos_list
              else 0,
          )

          status_list = ["Pendente", "Em Andamento", "Concluída", "Atrasada"]
          edit_status = st.selectbox(
              "Status",
              status_list,
              index=status_list.index(demanda_sel["status"])
              if demanda_sel["status"] in status_list
              else 0,
          )

          dt_prazo = (
              demanda_sel["prazo"].date()
              if hasattr(demanda_sel["prazo"], "date")
              else datetime.date.today()
          )
          edit_prazo = st.date_input("Prazo de Entrega", dt_prazo)

        st.markdown("**Valores e Taxas / Contabilidade**")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1:
          edit_valor = st.number_input(
              "Valor Bruto (R$)",
              min_value=0.0,
              value=float(demanda_sel["valor"]),
              format="%.2f",
          )
        with col_ev2:
          edit_taxa_desc = st.number_input(
              "Taxa / Desconto (%)",
              min_value=0.0,
              max_value=100.0,
              value=float(demanda_sel["taxa_desc"]),
              step=0.05,
          )

        st.markdown("**Parceria e Divisão de Lucro**")
        col_ep1, col_ep2, col_ep3 = st.columns(3)
        with col_ep1:
          edit_parceria = st.selectbox(
              "Possui Parceria?",
              ["Não", "Sim"],
              index=0 if demanda_sel["parceria"] == "Não" else 1,
          )
        with col_ep2:
          edit_parceiro_nome = st.text_input(
              "Nome do Parceiro", value=str(demanda_sel["parceiro_nome"])
          )
        with col_ep3:
          edit_pct_sds = st.number_input(
              "% Lucro SDS",
              min_value=0.0,
              max_value=100.0,
              value=float(demanda_sel["pct_sds"]),
              step=5.0,
          )

        edit_pagamento = st.selectbox(
            "Status do Pagamento",
            ["Pendente", "Recebido"],
            index=0 if demanda_sel["pagamento"] == "Pendente" else 1,
        )

        btn_salvar_edicao = st.form_submit_button("💾 Salvar Alterações")

        if btn_salvar_edicao:
          conn = sqlite3.connect("sds_imoveis.db")
          cursor = conn.cursor()
          cursor.execute(
              """
                    UPDATE demandas
                    SET adquirente = ?, numero_imovel = ?, responsavel = ?, tipo_imovel = ?,
                        status = ?, prazo = ?, parceria = ?, parceiro_nome = ?, pct_sds = ?,
                        valor = ?, taxa_desc = ?, pagamento = ?
                    WHERE id = ?
                """,
              (
                  edit_adquirente,
                  edit_numero_imovel,
                  edit_responsavel,
                  edit_tipo_imovel,
                  edit_status,
                  str(edit_prazo),
                  edit_parceria,
                  edit_parceiro_nome,
                  edit_pct_sds,
                  edit_valor,
                  edit_taxa_desc,
                  edit_pagamento,
                  id_selecionado,
              ),
          )
          conn.commit()
          conn.close()
          st.success(f"Demanda ID {id_selecionado} atualizada com sucesso!")
          st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Excluir Esta Demanda"):
      conn = sqlite3.connect("sds_imoveis.db")
      cursor = conn.cursor()
      cursor.execute("DELETE FROM demandas WHERE id = ?", (id_selecionado,))
      conn.commit()
      conn.close()
      st.success(f"Demanda ID {id_selecionado} excluída com sucesso!")
      st.rerun()

  else:
    st.info("Nenhum registo encontrado.")

# ---------------------------------------------------------
# 3. FATURAMENTO (EXCLUSIVO CEO / ADM)
# ---------------------------------------------------------
elif menu == "Faturamento":
  st.title("💰 Controle de Faturamento e Lucro Líquido Real")

  df = carregar_dados()
  df_g = carregar_gastos()

  if not df.empty:
    anos_disponiveis = sorted(df["Ano"].dropna().unique(), reverse=True)
    ano_selecionado = st.selectbox("Filtrar por Ano", anos_disponiveis)

    df_ano = df[df["Ano"] == ano_selecionado]
    df_g_ano = (
        df_g[df_g["Ano"] == ano_selecionado] if not df_g.empty else pd.DataFrame()
    )

    total_recebido_sds = df_ano[df_ano["pagamento"] == "Recebido"][
        "lucro_SDS"
    ].sum()
    total_pendente_sds = df_ano[df_ano["pagamento"] == "Pendente"][
        "lucro_SDS"
    ].sum()
    total_gastos = df_g_ano["valor"].sum() if not df_g_ano.empty else 0.0
    lucro_real = total_recebido_sds - total_gastos

    st.subheader(f"📅 Resumo Financeiro do Ano: {ano_selecionado}")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    col1.metric("Recebido SDS (Bruto Líquido)", f"R$ {total_recebido_sds:,.2f}")
    col2.metric("Total de Gastos", f"R$ {total_gastos:,.2f}")
    col3.metric("Lucro Real SDS (Entradas - Gastos)", f"R$ {lucro_real:,.2f}")
    col4.metric("Pendente a Receber SDS", f"R$ {total_pendente_sds:,.2f}")

    st.markdown("---")
    st.subheader("📊 Faturamento SDS por Mês")

    resumo_mensal = []
    for m in range(1, 13):
      df_mes = df_ano[df_ano["Mês"] == m]
      df_g_mes = (
          df_g_ano[df_g_ano["Mês"] == m] if not df_g_ano.empty else pd.DataFrame()
      )

      rec_mes = df_mes[df_mes["pagamento"] == "Recebido"]["lucro_SDS"].sum()
      pend_mes = df_mes[df_mes["pagamento"] == "Pendente"]["lucro_SDS"].sum()
      gastos_mes = df_g_mes["valor"].sum() if not df_g_mes.empty else 0.0
      lucro_mes = rec_mes - gastos_mes

      if not df_mes.empty or rec_mes > 0 or pend_mes > 0 or gastos_mes > 0:
        resumo_mensal.append({
            "Mês": meses_nomes[m],
            "Recebido SDS (R$)": rec_mes,
            "Gastos (R$)": gastos_mes,
            "Lucro Real Mês (R$)": lucro_mes,
            "Pendente SDS (R$)": pend_mes,
        })

    if resumo_mensal:
      df_resumo_mensal = pd.DataFrame(resumo_mensal)
      st.dataframe(df_resumo_mensal, use_container_width=True)
    else:
      st.info(f"Sem movimentações registadas para o ano {ano_selecionado}.")

    st.markdown("---")
    st.subheader(f"Detalhamento de Entradas ({ano_selecionado})")
    cols_fat = [
        "id",
        "adquirente",
        "numero_imovel",
        "responsavel",
        "tipo_imovel",
        "parceiro_nome",
        "valor",
        "taxa_desc",
        "valor_liquido",
        "pct_sds",
        "lucro_SDS",
        "pagamento",
    ]
    st.dataframe(df_ano[cols_fat], use_container_width=True)
  else:
    st.info("Sem dados financeiros disponíveis.")

# ---------------------------------------------------------
# 4. CONTROLE DE REPASSE A PARCEIROS (EXCLUSIVO CEO / ADM)
# ---------------------------------------------------------
elif menu == "🤝 Controle de Repasse a Parceiros":
  st.title("🤝 Gestão de Comissões e Repasses a Parceiros")
  st.write(
      "Acompanhe o que precisa ser pago aos parceiros para manter as contas"
      " em dia."
  )

  df = carregar_dados()

  if not df.empty:
    df_parcerias = df[df["parceria"] == "Sim"].copy()

    if not df_parcerias.empty:
      df_pendentes_parc = df_parcerias[
          (df_parcerias["pagamento"] == "Recebido")
          & (df_parcerias["status_parceiro"] == "Pendente")
      ]
      total_devido_parceiros = df_pendentes_parc["Lucro_Parceiro (R$)"].sum()

      df_pagos_parc = df_parcerias[df_parcerias["status_parceiro"] == "Pago"]
      total_ja_pago_parceiros = df_pagos_parc["Lucro_Parceiro (R$)"].sum()

      col_pr1, col_pr2 = st.columns(2)
      col_pr1.metric(
          "🔴 Total Pendente A Pagar a Parceiros",
          f"R$ {total_devido_parceiros:,.2f}",
      )
      col_pr2.metric(
          "🟢 Total Já Repassado a Parceiros", f"R$ {total_ja_pago_parceiros:,.2f}"
      )

      st.markdown("---")

      st.subheader("🚨 Repasses Pendentes (Ação Necessária)")
      if not df_pendentes_parc.empty:
        cols_p_view = [
            "id",
            "parceiro_nome",
            "adquirente",
            "numero_imovel",
            "valor_liquido",
            "Lucro_Parceiro (R$)",
            "status_parceiro",
        ]
        st.dataframe(df_pendentes_parc[cols_p_view], use_container_width=True)

        st.markdown("### 💳 Baixa de Repasse")
        id_parc_dar_baixa = st.selectbox(
            "Selecione o ID da Demanda para confirmar o repasse efetuado",
            df_pendentes_parc["id"].tolist(),
        )

        if st.button("✅ Confirmar Repasse Efetuado ao Parceiro"):
          conn = sqlite3.connect("sds_imoveis.db")
          cursor = conn.cursor()
          cursor.execute(
              "UPDATE demandas SET status_parceiro = 'Pago' WHERE id = ?",
              (id_parc_dar_baixa,),
          )
          conn.commit()
          conn.close()
          st.success(
              f"Repasse referente à demanda ID {id_parc_dar_baixa} confirmado"
              " com sucesso!"
          )
          st.rerun()
      else:
        st.success(
            "🎉 Excelente! Não há nenhum repasse pendente a parceiros no"
            " momento."
        )

      st.markdown("---")
      st.subheader("📜 Histórico Geral de Parcerias")
      cols_hist = [
          "id",
          "parceiro_nome",
          "adquirente",
          "numero_imovel",
          "valor_liquido",
          "lucro_SDS",
          "Lucro_Parceiro (R$)",
          "pagamento",
          "status_parceiro",
      ]
      st.dataframe(df_parcerias[cols_hist], use_container_width=True)

    else:
      st.info("Nenhuma demanda cadastrada com parceria até o momento.")
  else:
    st.info("Sem demandas cadastradas no sistema.")

# ---------------------------------------------------------
# 5. GESTÃO DE GASTOS (EXCLUSIVO CEO / ADM)
# ---------------------------------------------------------
elif menu == "💸 Gestão de Gastos":
  st.title("💸 Controle de Gastos e Despesas da Empresa")
  st.write("Cadastre e acompanhe os custos fixos e variáveis da SDS Imóveis.")

  with st.form("form_gastos", clear_on_submit=True):
    st.subheader("➕ Cadastrar Novo Gasto / Despesa")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
      desc_gasto = st.text_input(
          "Descrição do Gasto (Ex: Aluguel, Anúncio Meta, Contador)"
      )
      valor_gasto = st.number_input(
          "Valor do Gasto (R$)", min_value=0.0, format="%.2f"
      )
      data_gasto = st.date_input(
          "Data do Pagamento / Vencimento", datetime.date.today()
      )
    with col_g2:
      tipo_gasto = st.selectbox("Tipo de Gasto", ["Fixo", "Variável"])
      categoria_gasto = st.selectbox("Categoria", [
          "Infraestrutura / Aluguel",
          "Marketing / Anúncios",
          "Sistemas / Software",
          "Impostos / Contador",
          "Folha de Pagamento",
          "Manutenção / Material",
          "Outros",
      ])
      status_gasto = st.selectbox("Status", ["Pago", "Pendente"])

    submit_gasto = st.form_submit_button("Salvar Despesa")

    if submit_gasto:
      if desc_gasto and valor_gasto > 0:
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO gastos (descricao, tipo, categoria, valor, data_gasto, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                desc_gasto,
                tipo_gasto,
                categoria_gasto,
                valor_gasto,
                str(data_gasto),
                status_gasto,
            ),
        )
        conn.commit()
        conn.close()
        st.success("Gasto cadastrado com sucesso!")
        st.rerun()
      else:
        st.error("Preencha a descrição e informe um valor maior que zero.")

  st.markdown("---")

  df_g = carregar_gastos()

  if not df_g.empty:
    anos_gastos = sorted(df_g["Ano"].dropna().unique(), reverse=True)
    ano_filtro_g = st.selectbox("Filtrar Gastos por Ano", anos_gastos)

    df_g_filtrado = df_g[df_g["Ano"] == ano_filtro_g]

    total_fixos = df_g_filtrado[df_g_filtrado["tipo"] == "Fixo"]["valor"].sum()
    total_variaveis = df_g_filtrado[df_g_filtrado["tipo"] == "Variável"][
        "valor"
    ].sum()
    total_geral_gastos = df_g_filtrado["valor"].sum()

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total de Gastos Fixos", f"R$ {total_fixos:,.2f}")
    col_m2.metric("Total de Gastos Variáveis", f"R$ {total_variaveis:,.2f}")
    col_m3.metric("Total Geral de Despesas", f"R$ {total_geral_gastos:,.2f}")

    st.markdown("---")
    st.subheader("📋 Tabela de Gastos Registrados")
    st.dataframe(
        df_g_filtrado[[
            "id",
            "descricao",
            "tipo",
            "categoria",
            "valor",
            "data_gasto",
            "status",
        ]],
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("🗑️ Excluir Registro de Gasto")
    id_gasto_del = st.selectbox(
        "Selecione o ID do Gasto para Excluir", df_g_filtrado["id"].tolist()
    )
    if st.button("Excluir Este Gasto"):
      conn = sqlite3.connect("sds_imoveis.db")
      cursor = conn.cursor()
      cursor.execute("DELETE FROM gastos WHERE id = ?", (id_gasto_del,))
      conn.commit()
      conn.close()
      st.success(f"Gasto ID {id_gasto_del} removido com sucesso!")
      st.rerun()
  else:
    st.info("Nenum gasto ou despesa cadastrado ainda.")

# ---------------------------------------------------------
# 6. PAGAMENTOS DE FUNCIONÁRIOS (EXCLUSIVO CEO / ADM)
# ---------------------------------------------------------
elif menu == "👔 Pagamentos de Funcionários":
  st.title("👔 Gestão de Pessoal e Benefícios (Folha Mensal)")
  st.write(
      "Controle salários, vale transporte, refeição/almoço e bônus de forma"
      " individualizada."
  )

  conn = sqlite3.connect("sds_imoveis.db")
  df_users = pd.read_sql(
      "SELECT usuario, cargo FROM utilizadores WHERE cargo != 'CEO /"
      " Administração'",
      conn,
  )
  conn.close()

  lista_funcionarios = (
      df_users["usuario"].tolist() if not df_users.empty else []
  )

  st.subheader("➕ Novo Lançamento de Pagamento")
  with st.form("form_folha_pagamento", clear_on_submit=True):
    col_p1, col_p2, col_p3 = st.columns(3)

    with col_p1:
      func_opcao = st.selectbox(
          "Selecione o Colaborador Cadastrado",
          ["Digite o Nome Manualmente..."] + lista_funcionarios,
      )
      if func_opcao == "Digite o Nome Manualmente...":
        nome_funcionario = st.text_input("Nome do Colaborador / Funcionário")
      else:
        nome_funcionario = func_opcao

      mes_ref = st.selectbox(
          "Mês de Referência",
          list(range(1, 13)),
          format_func=lambda x: meses_nomes[x],
          index=datetime.date.today().month - 1,
      )
      ano_ref = st.number_input(
          "Ano de Referência", value=datetime.date.today().year, step=1
      )

    with col_p2:
      salario_base = st.number_input(
          "Salário Base (R$)", min_value=0.0, format="%.2f"
      )
      transporte = st.number_input(
          "Vale Transporte (R$)", min_value=0.0, format="%.2f"
      )
      almoco = st.number_input(
          "Vale Alimentação / Almoço (R$)", min_value=0.0, format="%.2f"
      )

    with col_p3:
      bonus = st.number_input(
          "Bônus / Comissão / Extra (R$)", min_value=0.0, format="%.2f"
      )
      descontos = st.number_input(
          "Descontos / Faltas (R$)", min_value=0.0, format="%.2f"
      )
      status_pag_func = st.selectbox(
          "Status do Pagamento", ["Pendente", "Pago"]
      )

    total_pago_calc = salario_base + transporte + almoco + bonus - descontos
    st.info(f"💰 **Total Líquido A Pagar:** R$ {total_pago_calc:,.2f}")

    btn_salvar_folha = st.form_submit_button("Salvar Registro de Pagamento")

    if btn_salvar_folha:
      if nome_funcionario and total_pago_calc > 0:
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()
        cursor.execute(
            """
                    INSERT INTO pagamentos_equipe (funcionario, mes, ano, salario_base, transporte, almoco, bonus, descontos, total_calculado, status_pagamento, data_registro)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                nome_funcionario,
                mes_ref,
                ano_ref,
                salario_base,
                transporte,
                almoco,
                bonus,
                descontos,
                total_pago_calc,
                status_pag_func,
                str(datetime.date.today()),
            ),
        )

        if status_pag_func == "Pago":
          desc_auto = (
              f"Folha/Benefícios - {nome_funcionario} ({meses_nomes[mes_ref]}/{ano_ref})"
          )
          cursor.execute(
              """
                        INSERT INTO gastos (descricao, tipo, categoria, valor, data_gasto, status)
                        VALUES (?, 'Fixo', 'Folha de Pagamento', ?, ?, 'Pago')
                    """,
              (desc_auto, total_pago_calc, str(datetime.date.today())),
          )

        conn.commit()
        conn.close()
        st.success("Lançamento de pagamento salvo com sucesso!")
        st.rerun()
      else:
        st.error(
            "Informe o nome do funcionário e garanta que o valor total seja"
            " maior que R$ 0,00."
        )

  st.markdown("---")

  df_p = carregar_pagamentos_equipe()

  if not df_p.empty:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      ano_folha = st.selectbox(
          "Filtrar por Ano", sorted(df_p["ano"].unique(), reverse=True)
      )
    with col_f2:
      status_folha_filtro = st.selectbox(
          "Filtrar por Status de Pagamento", ["Todos", "Pendente", "Pago"]
      )

    df_p_filtrado = df_p[df_p["ano"] == ano_folha]
    if status_folha_filtro != "Todos":
      df_p_filtrado = df_p_filtrado[
          df_p_filtrado["status_pagamento"] == status_folha_filtro
      ]

    total_pendente_folha = df_p_filtrado[
        df_p_filtrado["status_pagamento"] == "Pendente"
    ]["total_calculado"].sum()
    total_pago_folha = df_p_filtrado[
        df_p_filtrado["status_pagamento"] == "Pago"
    ]["total_calculado"].sum()

    col_m1, col_m2 = st.columns(2)
    col_m1.metric(
        "🔴 Total Pendente (A Pagar)", f"R$ {total_pendente_folha:,.2f}"
    )
    col_m2.metric("🟢 Total Pago", f"R$ {total_pago_folha:,.2f}")

    st.markdown("---")
    st.subheader("📋 Histórico de Pagamentos e Benefícios")

    df_p_display = df_p_filtrado.copy()
    df_p_display["Mês Ref."] = df_p_display["mes"].apply(
        lambda x: meses_nomes.get(x, x)
    )
    cols_equipe = [
        "id",
        "funcionario",
        "Mês Ref.",
        "ano",
        "salario_base",
        "transporte",
        "almoco",
        "bonus",
        "descontos",
        "total_calculado",
        "status_pagamento",
    ]
    st.dataframe(df_p_display[cols_equipe], use_container_width=True)

    st.markdown("---")
    st.subheader("📝 Alterar Status ou Excluir Lançamento")

    id_p_sel = st.selectbox(
        "Selecione o ID do Lançamento", df_p_filtrado["id"].tolist()
    )

    col_a1, col_a2 = st.columns(2)
    with col_a1:
      if st.button("✅ Marcar como PAGO"):
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT funcionario, mes, ano, total_calculado FROM"
            " pagamentos_equipe WHERE id = ?",
            (id_p_sel,),
        )
        row = cursor.fetchone()

        cursor.execute(
            "UPDATE pagamentos_equipe SET status_pagamento = 'Pago' WHERE id ="
            " ?",
            (id_p_sel,),
        )

        if row:
          desc_auto = (
              f"Folha/Benefícios - {row[0]} ({meses_nomes[row[1]]}/{row[2]})"
          )
          cursor.execute(
              """
                        INSERT INTO gastos (descricao, tipo, categoria, valor, data_gasto, status)
                        VALUES (?, 'Fixo', 'Folha de Pagamento', ?, ?, 'Pago')
                    """,
              (desc_auto, row[3], str(datetime.date.today())),
          )

        conn.commit()
        conn.close()
        st.success(f"Lançamento ID {id_p_sel} marcado como PAGO!")
        st.rerun()

    with col_a2:
      if st.button("🗑️ Excluir Registro de Pagamento"):
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM pagamentos_equipe WHERE id = ?", (id_p_sel,)
        )
        conn.commit()
        conn.close()
        st.success(f"Lançamento ID {id_p_sel} excluído com sucesso!")
        st.rerun()

  else:
    st.info("Nenhum pagamento registrado para a equipe ainda.")

# ---------------------------------------------------------
# 7. RELATÓRIOS (EXCLUSIVO CEO / ADM)
# ---------------------------------------------------------
elif menu == "Relatórios":
  st.title("📈 Relatórios e Exportação Avançada")
  st.write(
      "Visualize o resumo analítico e descarregue os relatórios completos da"
      " imobiliária."
  )

  df = carregar_dados()

  if not df.empty:
    total_geral_sds = df["lucro_SDS"].sum()
    total_geral_recebido = df[df["pagamento"] == "Recebido"][
        "lucro_SDS"
    ].sum()
    total_geral_pendente = df[df["pagamento"] == "Pendente"][
        "lucro_SDS"
    ].sum()

    col1, col2, col3 = st.columns([1, 1, 1])
    col1.metric("Lucro SDS Total Registado", f"R$ {total_geral_sds:,.2f}")
    col2.metric("Lucro SDS Recebido", f"R$ {total_geral_recebido:,.2f}")
    col3.metric("Lucro SDS Pendente", f"R$ {total_geral_pendente:,.2f}")

    st.markdown("---")

    st.subheader("🔍 Filtrar Dados para Relatório")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
      status_filtro = st.selectbox(
          "Status Demanda",
          ["Todos", "Pendente", "Em Andamento", "Concluída", "Atrasada"],
      )
    with col_f2:
      pag_filtro = st.selectbox(
          "Status Pagamento", ["Todos", "Recebido", "Pendente"]
      )
    with col_f3:
      tipo_filtro = st.selectbox(
          "Tipo de Imóvel",
          ["Todos", "Caixa", "Tenda", "Novo", "Usado", "Outros"],
      )
    with col_f4:
      parc_filtro = st.selectbox("Apenas Parcerias?", ["Todos", "Sim", "Não"])

    df_filtrado = df.copy()
    if status_filtro != "Todos":
      df_filtrado = df_filtrado[df_filtrado["status"] == status_filtro]
    if pag_filtro != "Todos":
      df_filtrado = df_filtrado[df_filtrado["pagamento"] == pag_filtro]
    if tipo_filtro != "Todos":
      df_filtrado = df_filtrado[df_filtrado["tipo_imovel"] == tipo_filtro]
    if parc_filtro != "Todos":
      df_filtrado = df_filtrado[df_filtrado["parceria"] == parc_filtro]

    st.subheader("📋 Pré-visualização do Relatório Filtrado")
    cols_rel = [
        "id",
        "adquirente",
        "numero_imovel",
        "responsavel",
        "tipo_imovel",
        "parceiro_nome",
        "valor",
        "taxa_desc",
        "valor_liquido",
        "pct_sds",
        "lucro_SDS",
        "Lucro_Parceiro (R$)",
        "status",
        "pagamento",
    ]
    st.dataframe(df_filtrado[cols_rel], use_container_width=True)

    st.markdown("---")

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      df_filtrado.to_excel(
          writer, index=False, sheet_name="Relatorio_SDS_Imoveis"
      )
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Baixar Relatório Filtrado em Excel",
        data=excel_data,
        file_name="relatorio_detalhado_sds.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
  else:
    st.info("Não há dados disponíveis para gerar relatórios.")

# ---------------------------------------------------------
# 8. GERENCIAR USUÁRIOS (EXCLUSIVO CEO / ADM)
# ---------------------------------------------------------
elif menu == "👥 Gerenciar Usuários":
  st.title("👥 Gerenciamento de Usuários e Acessos")
  st.write("Altere dados, senhas e permissões dos colaboradores da imobiliária.")

  conn = sqlite3.connect("sds_imoveis.db")
  df_users = pd.read_sql("SELECT id, usuario, cargo FROM utilizadores", conn)
  conn.close()

  st.subheader("📋 Lista de Usuários Cadastrados")
  st.dataframe(df_users, use_container_width=True)

  st.markdown("---")
  st.subheader("⚙️ Alterar Dados, Cargo ou Senha de um Usuário")

  col_u1, col_u2 = st.columns(2)
  with col_u1:
    user_sel = st.selectbox(
        "Selecione o Usuário para Alterar", df_users["usuario"].tolist()
    )

  user_info = df_users[df_users["usuario"] == user_sel].iloc[0]

  with col_u2:
    novo_cargo_user = st.selectbox(
        "Cargo do Usuário",
        ["CEO / Administração", "Corretor", "Funcionário"],
        index=["CEO / Administração", "Corretor", "Funcionário"].index(
            user_info["cargo"]
        ),
    )

  nova_senha_user = st.text_input(
      "Nova Senha (deixe em branco se não quiser alterar)", type="password"
  )

  col_b1, col_b2 = st.columns(2)
  with col_b1:
    if st.button("Salvar Alterações"):
      conn = sqlite3.connect("sds_imoveis.db")
      cursor = conn.cursor()
      if nova_senha_user.strip():
        cursor.execute(
            "UPDATE utilizadores SET cargo = ?, senha = ? WHERE usuario = ?",
            (novo_cargo_user, nova_senha_user, user_sel),
        )
      else:
        cursor.execute(
            "UPDATE utilizadores SET cargo = ? WHERE usuario = ?",
            (novo_cargo_user, user_sel),
        )
      conn.commit()
      conn.close()
      st.success(f"Dados do usuário '{user_sel}' atualizados com sucesso!")
      st.rerun()

  with col_b2:
    if st.button("⚠️ Excluir Usuário"):
      if user_sel == st.session_state["usuario"]:
        st.error("Você não pode excluir o seu próprio usuário logado.")
      else:
        conn = sqlite3.connect("sds_imoveis.db")
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM utilizadores WHERE usuario = ?", (user_sel,)
        )
        conn.commit()
        conn.close()
        st.success(f"Usuário '{user_sel}' removido com sucesso!")
        st.rerun()

# ---------------------------------------------------------
# 9. CALCULADORA COMPLETA DEDICADA
# ---------------------------------------------------------
elif menu == "🧮 Calculadora":
  st.title("🧮 Calculadora Financeira e Contábil SDS")
  st.write("Realize cálculos rápidos de comissão, impostos e divisão de valores.")

  col_ca1, col_ca2 = st.columns(2)

  with col_ca1:
    st.subheader("1. Cálculo de Desconto / Taxa Imposto")
    v_bruto = st.number_input("Valor Bruto (R$)", min_value=0.0, value=1500.0)
    tx_pct = st.number_input(
        "Taxa (%)", min_value=0.0, max_value=100.0, value=14.45
    )

    v_desconto = v_bruto * (tx_pct / 100.0)
    v_liq = v_bruto - v_desconto

    st.write(f"**Valor do Desconto:** R$ {v_desconto:,.2f}")
    st.success(f"**Valor Líquido:** R$ {v_liq:,.2f}")

  with col_ca2:
    st.subheader("2. Divisão de Parceria")
    pct_sds_calc = st.slider("% SDS Imóveis", 0.0, 100.0, 50.0, step=5.0)

    val_sds = v_liq * (pct_sds_calc / 100.0)
    val_parc = v_liq - val_sds

    st.info(f"**Parte Líquida SDS:** R$ {val_sds:,.2f}")
    st.warning(f"**Parte Líquida Parceiro:** R$ {val_parc:,.2f}")