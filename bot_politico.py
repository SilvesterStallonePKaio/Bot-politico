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

BRIEFING_BRASIL_2026 = """
=== QUEM E QUEM NA POLITICA BRASILEIRA — MARCO 2026 ===

GOVERNO LULA (PT):
- Lula (Luiz Inacio Lula da Silva): Presidente da Republica, PT, quer reeleicao 2026. 57% dos brasileiros acha que nao devia se candidatar.
- Fernando Haddad: Ministro da Fazenda. Economista, ex-prefeito SP, perdeu para Bolsonaro em 2022.
- Gleisi Hoffmann: Presidente nacional do PT. Linha dura, defensora ferrenha de Lula.
- Rui Costa: Ministro da Casa Civil. Homem de confianca de Lula, ex-governador da Bahia.
- Alexandre Padilha: Ministro das Relacoes Institucionais. Articulador politico do governo no Congresso.
- Ricardo Lewandowski: Ministro da Justica. Ex-ministro do STF.
- Jorge Messias: Advogado-Geral da Uniao (AGU).
- Gabriel Galipolo: Presidente do Banco Central. Indicado por Lula, assumiu em 2024.
- Flavio Dino: Ministro do STF. Ex-ministro da Justica de Lula, indicado por ele ao Supremo.

OPOSICAO:
- Jair Bolsonaro: Ex-presidente, PL. Inelegivel ate 2030 por tentativa de golpe em 8 de janeiro. Preso preventivamente em 2025.
- Tarcisio de Freitas: Governador de Sao Paulo, Republicanos. Principal nome da oposicao para 2026. Ex-ministro de Bolsonaro.
- Flavio Bolsonaro: Senador, PL. Filho de Bolsonaro. Candidato escolhido pelo pai para 2026.
- Eduardo Bolsonaro: Deputado Federal, PL. Filho de Bolsonaro. Passou longa temporada nos EUA articulando com Trump.
- Michelle Bolsonaro: Esposa de Bolsonaro. Aparece em pesquisas como candidata potencial.
- Nikolas Ferreira: Deputado Federal, PL. Fenomeno nas redes sociais, lider de engajamento no Congresso.
- Ronaldo Caiado: Governador de Goias, PSD. Pre-candidato a presidente 2026.
- Ratinho Jr: Governador do Parana, PSD. Pre-candidato a presidente 2026.
- Romeu Zema: Governador de Minas Gerais, Novo. Pre-candidato a presidente 2026.

CENTRAO E CONGRESSO:
- Hugo Motta: Presidente da Camara dos Deputados, Republicanos. Aliado do governo.
- Davi Alcolumbre: Presidente do Senado Federal, Uniao Brasil. Esta bloqueando a CPI do Master no Senado.
- Arthur Lira: Ex-presidente da Camara, PP. Articulador do centrao, cobrava "taxas" para pautar projetos.
- Alessandro Vieira: Senador, MDB. Um dos condutores da CPI do Master.

STF (SUPREMO TRIBUNAL FEDERAL) — NO CENTRO DO ESCANDALO MASTER:
- Alexandre de Moraes: Ministro do STF. Esposa (Ana Moraes) tem contrato de R$129 milhoes com o Banco Master. Trocava mensagens diretas com Daniel Vorcaro (dono do Master). Investigado por suspeicao.
- Dias Toffoli: Ministro do STF. Era relator do processo do Banco Master no Supremo. Familia vendeu resort em Angra dos Reis a fundo ligado ao Master por R$6,6 milhoes. Afastado da relatoria por suspeicao. Historico de decisoes polemicas beneficiando investigados.
- Edson Fachin: Presidente do STF. Considerado linha dura na defesa da democracia.
- Luis Roberto Barroso: Vice-presidente do STF. Ex-advogado, indicado por Dilma.

ESCANDALO BANCO MASTER — O MAIOR DO MOMENTO:
- Daniel Vorcaro: Empresario, dono do Banco Master. NAO E POLITICO. Banqueiro que construiu esquema financeiro fraudulento. Preso na 3a fase da Operacao Compliance Zero em marco 2026.
- Banco Master: Banco privado que comprou ativos podres (principalmente precatorios — dividas do governo de baixo valor real), inflou o balanco e vendeu CDBs para investidores como se fossem seguros. Rombo estimado em R$50 bilhoes. Liquidado pelo Banco Central.
- BRB (Banco de Brasilia): Banco publico do DF que cogitou comprar o Master, o que socializaria o prejuizo com dinheiro publico.
- FGC (Fundo Garantidor de Creditos): Fundo que garante depositos bancarios ate R$250 mil. Seria acionado para cobrir parte do rombo do Master.
- Operacao Compliance Zero: Operacao da Policia Federal investigando o esquema do Master. Teve 3 fases. Na 3a fase (marco 2026), Vorcaro foi preso.
- Luiz Phillipi: Executor de ameacas a jornalistas contratado por aliados de Vorcaro. Morreu na cela da PF em 6 de marco de 2026 em circunstancias suspeitas.
- CPI do Master: Comissao Parlamentar de Inquerito no Senado para investigar o escandalo, conexoes com STF (Moraes e Toffoli) e possivel uso de dinheiro publico. Ja tem 35 assinaturas. Bloqueada por Alcolumbre.

IMPRENSA INVESTIGATIVA — PERSONAGENS IMPORTANTES:
- Malu Gaspar: Jornalista do O Globo e GloboNews. Principal repórter investigando o caso Master. Vorcaro planejou contratar um "sicario" para intimida-la.
- Lauro Jardim: Colunista do O Globo. Vorcaro planejou simular assalto para "quebrar todos os dentes" dele.
- Monica Bergamo: Colunista da Folha de S.Paulo. Cobre bastidores politicos, bem relacionada com o PT.
- Daniel Rittner: Diretor de jornalismo da CNN Brasil em Brasilia.
- Julie Milk (Juliana Moreira Leite): Jornalista e influenciadora. Tambem ameacada por aliados de Vorcaro.

VEICULOS DE REFERENCIA:
- O Globo, GloboNews: Lideraram investigacoes do Master.
- Folha de S.Paulo, Estadao: Cobertura politica tradicional.
- CNN Brasil: Jornalismo ao vivo e politico.
- Metropoles: Portal digital agressivo em furos politicos.
- Poder360: Especializado em politica.
- Revista Oeste: Linha editorial de direita, critica ao STF.
- Agencia Publica: Jornalismo investigativo independente.

CONTEXTO ELEITORAL 2026:
- Eleicoes presidenciais em outubro 2026.
- Lula vs Tarcisio e o cenario mais provavel segundo pesquisas.
- Bolsonaro preso e inelegivel mas ainda influencia fortemente a base.
- Escandalo Master pode afetar tanto o governo (Moraes indicado por Lula) quanto a oposicao.
"""

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
1. Fato seco + ironia: "Toffoli era relator do caso Master. A familia vendeu um resort a fundo ligado ao Master por R$6,6mi. Foi afastado. Que surpresa."
2. Analogia simples: "E como um juiz que vai julgar o acusado e ainda fez negocio com ele. So que com R$50 bilhoes do seu dinheiro na jogada."
3. Pergunta retorica: "A esposa de Moraes tem contrato de R$129mi com o Master. Ele julgaria o caso sem problemas. Por que nao, ne?"
4. Comparacao ironica: "Em 2022 prometeram transparencia. Em 2026 o relator do caso Master vendeu resort pro acusado. Promessa cumprida."

