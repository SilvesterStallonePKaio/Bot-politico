"""
Bot @OlhaQueSurpresa — Posts politicos para o X
Render + Telegram + Groq + Google News RSS + YouTube
"""

import schedule, requests, random, argparse
import threading, time, os, sys, json
import xml.etree.ElementTree as ET
import re, traceback
from datetime import datetime
from urllib.parse import quote
from flask import Flask, request as flask_request

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ─── CONFIG ──────────────────────────────────────────────
HORARIOS_POSTS = ["11:00", "15:00", "21:00", "00:00"]  # UTC = 08h, 12h, 18h, 21h Brasilia
RENDER_URL = "https://bot-politico.onrender.com"

# Fontes RSS — priorizadas por relevancia e atualidade
FONTES_BREAKING = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYVdjU0FtcHZHZ0pTVWlnQVAB?hl=pt-BR&gl=BR&ceid=BR:pt-419",
    "https://news.google.com/rss/search?q=Brasil+urgente+hoje&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=breaking+news+Brasil+politica&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
]

# RSS diretos — retornam links reais das materias (preview funciona no Telegram)
FONTES_RSS_DIRETO = [
    "https://www.metropoles.com/feed",
    "https://poder360.com.br/feed/",
    "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml",
    "https://agenciabrasil.ebc.com.br/rss/geral/feed.xml",
    "https://www.correiobraziliense.com.br/rss/politica.xml",
]

FONTES_POLITICA = [
    "https://news.google.com/rss/search?q=Banco+Master+STF+Vorcaro&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Moraes+Toffoli+STF+escandalo&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Lula+governo+corrupcao+escandalo&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Tarcisio+Bolsonaro+oposicao&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=congresso+nacional+polemica+votacao&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=politica+Brasil+escandalo+hoje&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=CPI+Master+senado+Alcolumbre&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=corrupcao+ministerio+Brasil+2026&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
]

VEICULOS_CONFIAVEIS = [
    "o globo", "folha", "estadao", "cnn brasil", "metropoles", 
    "poder360", "uol", "g1", "agencia brasil", "veja", "carta capital",
    "the intercept", "agencia publica", "piauí", "revista oeste", "band"
]

BRIEFING = """
=== QUEM E QUEM NA POLITICA BRASILEIRA — MARCO 2026 ===

GOVERNO LULA (PT):
- Lula: Presidente, PT, quer reeleicao 2026. 57% acha que nao devia se candidatar.
- Fernando Haddad: Ministro da Fazenda.
- Gleisi Hoffmann: Presidente do PT.
- Rui Costa: Casa Civil.
- Alexandre Padilha: Relacoes Institucionais.
- Ricardo Lewandowski: Ministro da Justica.
- Gabriel Galipolo: Presidente do Banco Central, indicado por Lula.
- Flavio Dino: Ministro do STF, indicado por Lula.

OPOSICAO:
- Bolsonaro: Ex-presidente, inelegivel ate 2030, preso por tentativa de golpe.
- Tarcisio de Freitas: Governador SP, principal candidato da oposicao 2026.
- Flavio Bolsonaro: Senador PL, filho de Bolsonaro, candidato escolhido pelo pai.
- Eduardo Bolsonaro: Deputado Federal PL, filho de Bolsonaro.
- Michelle Bolsonaro: Esposa de Bolsonaro, aparece em pesquisas.
- Nikolas Ferreira: Deputado Federal PL, fenomeno nas redes.
- Ronaldo Caiado: Governador GO, pre-candidato.
- Ratinho Jr: Governador PR, pre-candidato.

CENTRAO E CONGRESSO:
- Hugo Motta: Presidente da Camara, Republicanos.
- Davi Alcolumbre: Presidente do Senado, bloqueando CPI do Master.
- Arthur Lira: Ex-presidente da Camara, PP.
- Alessandro Vieira: Senador MDB, conduziu CPI do Master.

STF NO ESCANDALO MASTER:
- Alexandre de Moraes: Ministro STF. Esposa tem contrato de R$129mi com o Master. Trocava mensagens com Vorcaro.
- Dias Toffoli: Ministro STF. Era relator do caso Master. Familia vendeu resort por R$6,6mi a fundo ligado ao Master. Afastado.
- Edson Fachin: Presidente do STF.

ESCANDALO BANCO MASTER:
- Daniel Vorcaro: EMPRESARIO, dono do Banco Master. NAO E POLITICO. Preso na Operacao Compliance Zero.
- Banco Master: Comprou ativos podres (precatorios), vendeu CDBs como seguros. Rombo de R$50 bilhoes.
- BRB: Banco publico do DF que cogitou comprar o Master com dinheiro publico.
- Operacao Compliance Zero: PF investigando o Master. Vorcaro preso na 3a fase (marco 2026).
- Luiz Phillipi: Executor de ameacas a jornalistas. Morreu na cela da PF em 6/3/2026.
- CPI do Master: 35 assinaturas no Senado. Bloqueada por Alcolumbre.

IMPRENSA INVESTIGATIVA:
- Malu Gaspar: O Globo/GloboNews. Principal reporter investigando o Master. Vorcaro planejou intimidar.
- Lauro Jardim: Colunista O Globo. Vorcaro planejou agredir.
- Monica Bergamo: Colunista Folha de S.Paulo.
- Julie Milk: Jornalista/influenciadora, tambem ameacada.

REGRA CRITICA: Nunca confunda empresario com politico. Vorcaro NAO e politico.
"""

