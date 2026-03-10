"""
Bot @OlhaQueSurpresa — Posts politicos para o X
================================================
Fluxo:
  - Automatico: busca noticias + YouTube a cada ciclo
  - Manual: voce manda tema pelo Telegram
  - Gera 2 opcoes de post por ciclo para voce escolher

Variaveis de ambiente:
    ANTHROPIC_API_KEY=sk-ant-...
    TELEGRAM_BOT_TOKEN=...
    TELEGRAM_CHAT_ID=...
    YOUTUBE_API_KEY=...
    PORT=8081
"""

import anthropic
import schedule
import requests
import random
import argparse
import threading
import time
import os
import sys
import json
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from urllib.parse import quote
from flask import Flask, request as flask_request

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

HORARIOS_POSTS = ["08:00", "12:00", "18:00", "21:00"]

# Canais YouTube de politicos brasileiros proeminentes
CANAIS_YOUTUBE = {
    "Lula": "UCnGtLgHkbOtCkBuIMmFmjsg",
    "PT": "UCnGtLgHkbOtCkBuIMmFmjsg",
    "Bolsonaro": "UC8vZnvAVFl1bAoYLOHFMgaQ",
    "Tarcisio": "UCGkBwBGkBwBGkBwBGkBwBGkB",
    "Flavio Bolsonaro": "UCFlaBolsonaroOficial123",
    "Gleisi Hoffmann": "UCGleisiOficial123456789",
}

# Fontes RSS politicas
FONTES_RSS = [
    "https://news.google.com/rss/search?q=política+Brasil+escândalo&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Lula+governo+federal+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Banco+Master+OR+escândalo+OR+corrupção+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Tarcisio+Bolsonaro+oposição+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=congresso+nacional+votação+polêmica&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
]

PERSONALIDADE = """
Voce e o @OlhaQueSurpresa — perfil politico brasileiro com voz propria.

SEU ESTILO:
- Ironico e acido como quem diz "que surpresa, neh?" sem precisar escrever isso
- Didatico quando o assunto e complexo — explica com analogias do dia a dia
- Jocoso e inteligente — humor que vem da observacao, nao da grosseria
- Critico do governo atual (PT/Lula) como foco principal
- Nao poupa oposicao quando faz besteira — credibilidade vem da imparcialidade na critica
- Fala como pessoa real, nao como militante nem como assessoria

FORMATOS QUE VOCE USA:
1. Fato seco + ironia: "Banco Master vendeu ativos podres como se valessem ouro. Que surpresa."
2. Analogia simples: "E como comprar um carro batido por R$500, dizer que vale R$50mil e pedir financiamento. So que com o seu dinheiro como garantia."
3. Pergunta retorica: "O ministro disse que nao sabia de nada. De novo. Impressionante como esses caras dormem bem."
4. Comparacao ironica: "Em 2022 prometeram acabar com a fome. Em 2025 o ministro da fazenda tem fome de emendas."

TOM NUNCA:
- Sem militancia partidaria excessiva
- Sem fake news — so fatos verificaveis
- Sem xingamentos diretos
- Sem mayusculas gritadas
- Sem exclamacoes em excesso
"""

TIPOS_POST = [
    "escandalo_governo",
    "declaracao_politico", 
    "analogia_economica",
    "ironia_promessa",
    "bastidores_politica",
]

PROMPTS_POR_TIPO = {
    "escandalo_governo": "Comenta um escandalo ou falha do governo atual. Tom: ironico seco. Como alguem que ja esperava.",
    "declaracao_politico": "Reage a uma declaracao ou acao de politico. Tom: retorico, questiona a logica.",
    "analogia_economica": "Explica um tema economico/financeiro complexo com analogia simples do dia a dia. Tom: didatico + ironia no final.",
    "ironia_promessa": "Compara promessa feita com realidade atual. Tom: ironia fina, sem precisar explicar demais.",
    "bastidores_politica": "Comenta bastidores, articulacoes, jogadas politicas. Tom: sagaz, como quem entende o jogo.",
}

app = Flask(__name__)

# Tema manual enviado pelo Telegram
tema_manual_global = {"tema": None, "timestamp": 0}

def extrair_texto_simples(html):
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()[:500]

def buscar_noticias_politicas():
    """Busca noticias politicas recentes via Google News RSS."""
    noticias = []
    fonte_usada = random.choice(FONTES_RSS)
    try:
        resp = requests.get(fonte_usada, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:6]:
            titulo = item.findtext("title", "").split(" - ")[0].strip()
            pub_date = item.findtext("pubDate", "")[:16]
            descricao = extrair_texto_simples(item.findtext("description", ""))[:300]
            if titulo:
                entrada = f"• {titulo} ({pub_date})"
                if descricao:
                    entrada += f"\n  {descricao}"
                noticias.append(entrada)
    except Exception as e:
        print(f"[AVISO] Erro RSS: {e}")

    if noticias:
        print(f"[INFO] {len(noticias)} noticias politicas encontradas")
        return "\n".join(noticias[:5])
    return None