TOM NUNCA:
- Sem militancia partidaria excessiva
- Sem fake news — so fatos verificaveis do briefing ou das noticias recebidas
- Sem xingamentos diretos
- Sem maiusculas gritadas
- Sem exclamacoes em excesso
- NUNCA confunda empresarios com politicos (ex: Vorcaro NAO e politico)
- NUNCA invente fatos que nao estejam no briefing ou nas noticias
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
    """Busca noticias politicas recentes via Google News RSS.
    Retorna (texto_contexto, link_noticia, nome_veiculo) ou (None, None, None)
    """
    fonte_usada = random.choice(FONTES_RSS)
    try:
        resp = requests.get(fonte_usada, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None, None, None
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:6]
        
        noticias_texto = []
        melhor_link = None
        melhor_veiculo = None
        
        for item in items:
            titulo_raw = item.findtext("title", "")
            # Formato Google News: "Titulo - Veiculo"
            partes = titulo_raw.rsplit(" - ", 1)
            titulo = partes[0].strip()
            veiculo = partes[1].strip() if len(partes) > 1 else "Imprensa Nacional"
            
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "")[:16]
            descricao = extrair_texto_simples(item.findtext("description", ""))[:300]
            
            if titulo:
                entrada = f"• {titulo} ({pub_date}) [{veiculo}]"
                if descricao:
                    entrada += f"\n  {descricao}"
                noticias_texto.append(entrada)
                
                # Salva o primeiro link valido como fonte principal
                if not melhor_link and link:
                    melhor_link = link
                    melhor_veiculo = veiculo

        if noticias_texto:
            print(f"[INFO] {len(noticias_texto)} noticias encontradas. Fonte: {melhor_veiculo}")
            return "\n".join(noticias_texto[:5]), melhor_link, melhor_veiculo
    except Exception as e:
        print(f"[AVISO] Erro RSS: {e}")

    return None, None, None

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