PERSONALIDADE = """
Voce e o @OlhaQueSurpresa — perfil politico brasileiro.

ESTILO:
- Ironico e acido — humor inteligente, nao grosseiro
- Didatico quando necessario — analogias simples do dia a dia
- Critico do governo atual como foco principal
- Nao poupa oposicao quando erra — credibilidade vem disso
- Fala como pessoa real, nao militante

NUNCA:
- Inventar fatos
- Confundir empresario com politico (Vorcaro NAO e politico)
- Usar maiusculas gritadas ou exclamacoes em excesso
- Militancia partidaria excessiva
"""

# ─── FLASK ───────────────────────────────────────────────
app = Flask(__name__)

@app.route("/health", methods=["GET", "HEAD"])
def health():
    return json.dumps({"status": "ok"}), 200

# Estado de confirmacao por chat_id
ESTADO_CONFIRMACAO = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = flask_request.get_json(silent=True) or {}
        chat_id_config = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
        message = data.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        texto = message.get("text", "").strip()

        if chat_id != chat_id_config:
            return "ok", 200

        if not texto:
            return "ok", 200

        # Cancelar
        if texto.lower() in ["/cancelar", "cancelar", "cancel", "nao", "não"]:
            ESTADO_CONFIRMACAO.pop(chat_id, None)
            enviar_telegram("❌ Cancelado.")
            return "ok", 200

        # Aguardando confirmacao
        if chat_id in ESTADO_CONFIRMACAO:
            estado = ESTADO_CONFIRMACAO.pop(chat_id)
            if texto.lower() in ["sim", "s", "ok", "yes", "1", "confirma", "confirmar"]:
                enviar_telegram("⏳ _Confirmado! Gerando 10 opcoes..._")
                threading.Thread(
                    target=gerar_e_enviar,
                    kwargs={"contexto_confirmado": estado},
                    daemon=True
                ).start()
            else:
                enviar_telegram("❌ Cancelado. Mande outro tema quando quiser.")
            return "ok", 200

        # URL do X: pede titulo manual
        if any(d in texto.lower() for d in ["x.com", "twitter.com"]):
            enviar_telegram(
                "⚠️ *URL do X detectada*\n\n"
                "Nao consigo ler o conteudo do X diretamente.\n"
                "Digite o *titulo ou assunto* da noticia:"
            )
            return "ok", 200

        # Tema em texto: busca e confirma
        if not texto.startswith("/"):
            enviar_telegram(f"🔍 _Buscando noticias sobre:_ *{texto[:80]}*\n_Aguarde..._")
            threading.Thread(target=buscar_e_confirmar, args=(chat_id, texto), daemon=True).start()

    except Exception as e:
        print(f"[ERRO webhook] {e}")
    return "ok", 200

# ─── TELEGRAM ────────────────────────────────────────────
def enviar_telegram(texto):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown", "disable_web_page_preview": False}
    resp = requests.post(url, json=payload, timeout=15)
    if resp.status_code != 200:
        print(f"[AVISO Telegram] {resp.status_code}: {resp.text[:200]}")

def configurar_webhook():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    webhook_url = f"{RENDER_URL}/webhook"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url}, timeout=10
        )
        data = resp.json()
        if data.get("ok"):
            print(f"[OK] Webhook: {webhook_url}")
        else:
            print(f"[AVISO] Webhook: {data}")
    except Exception as e:
        print(f"[AVISO] Webhook erro: {e}")

# ─── UTILIDADES ──────────────────────────────────────────
def limpar_html(html):
    html = re.sub(r'<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', html).strip()[:400]

def parsear_data_rss(data_str):
    """Converte string de data RSS para datetime. Retorna None se falhar."""
    formatos = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(data_str.strip(), fmt)
        except:
            continue
    return None

def dentro_de_2h(data_str):
    """Verifica se a noticia foi publicada nas ultimas 2 horas."""
    if not data_str:
        return True  # se nao tem data, inclui por precaucao
    dt = parsear_data_rss(data_str)
    if not dt:
        return True
    agora = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
    diff = agora - dt
    return diff.total_seconds() <= 7200  # 2h = 7200s

