#!/usr/bin/env python3
"""
Gerador do site Cozinha Crocante.

Lê posts.json (as receitas), affiliates.json (links de afiliado) e site.json
(nome, domínio) e gera o site estático na pasta dist/:

  /                              home com todas as receitas
  /categoria/<categoria>/        listas por categoria
  /receitas/<slug>/              uma página por receita (URL amigável)
  /og/<slug>.png                 imagem de compartilhamento de cada receita
  /busca.json                    índice leve usado pela busca por ingredientes
  /sitemap.xml, /robots.txt, /404.html, /CNAME

Uso:
  python3 build.py                 # gera dist/
  python3 build.py --check         # só valida os dados, sem gerar nada

Variáveis de ambiente opcionais: SITE_URL, BASE_PATH, BUILD_DATE (AAAA-MM-DD).
"""
import datetime
import hashlib
import html as htmllib
import json
import os
import random
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
STATIC = ROOT / "static"

# ----------------------------------------------------------------- configuração
SITE = json.loads((ROOT / "site.json").read_text("utf-8"))
NOME = SITE["nome"]
SITE_URL = (os.environ.get("SITE_URL") or SITE["url"]).rstrip("/")
BASE = (os.environ.get("BASE_PATH") if os.environ.get("BASE_PATH") is not None else SITE.get("base", "")).strip()
BASE = "" if BASE in ("", "/") else "/" + BASE.strip("/")
COR = SITE.get("cor", "#d9482b")
BUILD_ID = os.environ.get("BUILD_ID", "local")   # no GitHub Actions: run id; serve para conferir se o deploy novo já está no ar
DEPLOY_TARGET = os.environ.get("DEPLOY_TARGET", "github")

# id usado nos dados -> (nome no menu, slug da URL, título da página, descrição)
CATEGORIAS = {
    "airfryer": ("Air fryer", "air-fryer", "Receitas na air fryer",
                 "Receitas rápidas e crocantes para fazer na air fryer: salgados, acompanhamentos e sobremesas com passo a passo simples."),
    "frigideira": ("Frigideira", "frigideira", "Receitas de frigideira",
                   "Receitas práticas para fazer na frigideira, de omelete a sobremesas, com poucos ingredientes e passo a passo direto."),
    "salgado": ("Salgados", "salgados", "Receitas salgadas rápidas",
                "Receitas salgadas simples para o almoço, o jantar e o lanche, na air fryer ou na frigideira."),
    "doce": ("Sobremesas", "sobremesas", "Sobremesas rápidas",
             "Sobremesas simples e rápidas para fazer em casa, na air fryer ou na frigideira."),
}
TAGS_VALIDAS = set(CATEGORIAS)
TEMPEROS = ["sal", "pimenta-do-reino", "azeite", "óleo", "orégano", "canela", "páprica", "alho em pó", "alecrim"]

LOJAS = [
    ("ml", "Mercado Livre", "ml", lambda q: "https://lista.mercadolivre.com.br/" + urllib.parse.quote(q).replace("%20", "-")),
]


def hoje():
    if os.environ.get("BUILD_DATE"):
        return datetime.date.fromisoformat(os.environ["BUILD_DATE"])
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    except Exception:
        return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()


def esc(s):
    return htmllib.escape(str(s), quote=True)


def url(caminho):
    """caminho relativo ao site -> URL com o base path (para links internos)."""
    return f"{BASE}{caminho}"


def url_abs(caminho):
    return f"{SITE_URL}{BASE}{caminho}"