def enviar_opcoes(posts, tipo, fonte_nome=None, tem_noticias=False):
    """Envia cada opcao de post como mensagem separada no Telegram."""
    tipo_label = {
        "escandalo_governo": "Escandalo 💥",
        "declaracao_politico": "Declaracao Politica 🎤",
        "analogia_economica": "Analogia Economica 📊",
        "ironia_promessa": "Ironia de Promessa 😏",
        "bastidores_politica": "Bastidores 🔍",
    }.get(tipo, tipo)

    fonte_info = "📡 _Noticias de hoje_" if tem_noticias else "📚 _Contexto geral_"
    total = len(posts)

    # Cabecalho
    enviar_telegram(f"🇧🇷 *@OlhaQueSurpresa* — {total} opcoes de post!\n*Tipo:* {tipo_label} | {fonte_info}")
    time.sleep(0.5)

    # Cada opcao numa mensagem separada
    for i, post in enumerate(posts, 1):
        link = f"https://twitter.com/intent/tweet?text={quote(post)}"
        msg = f"*Opcao {i}/{total}* ({len(post)} chars):\n_{post}_\n👉 [Publicar opcao {i}]({link})"
        enviar_telegram(msg)
        time.sleep(0.5)

    enviar_telegram("_Escolha uma opcao acima ou ignore._")
    print(f"[Telegram] {total} opcoes enviadas!")

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
        print(f"[INFO] Gerando post manual: {tema}")
        claude_client = init_claude()
        print("[INFO] Claude conectado, gerando opcoes...")
        posts, tipo, fonte_nome, tem_noticias = gerar_cinco_opcoes(claude_client, tema_manual=tema)
        print(f"[INFO] {len(posts)} posts gerados, enviando...")
        enviar_opcoes(posts, tipo, fonte_nome, tem_noticias)
        print("[INFO] Envio concluido!")
    except Exception as e:
        import traceback
        print(f"[ERRO MANUAL] {traceback.format_exc()}")
        try:
            enviar_telegram(f"Erro: {str(e)[:200]}")
        except:
            pass

def extrair_fonte_rss(noticias_texto):
    """Extrai nome do veiculo da primeira noticia."""
    veiculos = ["O Globo","GloboNews","Folha","Estadao","CNN Brasil","Metropoles","Poder360","UOL","G1","Agencia Brasil","Revista Oeste"]
    for v in veiculos:
        if v.lower() in noticias_texto.lower():
            return v
    return "Imprensa Nacional"