def extrair_palavras_chave(texto):
    """Extrai palavras-chave relevantes de um texto/URL para busca."""
    texto = re.sub(r'https?://[^/]+/', ' ', texto)
    texto = re.sub(r'[-_]', ' ', texto)
    stopwords = {'de', 'da', 'do', 'das', 'dos', 'e', 'o', 'a', 'os', 'as', 'em',
                 'no', 'na', 'nos', 'nas', 'por', 'para', 'com', 'que', 'se', 'um',
                 'uma', 'ao', 'aos', 'html', 'php', 'br', 'www', 'noticia', 'noticias',
                 'sobre', 'mais', 'este', 'essa', 'isso', 'pelo', 'pela', 'apos', 'alem'}
    palavras = [p for p in re.findall(r'[a-zA-ZÀ-ú]{4,}', texto) if p.lower() not in stopwords]
    palavras_unicas = list(dict.fromkeys(palavras))
    # Prioriza palavras mais longas (mais especificas)
    palavras_unicas.sort(key=len, reverse=True)
    return palavras_unicas[:5]

def montar_contexto(noticias, label="NOTICIAS RECENTES"):
    """Formata lista de noticias em contexto para o prompt."""
    if not noticias:
        return None, None, None, None
    vistos = set()
    unicos = []
    for item in noticias:
        chave = item[0][:40].lower()
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)
    if not unicos:
        return None, None, None, None
    linhas = []
    for titulo, veiculo, link, desc, data in unicos[:8]:
        hora = data[17:22] if len(data) > 17 else ""
        linhas.append(f"• [{veiculo}] {titulo} {hora}\n  {desc}")
    contexto = f"{label}:\n" + "\n\n".join(linhas)

    # Prioriza links diretos (NewsAPI, RSS direto) sobre redirects Google
    links_diretos = [i for i in unicos if "news.google.com" not in i[2]]
    pool_links = links_diretos if links_diretos else unicos

    # Resolve redirect do Google News para o primeiro link (chamada unica)
    link1_raw = pool_links[0][2]
    link1 = resolver_link_google_news(link1_raw) if "news.google.com" in link1_raw else link1_raw

    link2_raw = pool_links[1][2] if len(pool_links) > 1 else link1_raw
    link2 = resolver_link_google_news(link2_raw) if "news.google.com" in link2_raw else link2_raw

    veiculo1 = pool_links[0][1] or "Google News"
    return contexto, link1, veiculo1, link2

CACHE_LINKS = {}  # cache para evitar requisicoes repetidas