def hash_arquivo(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()[:8]


# ----------------------------------------------------------------- dados
def carregar_posts():
    posts = json.loads((ROOT / "posts.json").read_text("utf-8"))
    aff = json.loads((ROOT / "affiliates.json").read_text("utf-8"))
    erros, avisos = [], []
    slugs = set()
    obrig = ["slug", "publicado", "titulo", "resumo", "emoji", "cor", "chave", "opc", "tags",
             "tempo", "porcoes", "nivel", "ingredientes", "passos", "dica", "produtos"]
    for i, r in enumerate(posts):
        nome = r.get("slug", f"#{i}")
        if nome in slugs:
            erros.append(f"{nome}: slug duplicado")
        slugs.add(nome)
        for c in obrig:
            if c not in r or r[c] in ("", None, []) and c not in ("opc",):
                erros.append(f"{nome}: campo ausente ou vazio: {c}")
        if erros and any(e.startswith(nome + ":") for e in erros):
            continue
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", r["slug"]):
            erros.append(f"{nome}: slug inválido (use letras minúsculas, números e hífens)")
        try:
            datetime.date.fromisoformat(r["publicado"])
        except ValueError:
            erros.append(f"{nome}: 'publicado' deve ser AAAA-MM-DD")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", r["cor"]):
            erros.append(f"{nome}: cor deve ser #RRGGBB")
        for t in r["tags"]:
            if t not in TAGS_VALIDAS:
                erros.append(f"{nome}: tag desconhecida '{t}' (válidas: {', '.join(sorted(TAGS_VALIDAS))})")
        if not any(t in ("airfryer", "frigideira") for t in r["tags"]) or not any(t in ("salgado", "doce") for t in r["tags"]):
            avisos.append(f"{nome}: ideal ter uma tag de método (airfryer/frigideira) e uma de tipo (salgado/doce)")
        if minutos(r["tempo"]) == 0:
            erros.append(f"{nome}: 'tempo' deve ser algo como '25 min' ou '1 h 10 min'")
        for p in r["produtos"]:
            if p["busca"] not in aff:
                avisos.append(f"{nome}: produto '{p['busca']}' não está em affiliates.json (usando link de busca)")
        if r.get("imagem") and not (ROOT / "img" / r["imagem"]).exists():
            erros.append(f"{nome}: imagem 'img/{r['imagem']}' não encontrada")
    if erros:
        print("ERROS nos dados:")
        for e in erros:
            print("  -", e)
        sys.exit(1)
    limite = hoje()
    visiveis = [r for r in posts if datetime.date.fromisoformat(r["publicado"]) <= limite]
    if not visiveis:
        print("ERRO: nenhuma receita publicada (verifique as datas em 'publicado' no posts.json).")
        sys.exit(1)
    agendadas = len(posts) - len(visiveis)
    visiveis = sorted(visiveis, key=lambda r: r["publicado"], reverse=True)   # estável: mantém a ordem do arquivo nas datas iguais
    return visiveis, aff, avisos, agendadas


def minutos(t):
    h = re.search(r"(\d+)\s*h", t)
    m = re.search(r"(\d+)\s*min", t)
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


# ----------------------------------------------------------------- imagens de compartilhamento
def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _escurecer(c, f):
    return tuple(max(0, int(v * f)) for v in c)


def _quebrar(d, texto, fonte, largura):
    linhas, atual = [], ""
    for p in texto.split():
        t = (atual + " " + p).strip()
        if d.textlength(t, font=fonte) <= largura:
            atual = t
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def gerar_card(titulo, cor, linha_meta, rotulo, destino, fundo=None):
    """Cria uma imagem 1200x630 (formato ideal para WhatsApp, Facebook, X)."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    fonts = STATIC / "fonts"
    bg = _rgb(cor)
    tomate, tinta = _rgb(COR), (43, 33, 24)
    img = Image.new("RGB", (W, H), bg)
    if fundo:
        from PIL import ImageOps
        foto = ImageOps.fit(Image.open(fundo).convert("RGB"), (W, H), Image.LANCZOS)
        # degradê escuro (forte à esquerda, onde fica o texto) para garantir leitura
        veu = Image.new("L", (W, H))
        veu.putdata([int(215 - 120 * min(1, x / W)) for _ in range(H) for x in range(W)])
        img = Image.composite(Image.new("RGB", (W, H), (20, 14, 9)), foto, veu)
        tinta = (255, 255, 255)
        d = ImageDraw.Draw(img)
    else:
        d = ImageDraw.Draw(img)
        d.ellipse((W - 560, -180, W + 160, 540), fill=_escurecer(bg, 0.94))
        d.ellipse((W - 420, 250, W + 80, 750), fill=_escurecer(bg, 0.89))
    d.rectangle((0, 0, 22, H), fill=tomate)

    marca = ImageFont.truetype(str(fonts / "DejaVuSans-Bold.ttf"), 30)
    d.text((80, 62), NOME.upper(), font=marca, fill=tomate)
    if rotulo:
        d.text((80, 108), rotulo.upper(), font=ImageFont.truetype(str(fonts / "DejaVuSans.ttf"), 24), fill=_escurecer(tinta, 1.8) if not fundo else (230, 220, 210))

    largura = W - 80 - 200
    for tam in (88, 76, 66, 56, 48):
        ft = ImageFont.truetype(str(fonts / "DejaVuSerif-Bold.ttf"), tam)
        linhas = _quebrar(d, titulo, ft, largura)
        if len(linhas) <= 3:
            break
    y = 175
    for ln in linhas:
        d.text((80, y), ln, font=ft, fill=tinta)
        y += int(tam * 1.22)

    if linha_meta:
        d.text((80, H - 100), linha_meta, font=ImageFont.truetype(str(fonts / "DejaVuSans-Bold.ttf"), 34), fill=tinta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, "PNG", optimize=True)


# ----------------------------------------------------------------- HTML
GAVETA = """<button class="aba" id="aba-busca" type="button" data-act="abrir" aria-haspopup="dialog" aria-expanded="false" aria-controls="gaveta">
  <span class="ico" aria-hidden="true">🔍</span><span>O que tenho em casa?</span><span class="badge" id="badge" hidden>0</span>
</button>

<aside class="gaveta" id="gaveta" role="dialog" aria-modal="true" aria-labelledby="gaveta-titulo" aria-hidden="true">
  <div class="gaveta-top"><div class="wrap">
    <h2 id="gaveta-titulo">Buscar por ingredientes</h2>
    <button class="fechar" type="button" data-act="fechar" aria-label="Fechar busca" title="Fechar (Esc)"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19"/></svg></button>
  </div></div>
  <div class="wrap gaveta-corpo">
    <section class="box finder">
      <p class="sub">Digite o que você tem em casa (separe por vírgula) e veja o que dá para fazer.</p>
      <form class="addrow" id="f-ing" autocomplete="off">
        <input id="ing-input" list="ing-list" placeholder="Ex.: ovo, banana, frango" aria-label="Ingrediente">
        <datalist id="ing-list"></datalist>
        <button class="btn-add" type="submit">Adicionar</button>
      </form>
      <div class="sel" id="sel"></div>
      <div class="quick"><span>Ou toque para adicionar:</span><div id="quick"></div></div>
      <div class="opts">
        <label><input type="radio" name="modo" value="exato" checked>
          <span>Só com o que tenho<small>Mostra receitas que usam apenas os ingredientes da minha lista.</small></span></label>
        <label><input type="radio" name="modo" value="mais">
          <span>Aceito comprar mais<small>Mostra receitas que usam algum dos meus ingredientes e o que falta.</small></span></label>
        <label><input type="checkbox" id="temperos" checked>
          <span>Já tenho temperos básicos<small id="lista-temperos">__TEMPEROS__</small></span></label>
      </div>
    </section>
    <div id="resultado-busca" aria-live="polite"></div>
  </div>
</aside>
"""


CTX = {"posts": []}
EMOJI_CAT = {"airfryer": "🍟", "frigideira": "🍳", "salgado": "🥪", "doce": "🍰"}
ICONE_CAT = {"airfryer": "fa-fire", "frigideira": "fa-kitchen-set", "salgado": "fa-burger", "doce": "fa-cake-candles"}


def lateral_esq():
    posts = CTX["posts"]
    menu = f'<li><a href="{url("/")}"><i class="fa-solid fa-house" aria-hidden="true"></i> <span>Início</span></a></li>'
    menu += "".join(f'<li><a href="{url("/categoria/" + c[1] + "/")}"><i class="fa-solid {ICONE_CAT[k]}" aria-hidden="true"></i> <span>{esc(c[0])}</span></a></li>' for k, c in CATEGORIAS.items())
    menu += '<li><button type="button" data-act="abrir"><i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i> <span>O que tenho em casa?</span></button></li>'
    comunidades = "".join(
        f'<a class="com" href="{url("/categoria/" + c[1] + "/")}"><span class="com-ico">{EMOJI_CAT[k]}</span>'
        f'<span class="com-nome">{esc(c[0])}</span><span class="com-n">{sum(1 for r in posts if k in r["tags"])} receitas</span></a>'
        for k, c in CATEGORIAS.items())
    return f"""<section class="box perfil">
  <div class="foto"><img src="{url('/assets/logo.png')}?v={hash_arquivo(STATIC / 'logo.png')}" alt="Logo {esc(NOME)}"></div>
  <h2 class="nome">{esc(NOME)}</h2>
  <p class="frase">“{esc(SITE.get('slogan', ''))}”</p>
  <ul class="menu">{menu}</ul>
  <dl class="ficha">
    <dt>Status</dt><dd>com fome e sem tempo</dd>
    <dt>Relacionamento</dt><dd>sério com a air fryer</dd>
    <dt>Gosto de</dt><dd>crocância, pouca louça</dd>
    <dt>Receitas</dt><dd>{len(posts)}</dd>
  </dl>
</section>
<section class="box">
  <div class="box-h"><h2>comunidades ({len(CATEGORIAS)})</h2></div>
  <div class="box-c coms">{comunidades}</div>
</section>"""


def escolhas_do_dia(posts, d):
    """Sorte do dia + 3 recados: sorteio determinístico pela data (mesma data = mesmo resultado).
    A sorte nunca repete a de ontem; os recados são distintos entre si e da sorte."""
    def embaralhar(dia):
        ordem = list(posts)
        random.Random(dia.isoformat()).shuffle(ordem)
        return ordem

    ontem = embaralhar(d - datetime.timedelta(days=1))[0]
    ordem = embaralhar(d)
    if len(ordem) > 1 and ordem[0]["slug"] == ontem["slug"]:
        ordem.append(ordem.pop(0))
    return ordem[0], ordem[1:4]


def lateral_dir():
    posts = CTX["posts"]
    if not posts:
        return ""
    d = hoje()
    sorte, recados = escolhas_do_dia(posts, d)
    rec = ""
    for r in recados:
        rec += (f'<div class="recado"><div class="rec-foto" style="background:{esc(r["cor"])}">{r["emoji"]}</div>'
                f'<div><a href="{url("/receitas/" + r["slug"] + "/")}">{esc(r["titulo"])}</a> escreveu:'
                f'<p>“{esc(r["dica"])}”</p></div></div>')
    return f"""<section class="box">
  <div class="box-h"><h2>sorte do dia</h2></div>
  <div class="box-c sorte"><a href="{url("/receitas/" + sorte["slug"] + "/")}"><span class="sorte-emoji" style="background:{esc(sorte["cor"])}">{sorte["emoji"]}</span>
    <strong>{esc(sorte["titulo"])}</strong></a>
    <p>A receita de hoje, escolhida pela sorte. Atualiza todo dia.</p></div>
</section>
<section class="box">
  <div class="box-h"><h2>recados</h2></div>
  <div class="box-c">{rec}</div>
</section>
<p class="atualizado">Atualizado em {d.strftime("%d/%m/%Y")}</p>"""


def pagina(*, titulo, descricao, caminho, corpo, og_image=None, og_dim=True, og_tipo="website",
           og_alt="", jsonld=None, noindex=False):
    canonical = url_abs(caminho)
    css = f"{url('/assets/style.css')}?v={hash_arquivo(STATIC / 'style.css')}"
    js = f"{url('/assets/app.js')}?v={hash_arquivo(STATIC / 'app.js')}"
    og_image = og_image or url_abs("/og/site.png")
    dim = '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' if og_dim else ""
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    nav = "".join(f'<a href="{url("/categoria/" + s + "/")}">{n}</a>' for (n, s, _, _) in CATEGORIAS.values())
    gaveta = GAVETA.replace("__TEMPEROS__", esc(", ".join(TEMPEROS) + "."))
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<meta name="description" content="{esc(descricao)}">
<link rel="canonical" href="{esc(canonical)}">
{'<meta name="robots" content="noindex">' if noindex else '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">'}
<meta name="theme-color" content="{esc(COR)}">
<link rel="icon" href="{url('/assets/favicon.svg')}?v={hash_arquivo(STATIC / 'favicon.svg')}" type="image/svg+xml">
<meta name="build-id" content="{esc(BUILD_ID)}">
<meta property="og:site_name" content="{esc(NOME)}">
<meta property="og:locale" content="pt_BR">
<meta property="og:type" content="{og_tipo}">
<meta property="og:title" content="{esc(titulo)}">
<meta property="og:description" content="{esc(descricao)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(og_image)}">
{dim}
<meta property="og:image:alt" content="{esc(og_alt or titulo)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(titulo)}">
<meta name="twitter:description" content="{esc(descricao)}">
<meta name="twitter:image" content="{esc(og_image)}">
<link rel="preload" href="{url('/assets/comfortaa-700.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{url('/assets/fa-brands-400.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{url('/assets/fa-solid-900.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{css}">
<script>window.SITE={json.dumps({"base": BASE})};</script>
{ld}
</head>
<body>
<header class="top">
  <div class="wrap">
    <a class="logo" href="{url('/')}"><img class="logo-img" src="{url('/assets/logo.png')}?v={hash_arquivo(STATIC / 'logo.png')}" alt="" width="30" height="34"><span>cozinha<b>crocante</b></span></a>
    <nav aria-label="Categorias">{nav}</nav>
  </div>
</header>

<div class="wrap layout">
<main class="col-meio">
{corpo}
</main>
<aside class="col-esq">
{lateral_esq()}
</aside>
<aside class="col-dir">
{lateral_dir()}
</aside>
</div>

{gaveta}
<footer>
  <div class="wrap">
    <p class="disc" id="sobre"><strong>Aviso de afiliados:</strong> alguns links deste site são de afiliados (Mercado Livre). Se você comprar por eles, posso receber uma comissão, sem nenhum custo extra para você. Isso ajuda a manter o {esc(NOME)} no ar.</p>
    <p>Preços, ofertas e disponibilidade mudam o tempo todo e são definidos pelas lojas; confira sempre na página do produto antes de comprar.</p>
    <p class="saudade">Feito com saudade dos tempos de recado, comunidade e foto com flash estourado. 💙</p>
    <p>Receitas originais do {esc(NOME)}. Tempos e temperaturas são aproximados e variam conforme o aparelho; ajuste ao seu equipamento. Cozinhe carnes até o ponto seguro (frango: 74 °C no centro).</p>
  </div>
</footer>
<script src="{js}" defer></script>
</body>
</html>
"""


def thumb(r, classe):
    if r.get("imagem"):
        return f'<div class="{classe}" style="background:{esc(r["cor"])}"><img src="{url("/img/" + esc(r["imagem"]))}" alt="" loading="lazy"></div>'
    return f'<div class="{classe}" style="background:{esc(r["cor"])}">{r["emoji"]}</div>'


def card(r):
    tags = "".join(f'<span class="tag">{esc(CATEGORIAS[t][0])}</span>' for t in r["tags"])
    return f"""    <a class="card" href="{url('/receitas/' + r['slug'] + '/')}">
      {thumb(r, 'thumb')}
      <div class="body">
        <div class="tags">{tags}</div>
        <h3>{esc(r['titulo'])}</h3>
        <p>{esc(r['resumo'])}</p>
        <div class="meta"><span>⏱ {esc(r['tempo'])}</span><span>🍽 {esc(r['porcoes'])}</span></div>
      </div>
    </a>"""


def chips(ativo):
    itens = [("todas", "Todas", "/")] + [(k, v[0], "/categoria/" + v[1] + "/") for k, v in CATEGORIAS.items()]
    return '<div class="chips" role="navigation" aria-label="Filtrar por categoria">' + "".join(
        f'<a class="chip" href="{url(c)}" aria-current="{"page" if k == ativo else "false"}">{esc(n)}</a>' for k, n, c in itens
    ) + "</div>"


def link_loja(loja, prod, aff):
    cfg = aff.get(prod["busca"], {})
    if cfg.get(loja[0]):
        return cfg[loja[0]], True
    return loja[3](prod["busca"]), False


def relacionadas(r, todas, n=3):
    def chaves(x):
        return {k for k in x["chave"] if k not in TEMPEROS}

    def pontos(o):
        return 2 * len(set(r["tags"]) & set(o["tags"])) + len(chaves(r) & chaves(o))
    outras = [o for o in todas if o["slug"] != r["slug"]]
    return sorted(outras, key=lambda o: -pontos(o))[:n]


def pagina_receita(r, todas, aff, imagem_og):
    caminho = f"/receitas/{r['slug']}/"
    canon = url_abs(caminho)
    cat_principal = next((t for t in r["tags"] if t in ("salgado", "doce")), r["tags"][0])
    cat_nome, cat_slug = CATEGORIAS[cat_principal][0], CATEGORIAS[cat_principal][1]
    tags = "".join(f'<a class="tag" href="{url("/categoria/" + CATEGORIAS[t][1] + "/")}">{esc(CATEGORIAS[t][0])}</a>' for t in r["tags"])
    ing = "".join(f'<li><label><input type="checkbox"><span>{esc(i)}</span></label></li>' for i in r["ingredientes"])
    passos = "".join(f"<li><span>{esc(p)}</span></li>" for p in r["passos"])
    prods = ""
    for p in r["produtos"]:
        bts = ""
        for loja in LOJAS:
            href, afiliado = link_loja(loja, p, aff)
            rel = "sponsored nofollow noopener" if afiliado else "nofollow noopener"
            bts += f'<a class="btn {loja[2]}" href="{esc(href)}" target="_blank" rel="{rel}">{loja[1]}</a>'
        prods += f'<div class="prod"><div><strong>{esc(p["nome"])}</strong><small>{esc(p["nota"])}</small></div><div class="btns">{bts}</div></div>'
    video = ""
    if r.get("video"):
        canal = f' — {esc(r["video"]["canal"])}' if r["video"].get("canal") else ""
        video = f'<a class="video" href="{esc(r["video"]["url"])}" target="_blank" rel="noopener">▶ Ver no YouTube{canal}</a>'

    q = urllib.parse.quote
    texto = f'{r["titulo"]} — {NOME}'
    compartilhar = f"""<div class="share" data-url="{esc(canon)}" data-title="{esc(texto)}">
            <span>Compartilhar:</span>
            <a class="sbtn ico" href="https://wa.me/?text={q(texto + ' ' + canon)}" target="_blank" rel="noopener" aria-label="Compartilhar no WhatsApp" title="WhatsApp"><i class="fa-whatsapp" aria-hidden="true"></i></a>
            <a class="sbtn ico" href="https://www.facebook.com/sharer/sharer.php?u={q(canon, safe='')}" target="_blank" rel="noopener" aria-label="Compartilhar no Facebook" title="Facebook"><i class="fa-facebook" aria-hidden="true"></i></a>
            <a class="sbtn ico" href="https://twitter.com/intent/tweet?url={q(canon, safe='')}&amp;text={q(texto)}" target="_blank" rel="noopener" aria-label="Compartilhar no X" title="X"><i class="fa-x-twitter" aria-hidden="true"></i></a>
            <a class="sbtn ico" href="https://pinterest.com/pin/create/button/?url={q(canon, safe='')}&amp;media={q(imagem_og, safe='')}&amp;description={q(r['titulo'])}" target="_blank" rel="noopener" aria-label="Compartilhar no Pinterest" title="Pinterest"><i class="fa-pinterest" aria-hidden="true"></i></a>
            <button class="sbtn" type="button" data-copiar>Copiar link</button>
            <button class="sbtn" type="button" data-nativo hidden>Mais…</button>
          </div>"""

    rel = "".join(card(o) for o in relacionadas(r, todas))
    relacionadas_html = f'<section class="box related"><div class="box-h"><h2>veja também</h2></div><div class="box-c"><div class="grid">\n{rel}\n</div></div></section>' if rel else ""

    corpo = f"""<nav class="breadcrumb" aria-label="Você está em"><a href="{url('/')}">Início</a> › <a href="{url('/categoria/' + cat_slug + '/')}">{esc(cat_nome)}</a> › <span>{esc(r['titulo'])}</span></nav>
<article>
  <div class="recipe-head">
    <div>
      <div class="tags">{tags}</div>
      <h1>{esc(r['titulo'])}</h1>
      <p>{esc(r['resumo'])}</p>
      <div class="facts">
        <div class="fact"><b>Tempo</b>{esc(r['tempo'])}</div>
        <div class="fact"><b>Rende</b>{esc(r['porcoes'])}</div>
        <div class="fact"><b>Nível</b>{esc(r['nivel'])}</div>
      </div>
      {video}
      {compartilhar}
    </div>
    {thumb(r, 'big-thumb')}
  </div>

  <div class="cols">
    <section class="box">
      <div class="box-h"><h2>Ingredientes</h2></div>
      <div class="box-c"><ul class="ing">{ing}</ul></div>
    </section>
    <section class="box">
      <div class="box-h"><h2>Modo de preparo</h2></div>
      <div class="box-c"><ol class="steps">{passos}</ol>
      <div class="tip"><strong>Recado da cozinha:</strong> {esc(r['dica'])}</div></div>
    </section>
  </div>

  <section class="box shop">
    <div class="box-h"><h2>Utensílios que ajudam nesta receita</h2></div>
    <div class="box-c"><p class="sub">Links de afiliado: posso receber comissão se você comprar, sem custo extra.</p>
    {prods}</div>
  </section>
  {relacionadas_html}
</article>"""

    total = minutos(r["tempo"])
    jsonld = [{
        "@context": "https://schema.org", "@type": "Recipe",
        "name": r["titulo"], "description": r["resumo"], "image": [imagem_og],
        "author": {"@type": "Organization", "name": NOME},
        "datePublished": r["publicado"],
        "totalTime": f"PT{total}M", "recipeYield": r["porcoes"],
        "recipeCategory": cat_nome, "recipeCuisine": "Brasileira",
        "keywords": ", ".join([CATEGORIAS[t][0] for t in r["tags"]] + [k.split("|")[0] for k in r["chave"] if k not in TEMPEROS]),
        "recipeIngredient": r["ingredientes"],
        "recipeInstructions": [{"@type": "HowToStep", "text": p} for p in r["passos"]],
        "mainEntityOfPage": canon, "inLanguage": "pt-BR", "dateModified": r["publicado"],
        "publisher": {"@type": "Organization", "name": NOME, "url": url_abs("/")},
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": url_abs("/")},
            {"@type": "ListItem", "position": 2, "name": cat_nome, "item": url_abs("/categoria/" + cat_slug + "/")},
            {"@type": "ListItem", "position": 3, "name": r["titulo"], "item": canon},
        ],
    }]
    return pagina(titulo=f"{r['titulo']} — {NOME}", descricao=r["resumo"], caminho=caminho, corpo=corpo,
                  og_image=imagem_og, og_dim=True, og_tipo="article", og_alt=r["titulo"], jsonld=jsonld)


