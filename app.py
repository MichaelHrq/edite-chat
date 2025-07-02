import os
import openai
import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

SUPABASE_CONFIG = {
    "dbname": os.getenv('SB_DBNAME'),
    "user": os.getenv('SB_USER'),
    "password": os.getenv('SB_PASSWORD'),
    "host": os.getenv('SB_HOST'),
    "port": os.getenv('SB_PORT')
}

app = Flask(__name__)

def gerar_embedding(texto):
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )
    return response.data[0].embedding

def buscar_produtos(embedding, limite=3):
    conn = psycopg2.connect(**SUPABASE_CONFIG)
    cursor = conn.cursor()

    # Converter vetor Python para texto tipo vector
    embedding_sql = str(embedding).replace('\n', '')  # Gera: "[0.1, -0.2, ...]"

    sql = f"""
    SELECT titulo, descricao, url
    FROM produtos_vetoriais
    ORDER BY embedding <-> '{embedding_sql}'::vector
    LIMIT %s;
    """

    cursor.execute(sql, (limite,))
    resultados = cursor.fetchall()

    cursor.close()
    conn.close()

    produtos = []
    for r in resultados:
        produtos.append({
            "titulo": r[0],
            "descricao": r[1],
            "url": r[2]
        })
    return produtos

def gerar_resposta(intencao, produtos):
    lista = "\n".join([
        f"{i+1}. {p['titulo']} – {p['descricao']} [Link: {p['url']}]"
        for i, p in enumerate(produtos)
    ])

    prompt = f"""
Sei un assistente virtual per un negozio di cosmetici. Un cliente ha detto:

\"{intencao}\"

Suggerisci fino a 3 prodotti adatti in modo amichevole e utile. Ecco i più rilevanti:

{lista}

Rispondi sempre in italiano, con tono empatico.
"""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )
    return response.choices[0].message.content.strip()
        
@app.route("/", methods=["GET"])
def home():
    return "✅ API online"
        
@app.route("/chat-sugestoes", methods=["POST"])
def chat_sugestoes():
    data = request.get_json()
    pergunta = data.get("mensagem", "").strip()

    if not pergunta:
        return jsonify({"erro": "Mensagem vazia"}), 400

    try:
        embedding = gerar_embedding(pergunta)
        produtos = buscar_produtos(embedding, limite=3)
        if not produtos:
            return jsonify({"resposta": "Non ho trovato nessun prodotto adatto, mi dispiace!"})
        resposta = gerar_resposta(pergunta, produtos)
        return jsonify({"resposta": resposta})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)