"""
Bot @OlhaQueSurpresa — Posts politicos para o X
Render + Telegram + Claude + Google News RSS + YouTube
"""

import anthropic, schedule, requests, random, argparse
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
HORARIOS_POSTS = ["11:00", "15:00", "18:00", "21:00"]  # UTC-3 via UTC
RENDER_URL = "https://bot-politico.onrender.com"

FONTES_RSS = [
    "https://news.google.com/rss/search?q=pol%C3%ADtica+Brasil+esc%C3%A2ndalo&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Lula+governo+federal+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Banco+Master+STF+corrupcao+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=Tarcisio+Bolsonaro+oposicao+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
    "https://news.google.com/rss/search?q=congresso+nacional+votacao+polemica&hl=pt-BR&gl=BR&ceid=BR:pt-419&sort=date",
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
            enviar_telegram(f"✅ Tema recebido! Gerando posts sobre:\n_{texto}_\n\nAguarde...")
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

def buscar_noticias():
    """Retorna (texto_contexto, link, veiculo) ou (None, None, None)"""
    fonte = random.choice(FONTES_RSS)
    try:
        resp = requests.get(fonte, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None, None, None
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:6]
        noticias = []
        primeiro_link = None
        primeiro_veiculo = "Imprensa Nacional"
        for item in items:
            titulo_raw = item.findtext("title", "")
            partes = titulo_raw.rsplit(" - ", 1)
            titulo = partes[0].strip()
            veiculo = partes[1].strip() if len(partes) > 1 else "Imprensa Nacional"
            link = item.findtext("link", "").strip()
            desc = limpar_html(item.findtext("description", ""))
            if titulo:
                noticias.append(f"• {titulo} [{veiculo}]\n  {desc}")
                if not primeiro_link and link:
                    primeiro_link = link
                    primeiro_veiculo = veiculo
        if noticias:
            print(f"[INFO] {len(noticias)} noticias. Fonte: {primeiro_veiculo}")
            return "\n".join(noticias[:5]), primeiro_link, primeiro_veiculo
    except Exception as e:
        print(f"[AVISO RSS] {e}")
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

# ─── GERACAO ─────────────────────────────────────────────
def gerar_posts(tema_manual=None):
    """Retorna lista de posts gerados pelo Claude."""
    claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    link_fonte = None
    veiculo = None

    if tema_manual:
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

REGRAS:
- Maximo 220 caracteres por versao
- 1 hashtag no final (#Brasil ou #BancoMaster ou #Politica)
- NUNCA invente fatos
- Retorne EXATAMENTE neste formato:
VERSAO1: [texto]
VERSAO2: [texto]
VERSAO3: [texto]
VERSAO4: [texto]
VERSAO5: [texto]"""

    msg = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    resposta = msg.content[0].text.strip()
    print(f"[INFO] Resposta Claude:\n{resposta[:300]}")

    posts = []
    for linha in resposta.split("\n"):
        linha = linha.strip()
        for i in range(1, 6):
            for prefix in [f"VERSAO{i}:", f"VERSÃO{i}:", f"VERSAO {i}:", f"VERSÃO {i}:"]:
                if linha.upper().startswith(prefix.upper()):
                    texto = linha[len(prefix):].strip().strip('"').strip("'")
                    if texto:
                        # Adiciona link se disponivel e couber
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

    for var in ["ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "YOUTUBE_API_KEY"]:
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