def buscar_videos_youtube():
    """Busca videos recentes de politicos brasileiros no YouTube."""
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return None
    
    termos = [
        "Lula discurso hoje",
        "Tarcisio Freitas declaracao",
        "Bolsonaro declaracao recente",
        "governo federal anuncio",
        "congresso nacional votacao",
    ]
    termo = random.choice(termos)
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": termo,
            "type": "video",
            "order": "date",
            "maxResults": 3,
            "regionCode": "BR",
            "relevanceLanguage": "pt",
            "key": api_key,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"[AVISO] YouTube API erro: {resp.status_code}")
            return None
        
        data = resp.json()
        videos = []
        for item in data.get("items", []):
            titulo = item["snippet"]["title"]
            canal = item["snippet"]["channelTitle"]
            data_pub = item["snippet"]["publishedAt"][:10]
            descricao = item["snippet"]["description"][:200]
            videos.append(f"• [{canal}] {titulo} ({data_pub})\n  {descricao}")
        
        if videos:
            print(f"[INFO] {len(videos)} videos do YouTube encontrados")
            return "\n".join(videos)
    except Exception as e:
        print(f"[AVISO] Erro YouTube: {e}")
    return None

def init_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY nao encontrada")
    return anthropic.Anthropic(api_key=api_key)

def check_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID nao encontrados")

def enviar_telegram(mensagem):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        raise Exception(f"Telegram erro: {resp.status_code}")

def enviar_opcoes(post1, post2, tipo, tem_noticias=False):
    """Envia 2 opcoes de post para o usuario escolher."""
    tipo_label = {
        "escandalo_governo": "Escandalo 💥",
        "declaracao_politico": "Declaracao Politica 🎤",
        "analogia_economica": "Analogia Economica 📊",
        "ironia_promessa": "Ironia de Promessa 😏",
        "bastidores_politica": "Bastidores 🔍",
    }.get(tipo, tipo)

    link1 = f"https://twitter.com/intent/tweet?text={quote(post1)}"
    link2 = f"https://twitter.com/intent/tweet?text={quote(post2)}"
    fonte = "📡 _Baseado em noticias de hoje_" if tem_noticias else "📚 _Contexto geral_"

    msg = (
        f"🇧🇷 *@OlhaQueSurpresa* — novo post!\n"
        f"*Tipo:* {tipo_label} | {fonte}\n\n"
        f"*Opcao 1* ({len(post1)} chars):\n_{post1}_\n"
        f"👉 [Publicar opcao 1]({link1})\n\n"
        f"*Opcao 2* ({len(post2)} chars):\n_{post2}_\n"
        f"👉 [Publicar opcao 2]({link2})\n\n"
        f"_Ou ignore se nenhuma servir._"
    )
    enviar_telegram(msg)
    print(f"[Telegram] 2 opcoes enviadas!")