def gerar_cinco_opcoes(claude_client, tema_manual=None):
    """Gera 5 opcoes de post — variedade de tons e formatos."""
    tipo = random.choice(TIPOS_POST)
    instrucao = PROMPTS_POR_TIPO.get(tipo, PROMPTS_POR_TIPO["escandalo_governo"])
    fonte_nome = None

    link_fonte = None
    if tema_manual:
        contexto = f"TEMA MANUAL ENVIADO PELO USUARIO:\n{tema_manual}"
        tipo = "escandalo_governo"
        instrucao = "Comenta o tema acima com ironia inteligente e/ou analogia simples."
    else:
        noticias, link_fonte, fonte_nome = buscar_noticias_politicas()
        videos = buscar_videos_youtube()
        
        partes = []
        if noticias:
            partes.append(f"NOTICIAS POLITICAS RECENTES (Fonte: {fonte_nome}):\n{noticias}")
        if videos:
            partes.append(f"VIDEOS RECENTES DE POLITICOS NO YOUTUBE:\n{videos}")
        
        contexto = "\n\n".join(partes) if partes else "Sem noticias recentes — use contexto geral da politica brasileira 2026."

    link_info = f"\nLINK DA NOTICIA PRINCIPAL: {link_fonte}" if link_fonte else ""

    prompt = f"""{PERSONALIDADE}

{BRIEFING_BRASIL_2026}

MISSAO: {instrucao}

MATERIAL DO DIA:
{contexto}{link_info}

IMPORTANTE:
- Use o BRIEFING para entender quem e quem — nunca confunda empresario com politico
- NUNCA invente fatos — so comente o que esta no briefing ou no material do dia
- Se nao tiver material suficiente, use fatos verificados do briefing
- Escolha angulos DIFERENTES em cada versao — nao repita o mesmo raciocinio
- NAO inclua o link nos textos — ele sera adicionado automaticamente

Gere CINCO versoes do post com tons diferentes:
VERSAO 1: Ironico e seco — fato + "que surpresa" implicito
VERSAO 2: Analogia do dia a dia — explica para qualquer pessoa entender + ironia no final
VERSAO 3: Pergunta retorica — questiona a logica do que aconteceu
VERSAO 4: Comparacao temporal — promessa vs realidade, ou antes vs depois
VERSAO 5: Didatico — explica o tema como se fosse para alguem que nao acompanhou + pitada ironica

REGRAS TECNICAS:
- Cada versao: maximo 220 caracteres (deixa espaco para o link)
- Sem palavroes
- 1 hashtag no final de cada (#BancoMaster ou #Brasil ou #Politica conforme o tema)
- Retorne EXATAMENTE neste formato sem mais nada:
VERSAO1: [texto]
VERSAO2: [texto]
VERSAO3: [texto]
VERSAO4: [texto]
VERSAO5: [texto]
"""

    msg = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    resposta = msg.content[0].text.strip()
    posts = []
    for linha in resposta.split("\n"):
        linha_upper = linha.upper().strip()
        for i in range(1, 6):
            prefixos = [f"VERSAO{i}:", f"VERSAO {i}:", f"VERSÃO{i}:", f"VERSÃO {i}:", f"OPCAO{i}:", f"OPCAO {i}:"]
            for prefixo in prefixos:
                if linha_upper.startswith(prefixo):
                    texto = linha[len(prefixo):].strip().strip('"').strip("'")
                    if len(texto) > 280:
                        texto = texto[:277] + "..."
                    if texto:
                        posts.append(texto)
                    break

    # fallback: tenta pegar linhas com numero no inicio
    if len(posts) < 2:
        posts = []
        for linha in resposta.split("\n"):
            linha = linha.strip()
            if linha and len(linha) > 20:
                for prefix in ["1.", "2.", "3.", "4.", "5.", "1)", "2)", "3)", "4)", "5)"]:
                    if linha.startswith(prefix):
                        texto = linha[len(prefix):].strip().strip('"')
                        if len(texto) > 280:
                            texto = texto[:277] + "..."
                        if texto:
                            posts.append(texto)
                        break

    if not posts:
        posts = [resposta[:265]]

    # Adiciona link da fonte em todos os posts se disponivel
    if link_fonte:
        posts_com_link = []
        for p in posts:
            post_com_link = f"{p}\n\n🔗 {link_fonte}"
            if len(post_com_link) <= 280:
                posts_com_link.append(post_com_link)
            else:
                posts_com_link.append(p)  # sem link se ultrapassar
        posts = posts_com_link

    return posts, tipo, fonte_nome, tem_noticias

def ciclo(claude_client, dry_run=False):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando ciclo politico...")
    posts, tipo, fonte_nome, tem_noticias = gerar_cinco_opcoes(claude_client)
    
    if dry_run:
        for i, p in enumerate(posts, 1):
            print(f"\n[DRY RUN] Opcao {i}:\n{p}\n")
    else:
        enviar_opcoes(posts, tipo, fonte_nome, tem_noticias)

def configurar_webhook():
    """Configura webhook do Telegram para receber mensagens manuais."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[AVISO] Token nao encontrado")
        return

    # URL fixa do Render
    webhook_url = "https://bot-politico.onrender.com/webhook"
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        resp = requests.post(url, json={"url": webhook_url}, timeout=10)
        data = resp.json()
        if data.get("ok"):
            print(f"[OK] Webhook configurado: {webhook_url}")
        else:
            print(f"[AVISO] Webhook erro: {data}")
    except Exception as e:
        print(f"[AVISO] Webhook excecao: {e}")

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
