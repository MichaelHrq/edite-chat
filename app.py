import os
import openai
import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

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
CORS(app)  # libera CORS para todas as origens (uso geral)

def gerar_embedding(texto):
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )
    return response.data[0].embedding

def buscar_produtos(embedding, limite=5):
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

def gerar_resposta(intencao, produtos, idioma='en'):
    # Dicionário com os textos do prompt em cada idioma
    textos_prompt = {
        'pt': {
            'instrucao_sistema': "Você é um assistente virtual amigável para uma loja de cosméticos. Responda sempre em português do Brasil com um tom empático e prestativo. Sugira até 3 produtos da lista fornecida.",
            'header_produtos': "Aqui estão os produtos mais relevantes para usar na sua resposta:"
        },
        'it': {
            'instrucao_sistema': "Sei un assistente virtuale amichevole per un negozio di cosmetici. Rispondi sempre in italiano con un tono empatico e utile. Suggerisci fino a 3 prodotti dalla lista fornita.",
            'header_produtos': "Ecco i prodotti più rilevanti da usare nella tua risposta:"
        },
        'en': {
            'instrucao_sistema': "You are a friendly virtual assistant for a cosmetics store. Always answer in English with an empathetic and helpful tone. Suggest up to 3 products from the provided list.",
            'header_produtos': "Here are the most relevant products to use in your answer:"
        }
    }

    # Seleciona o texto do idioma correto, ou usa inglês ('en') como padrão
    textos = textos_prompt.get(idioma, textos_prompt['en'])

    # Formata a lista de produtos
    lista_produtos = "\n".join([
        f"- {p['titulo']}: {p['descricao']} (Link: {p['url']})"
        for p in produtos
    ])

    # Monta o prompt para o modelo
    prompt_usuario = f"""
A intenção do cliente é: "{intencao}"

{textos['header_produtos']}
{lista_produtos}
"""

    # Chama a API do OpenAI com as novas instruções
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            # Instrução geral sobre como o modelo deve se comportar
            {"role": "system", "content": textos['instrucao_sistema']},
            # A pergunta específica do usuário
            {"role": "user", "content": prompt_usuario}
        ],
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
    idioma = data.get('idioma', 'it')

    if not pergunta:
        return jsonify({"erro": "Mensagem vazia"}), 400

    try:
        embedding = gerar_embedding(pergunta)
        produtos = buscar_produtos(embedding, limite=5)
        if not produtos:
            return jsonify({"resposta": "Non ho trovato nessun prodotto adatto, mi dispiace!"})
        resposta = gerar_resposta(pergunta, produtos, idioma=idioma)
        return jsonify({"resposta": resposta})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)