@app.route("/health", methods=["GET"])
def health():
    return json.dumps({"status": "ok"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Recebe mensagens do Telegram para modo manual."""
    data = flask_request.get_json()
    if not data:
        return "ok", 200
    
    chat_id_config = os.environ.get("TELEGRAM_CHAT_ID", "")
    message = data.get("message", {})
    chat = message.get("chat", {})
    
    if str(chat.get("id", "")) != str(chat_id_config):
        return "ok", 200
    
    texto = message.get("text", "").strip()
    
    if texto and not texto.startswith("/"):
        tema_manual_global["tema"] = texto
        tema_manual_global["timestamp"] = time.time()
        enviar_telegram(f"✅ Tema recebido! Gerando post sobre:\n_{texto}_\n\nAguarde...")
        
        # Gera post imediatamente com o tema manual
        threading.Thread(
            target=gerar_e_enviar_manual,
            args=(texto,),
            daemon=True
        ).start()
    
    return "ok", 200

def gerar_e_enviar_manual(tema):
    """Gera post baseado em tema manual enviado pelo usuario."""
    try:
        claude_client = init_claude()
        post1, post2, tipo = gerar_duas_opcoes(claude_client, tema_manual=tema)
        enviar_opcoes(post1, post2, tipo, tem_noticias=True)
    except Exception as e:
        enviar_telegram(f"❌ Erro ao gerar post: {e}")

def gerar_duas_opcoes(claude_client, tema_manual=None):
    """Gera duas opcoes de post — uma mais ironica, uma mais didatica."""
    tipo = random.choice(TIPOS_POST)
    instrucao = PROMPTS_POR_TIPO.get(tipo, PROMPTS_POR_TIPO["escandalo_governo"])

    if tema_manual:
        contexto = f"TEMA MANUAL ENVIADO PELO USUARIO:\n{tema_manual}"
        tipo = "escandalo_governo"
        instrucao = "Comenta o tema acima com ironia inteligente e/ou analogia simples."
    else:
        noticias = buscar_noticias_politicas()
        videos = buscar_videos_youtube()
        
        partes = []
        if noticias:
            partes.append(f"NOTICIAS POLITICAS RECENTES:\n{noticias}")
        if videos:
            partes.append(f"VIDEOS RECENTES DE POLITICOS NO YOUTUBE:\n{videos}")
        
        contexto = "\n\n".join(partes) if partes else "Sem noticias recentes — use contexto geral da politica brasileira 2026."

    prompt = f"""{PERSONALIDADE}

MISSAO: {instrucao}

MATERIAL:
{contexto}

IMPORTANTE:
- NUNCA invente fatos — so comente o que esta explicitamente no material acima
- Se nao tiver material suficiente, use ironia sobre o comportamento geral dos politicos
- Escolha o angulo mais INESPERADO e INTELIGENTE, nao o obvio

Gere DUAS versoes do post:
VERSAO 1: Tom ironico e seco (estilo "que surpresa")
VERSAO 2: Tom didatico com analogia simples do dia a dia + ironia no final

REGRAS TECNICAS:
- Cada versao: maximo 270 caracteres
- Sem palavroes
- 1 a 2 hashtags no final de cada (#Brasil #Politica #OlhaQueSurpresa)
- Retorne EXATAMENTE neste formato:
VERSAO1: [texto do post 1]
VERSAO2: [texto do post 2]
"""

    msg = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    
    resposta = msg.content[0].text.strip()
    
    # Extrai as duas versoes
    post1 = post2 = ""
    for linha in resposta.split("\n"):
        if linha.startswith("VERSAO1:"):
            post1 = linha.replace("VERSAO1:", "").strip().strip('"')
        elif linha.startswith("VERSAO2:"):
            post2 = linha.replace("VERSAO2:", "").strip().strip('"')
    
    if not post1:
        post1 = resposta[:270]
    if not post2:
        post2 = post1
    
    if len(post1) > 280:
        post1 = post1[:277] + "..."
    if len(post2) > 280:
        post2 = post2[:277] + "..."
    
    tem_noticias = not tema_manual and bool(contexto)
    return post1, post2, tipo

def ciclo(claude_client, dry_run=False):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando ciclo politico...")
    post1, post2, tipo = gerar_duas_opcoes(claude_client)
    
    if dry_run:
        print(f"\n[DRY RUN] Opcao 1:\n{post1}\n")
        print(f"[DRY RUN] Opcao 2:\n{post2}\n")
    else:
        enviar_opcoes(post1, post2, tipo, tem_noticias=True)

def configurar_webhook():
    """Configura webhook do Telegram para receber mensagens manuais."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if not railway_url or not token:
        print("[AVISO] Webhook nao configurado — modo manual indisponivel")
        return
    webhook_url = f"https://{railway_url}/webhook"
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    resp = requests.post(url, json={"url": webhook_url}, timeout=10)
    if resp.status_code == 200:
        print(f"[OK] Webhook configurado: {webhook_url}")
    else:
        print(f"[AVISO] Erro ao configurar webhook: {resp.text}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print(" BOT @OlhaQueSurpresa - Politica BR")
    print(f" Modo: {'DRY RUN' if args.dry_run else 'PRODUCAO'}")
    print(f" Horarios: {', '.join(HORARIOS_POSTS)}")
    print("=" * 60)

    for var in ["ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YOUTUBE_API_KEY"]:
        valor = os.environ.get(var)
        print(f"[{'OK' if valor else 'AUSENTE'}] {var}")

    try:
        claude_client = init_claude()
        print("[OK] Claude conectado")
    except ValueError as e:
        print(f"[ERRO] {e}"); sys.exit(1)

    if not args.dry_run:
        try:
            check_telegram()
            print("[OK] Telegram configurado")
        except ValueError as e:
            print(f"[ERRO] {e}"); sys.exit(1)

    if args.once:
        ciclo(claude_client, dry_run=args.dry_run)
        return

    port = int(os.environ.get("PORT", 8081))
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    print(f"[OK] Health check + webhook na porta {port}")

    configurar_webhook()

    for horario in HORARIOS_POSTS:
        schedule.every().day.at(horario).do(ciclo, claude_client, dry_run=args.dry_run)

    print("[INFO] Bot politico rodando. Aguardando horarios...\n")
    print("[INFO] Para post manual: mande mensagem pro bot no Telegram!\n")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
