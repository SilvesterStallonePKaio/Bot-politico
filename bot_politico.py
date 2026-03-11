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

        if texto and not texto.startswith("/"):
            enviar_telegram(f"✅ Tema recebido! Gerando posts sobre:\n_{texto[:100]}_\n\nAguarde...")
            threading.Thread(target=gerar_e_enviar, args=(texto,), daemon=True).start()
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

# ─── RSS ─────────────────────────────────────────────────
def limpar_html(html):
    html = re.sub(r'<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', html).strip()[:400]

def parsear_rss(fonte, max_items=8):
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
        link = item.findtext("link", "").strip()
        desc = limpar_html(item.findtext("description", ""))
        pub = item.findtext("pubDate", "")[:25]
        if titulo and len(titulo) > 15 and link:
            resultados.append((titulo, veiculo, link, desc, pub))
    return resultados

def veiculo_confiavel(veiculo):
    v = veiculo.lower()
    return any(vc in v for vc in VEICULOS_CONFIAVEIS)

def buscar_noticias():
    todos = []
    for fonte in FONTES_BREAKING:
        try:
            items = parsear_rss(fonte)
            todos.extend(items)
        except Exception as e:
            print(f"[AVISO RSS breaking] {e}")

    fontes_pol = FONTES_POLITICA.copy()
    random.shuffle(fontes_pol)
    for fonte in fontes_pol[:4]:
        try:
            items = parsear_rss(fonte)
            todos.extend(items)
        except Exception as e:
            print(f"[AVISO RSS politica] {e}")

    if not todos:
        print("[AVISO] Nenhuma noticia encontrada")
        return None, None, None

    confiaveis = [i for i in todos if veiculo_confiavel(i[1])]
    pool = confiaveis if confiaveis else todos

    vistos = set()
    unicos = []
    for item in pool:
        chave = item[0][:40].lower()
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)

    if not unicos:
        return None, None, None

    principal = unicos[0]
    titulo_p, veiculo_p, link_p, desc_p, data_p = principal

    contexto_items = []
    for titulo, veiculo, link, desc, data in unicos[:6]:
        contexto_items.append(f"• {titulo} [{veiculo}] {data}\n  {desc}")

    contexto = "\n\n".join(contexto_items)
    print(f"[INFO] {len(unicos)} noticias unicas. Principal: {veiculo_p} — {titulo_p[:60]}")
    return contexto, link_p, veiculo_p

def buscar_conteudo_url(url):
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return None
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
def gerar_posts(tema_manual=None):
    """Retorna lista de posts gerados pelo Groq (Llama)."""
    groq_key = os.environ.get("GROQ_API_KEY")
    link_fonte = None
    veiculo = None

    if tema_manual:
        if tema_manual.startswith("http://") or tema_manual.startswith("https://"):
            print(f"[INFO] Buscando conteudo da URL: {tema_manual}")
            conteudo, link_fonte, veiculo = buscar_conteudo_url(tema_manual)
            if conteudo:
                contexto = f"MATERIA COMPLETA [{veiculo}]:\n{conteudo}"
                print(f"[INFO] Conteudo obtido: {len(conteudo)} chars")
            else:
                contexto = f"URL enviada: {tema_manual}\nNao foi possivel buscar o conteudo. Use o briefing."
        else:
            contexto = f"TEMA: {tema_manual}"
    else:
        noticias, link_fonte, veiculo = buscar_noticias()
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

Gere 5 versoes de post com tons diferentes:
VERSAO1: Ironico e seco
VERSAO2: Analogia do dia a dia + ironia no final
VERSAO3: Pergunta retorica
VERSAO4: Comparacao temporal (promessa vs realidade)
VERSAO5: Didatico para quem nao acompanhou + ironia

REGRAS CRITICAS:
- TODAS as 5 versoes sao obrigatorias — nao pule nenhuma
- Minimo 80 caracteres por versao, maximo 220 caracteres
- 1 hashtag no final (#Brasil ou #BancoMaster ou #Politica)
- NUNCA invente fatos — use apenas o briefing e o material do dia
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

def gerar_e_enviar(tema_manual=None):
    try:
        print(f"[INFO] Gerando posts... tema={tema_manual}")
        posts, veiculo = gerar_posts(tema_manual)
        print(f"[INFO] {len(posts)} posts gerados")

        fonte_info = f"📡 _{veiculo}_" if veiculo else "📚 _Contexto geral_"
        enviar_telegram(f"🇧🇷 *@OlhaQueSurpresa* — {len(posts)} opcoes!\n{fonte_info}")
        time.sleep(0.5)

        for i, post in enumerate(posts, 1):
            link_x = f"https://twitter.com/intent/tweet?text={quote(post)}"
            msg = f"*Opcao {i}/{len(posts)}* ({len(post)} chars):\n_{post}_\n👉 [Publicar no X]({link_x})"
            enviar_telegram(msg)
            time.sleep(0.5)

        enviar_telegram("_Escolha uma opcao acima ou ignore._")
        print(f"[INFO] {len(posts)} opcoes enviadas!")
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

    for var in ["GROQ_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YOUTUBE_API_KEY"]:
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
