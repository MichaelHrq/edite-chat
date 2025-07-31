import psycopg2
import os
import io
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do seu arquivo .env
load_dotenv()

# --- PREENCHA O NOME DO SEU ARQUIVO CSV AQUI ---
NOME_DO_ARQUIVO_CSV = './csv/supabase-produtos-vetoriais.csv'
# ---------------------------------------------

conn = None  # Inicializa a variável de conexão
try:
    # Conecta ao banco de dados do Supabase
    conn = psycopg2.connect(
        dbname=os.getenv('SB_DBNAME'),
        user=os.getenv('SB_USER'),
        password=os.getenv('SB_PASSWORD'),
        host=os.getenv('SB_HOST'),
        port=os.getenv('SB_PORT')
    )
    cursor = conn.cursor()

    # --- PASSO 1: LIMPAR A TABELA ---
    # Usamos TRUNCATE porque é muito mais rápido que "DELETE FROM".
    # "RESTART IDENTITY" reiniciaria sequências (não se aplica aqui, mas é uma boa prática).
    print("Limpando a tabela 'produtos_vetoriais'...")
    cursor.execute("TRUNCATE TABLE produtos_vetoriais RESTART IDENTITY;")
    print("Tabela limpa com sucesso.")

    # --- PASSO 2: PREENCHER A TABELA COM O CSV ---
    print(f"Iniciando o carregamento de dados do arquivo '{NOME_DO_ARQUIVO_CSV}'...")
    
    with open(NOME_DO_ARQUIVO_CSV, 'r', encoding='utf-8') as f:
        # Pula o cabeçalho do CSV. Se o seu CSV NÃO tiver cabeçalho, comente a linha abaixo.
        next(f) 
        
        # Usamos copy_expert (ou copy_from) para um carregamento em massa eficiente.
        # Isso envia o arquivo inteiro para o Postgres de uma vez.
        cursor.copy_expert(
            sql="""
                COPY produtos_vetoriais (id, titulo, descricao, url, embedding)
                FROM STDIN WITH (FORMAT CSV, DELIMITER ',')
            """,
            file=f
        )

    # --- PASSO 3: CONFIRMAR A TRANSAÇÃO ---
    # Se tudo correu bem, o commit torna as alterações permanentes.
    conn.commit()
    print("Dados carregados e salvos no banco de dados com sucesso!")

    # Opcional: Contar as linhas para verificar
    cursor.execute("SELECT COUNT(*) FROM produtos_vetoriais;")
    count = cursor.fetchone()[0]
    print(f"Verificação: A tabela 'produtos_vetoriais' agora contém {count} linhas.")


except (Exception, psycopg2.Error) as error:
    print(f"Erro ao conectar ou manipular o banco de dados: {error}")
    # Se ocorreu um erro, o rollback desfaz qualquer alteração parcial.
    if conn:
        conn.rollback()
        print("Transação revertida (rollback).")

finally:
    # Garante que a conexão com o banco de dados seja sempre fechada.
    if conn:
        cursor.close()
        conn.close()
        print("Conexão com o banco de dados fechada.")