def resolver_link_google_news(url):
    """Resolve o link real seguindo o redirect do Google News."""
    if "news.google.com" not in url:
        return url
    if url in CACHE_LINKS:
        return CACHE_LINKS[url]
    try:
        resp = requests.get(
            url, timeout=8, allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        link_real = resp.url if resp.url and "news.google.com" not in resp.url else url
        CACHE_LINKS[url] = link_real
        return link_real
    except:
        return url

def resolver_links_em_paralelo(items):
    """Resolve links do Google News em paralelo para nao travar."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    resultados = list(items)
    indices_google = [i for i, item in enumerate(resultados) if "news.google.com" in item[2]]
    if not indices_google:
        return resultados
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(resolver_link_google_news, resultados[i][2]): i for i in indices_google}
        for future in as_completed(futures, timeout=15):
            i = futures[future]
            try:
                link_real = future.result()
                t = resultados[i]
                resultados[i] = (t[0], t[1], link_real, t[3], t[4])
            except:
                pass
    return resultados

def veiculo_confiavel(veiculo):
    v = veiculo.lower()
    return any(vc in v for vc in VEICULOS_CONFIAVEIS)

# ─── RSS ─────────────────────────────────────────────────
def parsear_rss(fonte, max_items=10, filtro_2h=False):
    """Parseia feed RSS. Se filtro_2h=True, retorna apenas noticias das ultimas 2h."""
    try:
        resp = requests.get(fonte, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        resultados = []
        for item in root.findall(".//item")[:max_items]:
            titulo_raw = item.findtext("title", "")
            partes = titulo_raw.rsplit(" - ", 1)
            titulo = partes[0].strip()
            veiculo = partes[1].strip() if len(partes) > 1 else ""
            # Link redirect do Google News (aponta para materia especifica via redirect)
            link_artigo = item.findtext("link", "").strip()
            # Homepage do veiculo (tag <source url="...">)
            source_el = item.find("source")
            link_homepage = source_el.get("url", "").strip() if source_el is not None else ""
            # Guarda o link_artigo como principal — vai ser resolvido depois se necessario
            link_final = link_artigo or link_homepage
            desc = limpar_html(item.findtext("description", ""))
            pub = item.findtext("pubDate", "")
            if titulo and len(titulo) > 15 and link_final:
                if filtro_2h and not dentro_de_2h(pub):
                    continue
                resultados.append((titulo, veiculo, link_final, desc, pub[:25]))
        return resultados
    except Exception as e:
        print(f"[AVISO RSS parse] {e}")
        return []

def buscar_rss_por_tema(query, filtro_2h=True):
    """Busca no Google News RSS por query especifica."""
    query_encoded = quote(query)
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date"
    print(f"[INFO] RSS query: {query}")
    items = parsear_rss(url, max_items=10, filtro_2h=filtro_2h)
    if not items and filtro_2h:
        # Se nao achou em 2h, amplia para 6h
        print(f"[INFO] Nada em 2h, ampliando para 6h...")
        items_6h = parsear_rss(url, max_items=10, filtro_2h=False)
        # Filtra manualmente para 6h
        items = []
        for item in items_6h:
            dt = parsear_data_rss(item[4]) if item[4] else None
            if dt:
                agora = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
                if (agora - dt).total_seconds() <= 21600:  # 6h
                    items.append(item)
            else:
                items.append(item)
    return items

# ─── NEWSAPI ─────────────────────────────────────────────
def buscar_newsapi_por_tema(query, horas=2):
    """Busca noticias recentes na NewsAPI sobre um tema."""
    api_key = os.environ.get("NEWS_API_KEY")
    if not api_key:
        return []
    from datetime import timedelta, timezone
    agora = datetime.now(timezone.utc)
    desde = agora - timedelta(hours=horas)
    from_str = desde.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        resp = requests.get("https://newsapi.org/v2/everything", params={
            "q": query,
            "language": "pt",
            "sortBy": "publishedAt",
            "from": from_str,
            "pageSize": 10,
            "apiKey": api_key
        }, timeout=10)
        if resp.status_code != 200:
            print(f"[AVISO NewsAPI] {resp.status_code}: {resp.text[:100]}")
            return []
        artigos = resp.json().get("articles", [])
        resultados = []
        for a in artigos:
            titulo = a.get("title", "").replace(" - ", " ").strip()
            veiculo = a.get("source", {}).get("name", "")
            link = a.get("url", "")
            desc = (a.get("description") or "")[:300]
            pub = a.get("publishedAt", "")[:16].replace("T", " ")
            if titulo and len(titulo) > 15 and "[Removed]" not in titulo and link:
                resultados.append((titulo, veiculo, link, desc, pub))
        print(f"[INFO] NewsAPI: {len(resultados)} noticias para '{query}'")
        return resultados
    except Exception as e:
        print(f"[AVISO NewsAPI] {e}")
        return []

# ─── BUSCA COMBINADA ─────────────────────────────────────
def buscar_noticias_tema_completo(tema):
    """Busca noticias do tema nas ultimas 2h usando RSS + NewsAPI combinados."""
    palavras = extrair_palavras_chave(tema)
    query = " ".join(palavras[:4]) if palavras else tema[:60]
    print(f"[INFO] Buscando tema completo: '{query}'")

    # 1. NewsAPI — links diretos das materias
    newsapi_items = buscar_newsapi_por_tema(query, horas=2)
    if len(newsapi_items) < 3:
        newsapi_items = buscar_newsapi_por_tema(query, horas=6)
    print(f"[INFO] NewsAPI: {len(newsapi_items)} noticias")

    # 2. RSS diretos (Metropoles, Poder360, Agencia Brasil) — links reais
    diretos = []
    for fonte in FONTES_RSS_DIRETO:
        try:
            items = parsear_rss(fonte, max_items=10, filtro_2h=True)
            # Filtra pelo tema
            for item in items:
                texto = (item[0] + " " + item[3]).lower()
                if any(p.lower() in texto for p in palavras[:3]):
                    diretos.append(item)
        except:
            pass
    print(f"[INFO] RSS direto: {len(diretos)} noticias")

    # 3. RSS Google News — bom para contexto
    rss_items = buscar_rss_por_tema(query, filtro_2h=True)
    print(f"[INFO] RSS Google: {len(rss_items)} noticias")

    # Prioridade: NewsAPI + RSS direto na frente (links reais), Google News no fim
    todos = newsapi_items + diretos + rss_items

    # Fallback se pouco resultado
    if len(todos) < 3:
        print(f"[INFO] Poucas noticias, expandindo busca RSS...")
        todos.extend(buscar_rss_por_tema(query, filtro_2h=False))

    if not todos:
        return None, None, None, None

    # Prioriza veiculos confiaveis
    confiaveis = [i for i in todos if veiculo_confiavel(i[1])]
    pool = confiaveis if len(confiaveis) >= 3 else todos

    return montar_contexto(pool, label=f"COBERTURA DA MIDIA — ultimas horas — '{query}'")

def buscar_noticias():
    """Busca automatica para posts agendados — pega noticia mais relevante do momento."""
    # Busca em paralelo: NewsAPI + RSS direto + Google News
    todos = []

    # 1. RSS diretos com filtro 6h
    for fonte in FONTES_RSS_DIRETO:
        try:
            items = parsear_rss(fonte, max_items=10, filtro_2h=False)
            for item in items:
                dt = parsear_data_rss(item[4]) if item[4] else None
                if not dt:
                    todos.append(item)
                    continue
                agora = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.utcnow()
                if (agora - dt).total_seconds() <= 21600:
                    todos.append(item)
        except Exception as e:
            print(f"[AVISO RSS direto agendado] {e}")
    print(f"[INFO] Agendado — RSS direto: {len(todos)} noticias")

    # 2. NewsAPI — ultimas 6h
    newsapi_items = buscar_newsapi_por_tema("politica Brasil governo", horas=6)
    todos.extend(newsapi_items)
    print(f"[INFO] Agendado — NewsAPI: {len(newsapi_items)} noticias")

    # 3. Google News RSS — fallback
    if len(todos) < 3:
        for fonte in FONTES_BREAKING:
            try:
                todos.extend(parsear_rss(fonte, filtro_2h=True))
            except Exception as e:
                print(f"[AVISO RSS breaking] {e}")
        if len(todos) < 3:
            fontes_pol = FONTES_POLITICA.copy()
            random.shuffle(fontes_pol)
            for fonte in fontes_pol[:3]:
                try:
                    todos.extend(parsear_rss(fonte, filtro_2h=False))
                except:
                    pass

    confiaveis = [i for i in todos if veiculo_confiavel(i[1])]
    pool = confiaveis if len(confiaveis) >= 3 else todos
    return montar_contexto(pool, label="NOTICIAS RECENTES DO DIA")

def eh_url_bloqueada(url):
    dominios_bloqueados = ['x.com', 'twitter.com', 'instagram.com', 'facebook.com', 'tiktok.com']
    return any(d in url.lower() for d in dominios_bloqueados)

def extrair_tema_da_url(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    dominio = parsed.netloc.replace("www.", "").split(".")[0]
    path = parsed.path.replace("/", " ").replace("-", " ").replace("_", " ")
    path = re.sub(r'\b\d{5,}\b', '', path)
    return f"{dominio} {path}".strip()

def buscar_conteudo_url(url):
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return None, None, None
        texto = limpar_html(resp.text)
        from urllib.parse import urlparse
        dominio = urlparse(url).netloc.replace("www.", "").split(".")[0].title()
        return texto[:1500], url, dominio
    except Exception as e:
        print(f"[AVISO URL] {e}")
    return None, None, None

def buscar_youtube():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return None
    termo = random.choice(["Lula discurso hoje", "Tarcisio Freitas declaracao", "governo federal anuncio", "congresso nacional votacao"])
    try:
        resp = requests.get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "snippet", "q": termo, "type": "video",
            "order": "date", "maxResults": 3, "regionCode": "BR",
            "relevanceLanguage": "pt", "key": api_key
        }, timeout=10)
        if resp.status_code != 200:
            return None
        videos = []
        for item in resp.json().get("items", []):
            s = item["snippet"]
            videos.append(f"• [{s['channelTitle']}] {s['title']} ({s['publishedAt'][:10]})")
        return "\n".join(videos) if videos else None
    except Exception as e:
        print(f"[AVISO YouTube] {e}")
    return None

# ─── GERACAO VIA GROQ ─────────────────────────────────────────────
def gerar_posts(tema_manual=None, bloco=1):
    """Retorna lista de posts gerados pelo Groq (Llama).
    bloco=1: logica original (raspa URL ou usa tema direto)
    bloco=2: busca RSS Google News com palavras-chave do tema
    """
    groq_key = os.environ.get("GROQ_API_KEY")
    link_fonte = None
    veiculo = None

    if bloco == 2:
        # Bloco 2: busca combinada RSS + NewsAPI das ultimas 2h
        termo_busca = tema_manual or "politica brasil escandalo"
        contexto, link_fonte, veiculo, link2_fonte = buscar_noticias_tema_completo(termo_busca)
        if contexto:
            pass  # ja formatado
        else:
            contexto = f"TEMA: {tema_manual}\nNao foram encontradas noticias recentes. Use o briefing."
    elif tema_manual:
        is_url = tema_manual.startswith("http://") or tema_manual.startswith("https://")
        if is_url and eh_url_bloqueada(tema_manual):
            # URL bloqueada (X, Twitter, etc): extrai tema e busca combinada
            print(f"[INFO] URL bloqueada, usando busca combinada: {tema_manual}")
            tema_extraido = extrair_tema_da_url(tema_manual)
            contexto, link_fonte, veiculo, link2_fonte = buscar_noticias_tema_completo(tema_extraido)
            if not contexto:
                contexto = f"URL do X/Twitter enviada: {tema_manual}\nSem resultados recentes. Use o briefing."
        elif is_url:
            # URL normal: tenta raspar, fallback para busca combinada
            print(f"[INFO] Raspando URL: {tema_manual}")
            conteudo, link_fonte, veiculo = buscar_conteudo_url(tema_manual)
            if conteudo:
                contexto = f"MATERIA COMPLETA [{veiculo}]:\n{conteudo}"
            else:
                print(f"[INFO] Raspagem falhou, usando busca combinada")
                tema_extraido = extrair_tema_da_url(tema_manual)
                contexto, link_fonte, veiculo, link2_fonte = buscar_noticias_tema_completo(tema_extraido)
                if not contexto:
                    contexto = f"URL enviada: {tema_manual}\nNao foi possivel buscar. Use o briefing."
        else:
            # Texto/tema livre: busca combinada RSS + NewsAPI
            print(f"[INFO] Tema livre, buscando cobertura: {tema_manual}")
            contexto, link_fonte, veiculo, link2_fonte = buscar_noticias_tema_completo(tema_manual)
            if not contexto:
                contexto = f"TEMA: {tema_manual}\nNao foram encontradas noticias. Use o briefing."
    else:
        noticias, link_fonte, veiculo, link2_fonte = buscar_noticias()
        videos = buscar_youtube()
        partes = []
        if noticias:
            partes.append(f"NOTICIAS RECENTES [{veiculo}]:\n{noticias}")
        if videos:
            partes.append(f"VIDEOS RECENTES:\n{videos}")
        contexto = "\n\n".join(partes) if partes else "Use o briefing para comentar politica brasileira atual."

    prompt = f"""{PERSONALIDADE}

{BRIEFING}

MATERIAL DO DIA:
{contexto}

INSTRUCAO CRITICA: Os posts DEVEM ser baseados nos fatos especificos do MATERIAL DO DIA acima.
Use nomes, datas, valores e eventos concretos que aparecem nas noticias.
NAO comente o cenario geral — comente O QUE ACABOU DE ACONTECER.
Se houver multiplas noticias, escolha o fato mais impactante e ironize em cima dele.

Gere 5 versoes de post com tons diferentes:
VERSAO1: Ironico e seco — sobre o fato especifico de hoje
VERSAO2: Analogia do dia a dia + ironia no final — conectada ao fato de hoje
VERSAO3: Pergunta retorica — sobre o que acabou de acontecer
VERSAO4: Comparacao temporal (promessa vs realidade) — usando o fato de hoje
VERSAO5: Didatico para quem nao acompanhou + ironia — explicando o fato de hoje

REGRAS CRITICAS:
- TODAS as 5 versoes sao obrigatorias — nao pule nenhuma
- Minimo 80 caracteres por versao, maximo 220 caracteres
- 2 hashtags no final — uma especifica do assunto + uma geral (#Brasil, #Politica, #STF ou #BancoMaster)
- NUNCA invente fatos — use apenas o briefing e o material do dia
- NUNCA use frases genericas como "rombo de R$50 bilhoes" se o fato de hoje e outro
- Complete cada versao antes de comecar a proxima
- Retorne EXATAMENTE neste formato sem texto adicional:
VERSAO1: [texto completo]
VERSAO2: [texto completo]
VERSAO3: [texto completo]
VERSAO4: [texto completo]
VERSAO5: [texto completo]"""

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.8
        },
        timeout=30
    )

    if resp.status_code != 200:
        raise Exception(f"Groq erro {resp.status_code}: {resp.text[:200]}")

    resposta = resp.json()["choices"][0]["message"]["content"].strip()
    print(f"[INFO] Resposta Groq:\n{resposta[:300]}")

    posts = []
    for linha in resposta.split("\n"):
        linha = linha.strip()
        for i in range(1, 6):
            for prefix in [f"VERSAO{i}:", f"VERSÃO{i}:", f"VERSAO {i}:", f"VERSÃO {i}:"]:
                if linha.upper().startswith(prefix.upper()):
                    texto = linha[len(prefix):].strip().strip('"').strip("'")
                    if texto:
                        if link_fonte:
                            com_link = f"{texto}\n\n🔗 {link_fonte}"
                            posts.append(com_link if len(com_link) <= 280 else texto)
                        else:
                            posts.append(texto)
                    break

    if not posts:
        print(f"[AVISO] Nenhuma versao extraida. Resposta completa:\n{resposta}")
        posts = [resposta[:220]]

    return posts, veiculo

def chamar_groq(prompt):
    """Chama a API do Groq e retorna o texto da resposta."""
    groq_key = os.environ.get("GROQ_API_KEY")
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.8
        },
        timeout=30
    )
    if resp.status_code != 200:
        raise Exception(f"Groq erro {resp.status_code}: {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]["content"].strip()

def extrair_posts_da_resposta(resposta, link_fonte):
    """Extrai as 5 versoes da resposta do modelo."""
    posts = []
    for linha in resposta.split("\n"):
        linha = linha.strip()
        for i in range(1, 6):
            for prefix in [f"VERSAO{i}:", f"VERSÃO{i}:", f"VERSAO {i}:", f"VERSÃO {i}:"]:
                if linha.upper().startswith(prefix.upper()):
                    texto = linha[len(prefix):].strip().strip('"').strip("'")
                    # Trunca o texto para caber com o link (max 220 chars para o texto)
                    if len(texto) > 220:
                        texto = texto[:217] + "..."
                    if texto:
                        if link_fonte:
                            posts.append(f"{texto}\n\n🔗 {link_fonte}")
                        else:
                            posts.append(texto)
                    break
    if not posts:
        posts = [resposta[:220]]
    return posts

def gerar_posts_com_contexto(contexto, link_fonte, veiculo):
    """Gera 5 posts usando um contexto ja preparado e validado."""
    prompt = f"""{PERSONALIDADE}

{BRIEFING}

NOTICIAS REAIS DE AGORA — USE SOMENTE ESTES FATOS:
{contexto}

INSTRUCAO ABSOLUTA:
- Comente APENAS os fatos especificos acima — nomes, datas, declaracoes reais
- PROIBIDO usar fatos genericos ou do briefing que nao aparecem nas noticias acima
- Se a noticia e sobre Toffoli, comente Toffoli. Se e sobre outro assunto, comente esse assunto
- Zero reciclagem de posts anteriores

Gere 5 versoes de post:
VERSAO1: Ironico e seco — sobre o fato especifico
VERSAO2: Analogia do dia a dia + ironia — conectada ao fato
VERSAO3: Pergunta retorica — sobre o que aconteceu
VERSAO4: Comparacao (promessa vs realidade) — usando o fato
VERSAO5: Didatico + ironia — explica o fato para quem nao acompanhou

REGRAS:
- 5 versoes obrigatorias
- 80 a 220 caracteres cada
- 2 hashtags no final — uma especifica do assunto + uma geral (#Brasil, #Politica, #STF ou #BancoMaster)
- Formato exato:
VERSAO1: [texto]
VERSAO2: [texto]
VERSAO3: [texto]
VERSAO4: [texto]
VERSAO5: [texto]"""

    resposta = chamar_groq(prompt)
    print(f"[INFO] Groq resposta:\n{resposta[:300]}")
    posts = extrair_posts_da_resposta(resposta, link_fonte)
    return posts, veiculo

def buscar_e_confirmar(chat_id, tema):
    """Busca noticias, mostra resumo e pede confirmacao antes de gerar posts."""
    try:
        contexto, link, veiculo, link2 = buscar_noticias_tema_completo(tema)

        if not contexto:
            enviar_telegram(
                f"⚠️ Nao encontrei noticias recentes sobre *{tema}*.\n\n"
                "Tente um tema mais especifico ou verifique se a noticia ja foi publicada."
            )
            return

        # Extrai titulos das noticias encontradas para mostrar ao usuario
        linhas = contexto.split("\n")
        titulos = [l.strip() for l in linhas if l.strip().startswith("•")][:5]
        lista = "\n".join(titulos)

        msg = (
            f"📰 *Encontrei essas noticias sobre '{tema}':*\n\n"
            f"{lista}\n\n"
            f"✅ Digite *sim* para gerar 10 posts em cima dessas noticias\n"
            f"❌ Digite *nao* para cancelar"
        )
        enviar_telegram(msg)

        # Salva estado aguardando confirmacao
        ESTADO_CONFIRMACAO[chat_id] = {
            "tema": tema,
            "contexto": contexto,
            "link": link,
            "link2": link2,
            "veiculo": veiculo
        }

    except Exception as e:
        print(f"[ERRO buscar_e_confirmar] {e}")
        enviar_telegram(f"❌ Erro na busca: `{str(e)[:150]}`")

def buscar_og_image(url):
    """Extrai og:image de uma URL de materia."""
    if not url or "news.google.com" in url:
        return None
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None
        # og:image com content antes ou depois
        for pattern in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']',
            r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']',
        ]:
            m = re.search(pattern, resp.text)
            if m:
                return m.group(1)
    except:
        pass
    return None

def enviar_bloco(posts, veiculo, titulo_bloco, link_imagem=None):
    """Envia um bloco de posts formatados no Telegram, com imagem no topo se disponivel."""
    fonte_info = f"📡 _{veiculo}_" if veiculo else "📚 _Contexto geral_"
    cabecalho = f"{titulo_bloco}\n{fonte_info}"

    # Tenta enviar imagem da materia no topo do bloco
    imagem_enviada = False
    if link_imagem:
        og_img = buscar_og_image(link_imagem)
        if og_img:
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            try:
                resp = requests.post(
                    f"https://api.telegram.org/bot{token}/sendPhoto",
                    json={
                        "chat_id": chat_id,
                        "photo": og_img,
                        "caption": cabecalho,
                        "parse_mode": "Markdown"
                    },
                    timeout=15
                )
                imagem_enviada = resp.status_code == 200
            except:
                pass

    if not imagem_enviada:
        enviar_telegram(cabecalho)

    time.sleep(0.3)
    for i, post in enumerate(posts, 1):
        link_x = f"https://twitter.com/intent/tweet?text={quote(post)}"
        msg = f"*Opcao {i}/{len(posts)}* ({len(post)} chars):\n_{post}_\n👉 [Publicar no X]({link_x})"
        enviar_telegram(msg)
        time.sleep(0.5)

def gerar_e_enviar(tema_manual=None, contexto_confirmado=None):
    try:
        if contexto_confirmado:
            # Fluxo confirmado: usa contexto ja buscado e aprovado
            tema = contexto_confirmado["tema"]
            contexto = contexto_confirmado["contexto"]
            link = contexto_confirmado["link"]
            link2 = contexto_confirmado.get("link2", link)
            veiculo = contexto_confirmado["veiculo"]
            print(f"[INFO] Gerando posts com contexto confirmado: {tema}")

            # Bloco 1: gera posts com contexto confirmado
            enviar_telegram("⏳ _Gerando Bloco 1..._")
            posts1, _ = gerar_posts_com_contexto(contexto, link, veiculo)
            enviar_bloco(posts1, veiculo, "🇧🇷 *@OlhaQueSurpresa* — Bloco 1")

            time.sleep(1)

            # Bloco 2: usa link2 (segunda noticia diferente)
            enviar_telegram("⏳ _Gerando Bloco 2 (fontes complementares)..._")
            newsapi_items = buscar_newsapi_por_tema(tema, horas=6)
            if newsapi_items:
                ctx2, lnk2, vec2, lnk2b = montar_contexto(newsapi_items, label="COBERTURA COMPLEMENTAR")
            else:
                ctx2, lnk2, vec2 = contexto, link2, veiculo
            posts2, _ = gerar_posts_com_contexto(ctx2 or contexto, lnk2 or link2, vec2 or veiculo)
            enviar_bloco(posts2, vec2 or veiculo, "🔍 *@OlhaQueSurpresa* — Bloco 2")

            enviar_telegram(f"_Total: 10 opcoes sobre '{tema}'. Escolha ou ignore._")

        elif tema_manual:
            # Fallback legado (nao deveria chegar aqui no novo fluxo)
            posts, veiculo = gerar_posts(tema_manual, bloco=1)
            enviar_bloco(posts, veiculo, "🇧🇷 *@OlhaQueSurpresa*")
            enviar_telegram("_Escolha uma opcao acima ou ignore._")

        else:
            # Posts automaticos agendados
            contexto, link, veiculo, link2 = buscar_noticias()
            if contexto:
                posts, _ = gerar_posts_com_contexto(contexto, link, veiculo)
            else:
                posts, veiculo = gerar_posts(None, bloco=1)
            enviar_bloco(posts, veiculo, "🇧🇷 *@OlhaQueSurpresa* — Post do dia")
            enviar_telegram("_Escolha uma opcao acima ou ignore._")

    except Exception as e:
        erro = traceback.format_exc()
        print(f"[ERRO gerar_e_enviar]\n{erro}")
        try:
            enviar_telegram(f"❌ Erro ao gerar post:\n`{str(e)[:200]}`")
        except:
            pass

# ─── MAIN ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print(" BOT @OlhaQueSurpresa - Politica BR")
    print(f" Horarios: {', '.join(HORARIOS_POSTS)} (Brasilia)")
    print("=" * 60)

    for var in ["GROQ_API_KEY", "NEWS_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YOUTUBE_API_KEY"]:
        print(f"[{'OK' if os.environ.get(var) else 'AUSENTE'}] {var}")

    if args.once:
        if args.dry_run:
            posts, _ = gerar_posts()
            for i, p in enumerate(posts, 1):
                print(f"\nOpcao {i}:\n{p}")
        else:
            gerar_e_enviar()
        return

    port = int(os.environ.get("PORT", 8080))
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True
    ).start()
    print(f"[OK] Flask na porta {port}")

    configurar_webhook()

    for h in HORARIOS_POSTS:
        schedule.every().day.at(h).do(gerar_e_enviar)
        print(f"[OK] Agendado: {h}")

    print("[INFO] Bot rodando. Mande tema pelo Telegram para post manual!\n")
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
