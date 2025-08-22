import os
import openai
import json
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from tqdm import tqdm


openai.api_key = os.getenv('OPENAI_API_KEY')

load_dotenv()
conn = psycopg2.connect(
    dbname=os.getenv('SB_DBNAME'),
    user=os.getenv('SB_USER'),
    password=os.getenv('SB_PASSWORD'),
    host=os.getenv('SB_HOST'),
    port=os.getenv('SB_PORT')
)

cursor = conn.cursor()

print("Limpando a tabela 'produtos_vetoriais'...")
cursor.execute("TRUNCATE TABLE produtos_vetoriais RESTART IDENTITY;")
print("Tabela limpa com sucesso.")

with open('produtos.json', 'r', encoding='utf-8') as f:
    produtos = json.load(f)
    valores = []
    for p in tqdm(produtos):
        try:
            # Preparar texto para embedding
            texto = f"{p['titulo']} - {p['descricao'] or p.get('resumo', '')}".strip(
            )
            if not texto:
                continue

            # Gerar embedding com OpenAI
            embedding = openai.embeddings.create(
                model="text-embedding-3-small",
                input=texto
            ).data[0].embedding

            # Usar ID como string (TEXT)
            valores.append((
                p['id'],
                p['titulo'],
                p['descricao'],
                p['url'],
                embedding
            ))
        except Exception as e:
            print(f"Erro ao processar produto ID {p['id']}: {e}")
            continue

        if valores:
            try:
                sql = """
              INSERT INTO produtos_vetoriais (id, titulo, descricao, url, embedding)
              VALUES %s
              ON CONFLICT (id) DO UPDATE SET
                titulo = EXCLUDED.titulo,
                descricao = EXCLUDED.descricao,
                url = EXCLUDED.url,
                embedding = EXCLUDED.embedding
              """
                execute_values(cursor, sql, valores)
                conn.commit()
                print(f"✅ {len(valores)} produtos inseridos com sucesso.")
            except Exception as e:
                print("Erro ao inserir no banco:", e)
        else:
            print("⚠️ Nenhum produto válido para inserir.")

cursor.close()
conn.close()