# ----------------------------------------------------------------- cabeçalhos (Cloudflare Pages)
def cabecalhos_cloudflare():
    """Arquivo _headers do Cloudflare Pages. O GitHub Pages não permite mudar cabeçalhos."""
    b = BASE
    return f"""# Gerado pelo build.py (DEPLOY_TARGET=cloudflare). Formato do Cloudflare Pages.
# Arquivos em /assets/ são referenciados com ?v=<hash>, então podem ficar 1 ano no cache.
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin

{b}/assets/*
  Cache-Control: public, max-age=31536000, immutable

{b}/og/*
  Cache-Control: public, max-age=86400

{b}/img/*
  Cache-Control: public, max-age=86400

{b}/busca.json
  Cache-Control: public, max-age=0, must-revalidate

{b}/version.json
  Cache-Control: no-store
"""


# ----------------------------------------------------------------- build
def escrever(rel, conteudo):
    p = DIST / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, bytes):
        p.write_bytes(conteudo)
    else:
        p.write_text(conteudo, "utf-8")


def main():
    posts, aff, avisos, agendadas = carregar_posts()
    if "--check" in sys.argv:
        print(f"OK: {len(posts)} receitas válidas ({agendadas} agendadas para o futuro).")
        for a in avisos:
            print("  aviso:", a)
        return

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    # arquivos estáticos
    (DIST / "assets").mkdir(exist_ok=True)
    for f in STATIC.iterdir():
        if f.is_file():
            shutil.copy(f, DIST / "assets" / f.name)
    if (ROOT / "img").exists():
        shutil.copytree(ROOT / "img", DIST / "img")

    # imagens de compartilhamento
    try:
        import PIL  # noqa: F401
        tem_pillow = True
    except ImportError:
        tem_pillow = False
        avisos.append("Pillow não instalado: imagens de compartilhamento não foram geradas (pip install pillow)")
    og_site = url_abs("/og/site.png")
    if tem_pillow:
        gerar_card(NOME, "#fbf6ee", "", SITE.get("slogan", ""), DIST / "og" / "site.png")

    CTX["posts"] = posts

    # páginas das receitas
    for r in posts:
        if r.get("imagem") and not tem_pillow:
            og = url_abs("/img/" + r["imagem"])
        elif tem_pillow:
            rotulo = " · ".join(CATEGORIAS[t][0] for t in r["tags"])
            fundo = ROOT / "img" / r["imagem"] if r.get("imagem") else None
            gerar_card(r["titulo"], r["cor"], f"{r['tempo']}  •  {r['porcoes']}", rotulo, DIST / "og" / f"{r['slug']}.png", fundo)
            og = url_abs(f"/og/{r['slug']}.png")
        else:
            og = og_site
        escrever(f"receitas/{r['slug']}/index.html", pagina_receita(r, posts, aff, og))

    # home e categorias
    hero = f"""<section class="box hero">
  <div class="box-h"><h2>bem-vindo(a) ao {esc(NOME)}!</h2></div>
  <div class="box-c"><h1>Receitas <em>rápidas</em> e simples para o dia a dia</h1>
  <p>Pratos salgados e sobremesas que você faz na air fryer ou na frigideira. Sem ideia do que cozinhar? Clique em “O que tenho em casa?” no menu.</p></div>
</section>"""
    grid = lambda lista: '<div class="grid">\n' + "\n".join(card(r) for r in lista) + "\n</div>"
    site_ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": NOME, "url": url_abs("/"), "inLanguage": "pt-BR", "publisher": {"@type": "Organization", "name": NOME, "url": url_abs("/")}}]
    escrever("index.html", pagina(
        titulo=f"{NOME} — receitas rápidas na air fryer e na frigideira", descricao=SITE["descricao"], caminho="/",
        corpo=hero + chips("todas") + grid(posts), og_image=og_site if tem_pillow else None, jsonld=site_ld))
    for k, (nome, slug, titulo, desc) in CATEGORIAS.items():
        lista = [r for r in posts if k in r["tags"]]
        corpo = f'<section class="box hero"><div class="box-h"><h2>categoria</h2></div><div class="box-c"><h1>{esc(titulo)}</h1><p>{esc(desc)}</p></div></section>' + chips(k) + grid(lista)
        escrever(f"categoria/{slug}/index.html", pagina(
            titulo=f"{titulo} — {NOME}", descricao=desc, caminho=f"/categoria/{slug}/", corpo=corpo,
            og_image=og_site if tem_pillow else None,
            jsonld=[{"@context": "https://schema.org", "@type": "CollectionPage", "name": titulo, "description": desc,
                     "url": url_abs(f"/categoria/{slug}/"), "inLanguage": "pt-BR",
                     "hasPart": [{"@type": "Recipe", "name": r["titulo"], "url": url_abs("/receitas/" + r["slug"] + "/")} for r in lista]},
                    {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Início", "item": url_abs("/")},
                        {"@type": "ListItem", "position": 2, "name": nome, "item": url_abs(f"/categoria/{slug}/")}]}]))

    # 404
    escrever("404.html", pagina(
        titulo=f"Página não encontrada — {NOME}", descricao="Essa página não existe.", caminho="/404.html", noindex=True,
        corpo=f'<section class="box hero"><div class="box-h"><h2>erro 404</h2></div><div class="box-c"><h1>Ops, essa página <em>não existe</em></h1><p>O endereço pode ter mudado. Veja as receitas mais recentes na <a href="{url("/")}">página inicial</a>.</p></div></section>'))

    # índice leve para a busca por ingredientes
    busca = [{k: r.get(k) for k in ("slug", "titulo", "resumo", "emoji", "cor", "tags", "tempo", "porcoes", "chave", "opc", "imagem") if r.get(k) not in (None, "")}
             for r in posts]
    escrever("busca.json", json.dumps(busca, ensure_ascii=False, separators=(",", ":")))

    # sitemap, robots, CNAME
    urls = [("/", max(r["publicado"] for r in posts))]
    urls += [(f"/categoria/{s}/", max(r["publicado"] for r in posts)) for (_, s, _, _) in CATEGORIAS.values()]
    urls += [(f"/receitas/{r['slug']}/", r["publicado"]) for r in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sm += "".join(f"  <url><loc>{esc(url_abs(c))}</loc><lastmod>{d}</lastmod></url>\n" for c, d in urls) + "</urlset>\n"
    escrever("sitemap.xml", sm)
    escrever("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {url_abs('/sitemap.xml')}\n")
    host = urllib.parse.urlparse(SITE_URL).netloc
    if BASE == "" and host and not host.endswith("github.io"):
        escrever("CNAME", host + "\n")
    escrever(".nojekyll", "")
    escrever("version.json", json.dumps({
        "build": BUILD_ID,
        "sha": os.environ.get("GITHUB_SHA", ""),
        "gerado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }))
    if DEPLOY_TARGET == "cloudflare":
        escrever("_headers", cabecalhos_cloudflare())

    print(f"Site gerado em {DIST}: {len(posts)} receitas, {len(CATEGORIAS)} categorias"
          + (f", {agendadas} agendadas (ainda não publicadas)" if agendadas else ""))
    print(f"URL base: {SITE_URL}{BASE}")
    sem_link = sorted({p["busca"] for r in posts for p in r["produtos"] if not any(aff.get(p["busca"], {}).values())})
    if sem_link:
        print(f"Produtos sem nenhum link de afiliado em affiliates.json ({len(sem_link)}): " + ", ".join(sem_link))
    for a in avisos:
        print("aviso:", a)


if __name__ == "__main__":
    main()
