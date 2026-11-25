#!/usr/bin/env python3
"""
Gerador do site Cozinha Crocante.

Lê posts.json (as receitas), affiliates.json (links de afiliado) e site.json
(nome, domínio) e gera o site estático na pasta dist/:

  /                              home com todas as receitas
  /categoria/<categoria>/        listas por categoria
  /receitas/<slug>/              uma página por receita (URL amigável)
  /og/<slug>.jpg                 imagem de compartilhamento de cada receita
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
import unicodedata
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


# ----------------------------------------------------------------- jogo da palavra do dia
DICIONARIO = STATIC / "dicionario"          # static/dicionario/<n>.txt, gerado por scripts/dicionario.py
FORMA_PALAVRA = re.compile(r"[a-z]{4,10}")  # depois de normalizar (sem acento, minúscula)
_dicionarios = {}


def normalizar_palavra(s):
    s = unicodedata.normalize("NFD", str(s).strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def dicionario(n):
    """palavras de n letras (conjunto de strings normalizadas); vazio se o arquivo não existir"""
    if n not in _dicionarios:
        p = DICIONARIO / f"{n}.txt"
        _dicionarios[n] = set(p.read_text("utf-8").split()) if p.exists() else set()
    return _dicionarios[n]


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
    palavras_vistas = {}
    obrig =["slug", "publicado", "titulo", "resumo", "emoji", "cor", "chave", "opc", "tags",
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
        if r.get("palavra"):
            norm = normalizar_palavra(r["palavra"])
            if not FORMA_PALAVRA.fullmatch(norm):
                erros.append(f"{nome}: 'palavra' deve ter de 4 a 10 letras de a-z (com ou sem acento), sem espaço, número ou hífen")
            elif norm in palavras_vistas:
                erros.append(f"{nome}: palavra '{r['palavra']}' repetida (também em {palavras_vistas[norm]})")
            else:
                palavras_vistas[norm] = nome
                if norm not in dicionario(len(norm)):
                    erros.append(f"{nome}: palavra '{r['palavra']}' não está em static/dicionario/{len(norm)}.txt. "
                                 "Rode: python3 scripts/dicionario.py sincronizar")
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
    if sum(1 for r in visiveis if r.get("palavra")) < 2:
        avisos.append("menos de 2 receitas publicadas com 'palavra': o jogo da palavra do dia não será gerado")
    agendadas = len(posts) - len(visiveis)
    visiveis = sorted(visiveis, key=lambda r: r["publicado"], reverse=True)   # estável: mantém a ordem do arquivo nas datas iguais
    return visiveis, aff, avisos, agendadas


def minutos(t):
    h = re.search(r"(\d+)\s*h", t)
    m = re.search(r"(\d+)\s*min", t)
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


# ----------------------------------------------------------------- otimização das fotos
IMG_MAX_LARGURA = 1000   # px; suficiente para a página da receita em telas 2x
IMG_QUALIDADE = 78
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def otimizar_imagens(posts, tem_pillow):
    """Converte as fotos de img/ para JPEG progressivo reduzido em dist/img/.

    As originais ficam intactas em img/ (e continuam valendo no posts.json). Cada receita
    ganha `imagem_original` (arquivo-fonte, usado no card OG) e `imagem` passa a apontar
    para o .jpg gerado. Sem Pillow, copia as originais sem alterar."""
    origem = ROOT / "img"
    if not origem.exists():
        return
    destino = DIST / "img"
    destino.mkdir(exist_ok=True)
    fotos = sorted(f for f in origem.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT)
    antes = depois = 0
    for f in fotos:
        antes += f.stat().st_size
        if not tem_pillow:
            shutil.copy(f, destino / f.name)
            depois += f.stat().st_size
            continue
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(f))
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            fundo = Image.new("RGB", im.size, (255, 255, 255))
            fundo.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
            im = fundo
        else:
            im = im.convert("RGB")
        if im.width > IMG_MAX_LARGURA:
            im = im.resize((IMG_MAX_LARGURA, round(im.height * IMG_MAX_LARGURA / im.width)), Image.LANCZOS)
        saida = destino / (f.stem + ".jpg")
        im.save(saida, "JPEG", quality=IMG_QUALIDADE, optimize=True, progressive=True)
        depois += saida.stat().st_size
    for r in posts:
        if r.get("imagem"):
            r["imagem_original"] = r["imagem"]
            if tem_pillow:
                r["imagem"] = Path(r["imagem"]).stem + ".jpg"
    if fotos:
        print(f"Fotos: {len(fotos)} em img/ ({antes // 1024} KB -> {depois // 1024} KB)")


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


def gerar_card(titulo, resumo, linha_meta, destino, foto=None, doce=False):
    """Cria uma imagem 1200x630 (ideal para WhatsApp, Facebook, X) em JPEG leve, estilo Orkut."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    W, H = 1200, 630
    fonts = STATIC / "fonts"
    fundo, painel, rosa, azul, tinta, suave = (214, 224, 242), (255, 255, 255), (214, 51, 138), (75, 100, 160), (43, 47, 58), (91, 103, 133)
    img = Image.new("RGB", (W, H), fundo)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 22, H), fill=rosa)
    d.rectangle((22, 0, W, 14), fill=azul)

    def fonte(arq, tam):
        return ImageFont.truetype(str(fonts / arq), tam)

    # marca: ícone + "cozinha" "crocante" em minúsculas (Comfortaa Bold), canto superior esquerdo
    icone = Image.open(STATIC / "logo.png").convert("RGBA")
    ih = 64
    icone = icone.resize((round(icone.width * ih / icone.height), ih), Image.LANCZOS)
    img.paste(icone, (70, 40), icone)
    marca = fonte("Comfortaa[wght].ttf", 42)
    marca.set_variation_by_axes([700])
    x = 70 + icone.width + 14
    prim, seg = NOME.lower().split(" ", 1) if " " in NOME else (NOME.lower(), "")
    d.text((x, 72), prim, font=marca, fill=azul, anchor="lm")
    d.text((x + d.textlength(prim + " ", font=marca), 72), seg, font=marca, fill=rosa, anchor="lm")

    # coluna do texto (mais estreita quando há foto)
    esq, dir_ = 70, (640 if foto else W - 70)
    larg = dir_ - esq
    titulo = re.sub(r"\s*[—–-]\s*" + re.escape(NOME) + r"\s*$", "", titulo, flags=re.I)
    for tam in (66, 58, 50, 44):
        ft = fonte("DejaVuSerif-Bold.ttf", tam)
        linhas = _quebrar(d, titulo, ft, larg)
        if len(linhas) <= 3:
            break
    y = 150
    for ln in linhas:
        d.text((esq, y), ln, font=ft, fill=tinta)
        y += int(tam * 1.2)
    y += 8
    d.line((esq, y, dir_, y), fill=(191, 208, 234), width=2)
    y += 18
    fr = fonte("DejaVuSans.ttf", 26)
    for ln in _quebrar(d, resumo, fr, larg)[:3 if len(linhas) < 3 else 2]:
        d.text((esq, y), ln, font=fr, fill=suave)
        y += 36
    y += 14
    if linha_meta and not foto:
        d.text((esq, y), linha_meta, font=fonte("DejaVuSans-Bold.ttf", 28), fill=azul)

    # botão CTA
    fb = fonte("DejaVuSans-Bold.ttf", 30)
    rot = "FAÇA AGORA MESMO!"
    bw, bh = int(d.textlength(rot, font=fb)) + 64, 64
    by = H - 50 - bh
    # salgadas: fundo rosa e sombra azul; doces: cores invertidas
    c_fundo, c_sombra = (azul, rosa) if doce else (rosa, azul)
    d.rectangle((esq + 5, by + 5, esq + bw + 5, by + bh + 5), fill=c_sombra)
    d.rectangle((esq, by, esq + bw, by + bh), fill=c_fundo)
    d.text((esq + bw / 2, by + bh / 2), rot, font=fb, fill=(255, 255, 255), anchor="mm")

    # foto da receita recortada, com moldura deslocada; sem foto, sem painel
    if foto:
        fw, fh = 440, 400
        fx, fy = W - 70 - fw - 10, 85
        d.rectangle((fx + 14, fy + 14, fx + fw + 14, fy + fh + 14), fill=rosa)
        d.rectangle((fx - 4, fy - 4, fx + fw + 4, fy + fh + 4), fill=painel)
        img.paste(ImageOps.fit(Image.open(foto).convert("RGB"), (fw, fh), Image.LANCZOS), (fx, fy))
        if linha_meta:  # tempo e rendimento embaixo da foto, alinhados à direita
            d.text((fx + fw, fy + fh + 50), linha_meta, font=fonte("DejaVuSans-Bold.ttf", 28), fill=azul, anchor="ra")
    destino.parent.mkdir(parents=True, exist_ok=True)
    # orçamento de ~25 KB por imagem (todas juntas ficam abaixo de 1 MB): baixa a qualidade até caber
    import io
    for q in range(80, 24, -5):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= 25 * 1000:
            break
    destino.write_bytes(buf.getvalue())


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
    if CTX.get("jogo"):
        menu += f'<li><a href="{url("/palavra-do-dia/")}"><i class="fa-solid fa-spell-check" aria-hidden="true"></i> <span>Jogo palavra do dia</span></a></li>'
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


def palavra_do_dia(posts, d):
    """Receita cuja palavra vale hoje. Sorteio determinístico pela data, entre as receitas publicadas
    com 'palavra'; não repete a de ontem. None se houver menos de 2 candidatas."""
    cands = sorted((r for r in posts if r.get("palavra")), key=lambda r: r["slug"])
    if len(cands) < 2:
        return None

    def embaralhar(dia):
        ordem = list(cands)
        random.Random("jogo-" + dia.isoformat()).shuffle(ordem)
        return ordem

    ontem = embaralhar(d - datetime.timedelta(days=1))[0]
    ordem = embaralhar(d)
    if ordem[0]["slug"] == ontem["slug"]:
        ordem.append(ordem.pop(0))
    return ordem[0]


def dados_jogo(r, d):
    """conteúdo de jogo.json: só a palavra de hoje (nenhuma outra palavra é publicada)"""
    n = len(normalizar_palavra(r["palavra"]))
    return {
        "data": d.isoformat(),
        "palavra": r["palavra"].lower(),
        "tamanho": n,
        "slug": r["slug"],
        "titulo": r["titulo"],
        "dicionario": url(f"/dicionario/{n}.txt") + "?v=" + hash_arquivo(DICIONARIO / f"{n}.txt"),
    }


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
           og_alt="", jsonld=None, noindex=False, jogo_pagina=False, js_extra=""):
    canonical = url_abs(caminho)
    css = f"{url('/assets/style.css')}?v={hash_arquivo(STATIC / 'style.css')}"
    js = f"{url('/assets/app.js')}?v={hash_arquivo(STATIC / 'app.js')}"
    og_image = og_image or url_abs("/og/site.jpg")
    dim = '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">' if og_dim else ""
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in (jsonld or []))
    nav = "".join(f'<a href="{url("/categoria/" + s + "/")}">{n}</a>' for (n, s, _, _) in CATEGORIAS.values())
    if CTX.get("jogo"):
        nav += f'<a href="{url("/palavra-do-dia/")}">Palavra do dia</a>'
    esq = "" if jogo_pagina else f'<aside class="col-esq">\n{lateral_esq()}\n</aside>'
    direita = "" if jogo_pagina else f'<aside class="col-dir">\n{lateral_dir()}\n</aside>'
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
<body class="{'pagina-jogo' if jogo_pagina else ''}">
<header class="top">
  <div class="wrap">
    <a class="logo" href="{url('/')}"><img class="logo-img" src="{url('/assets/logo.png')}?v={hash_arquivo(STATIC / 'logo.png')}" alt="" width="30" height="34"><span>cozinha<b>crocante</b></span></a>
    <nav aria-label="Categorias">{nav}</nav>
  </div>
</header>

<div class="wrap layout{' so-meio' if jogo_pagina else ''}">
<main class="col-meio">
{corpo}
</main>
{esq}
{direita}
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
{js_extra}</body>
</html>
"""


TECLAS_JOGO = ["qwertyuiop", "asdfghjklç", "zxcvbnm"]


def pagina_jogo(jogo):
    n = jogo["tamanho"]
    grade = "".join(
        '<div class="linha">' + "".join('<span class="celula" aria-hidden="true"></span>' for _ in range(n)) + "</div>"
        for _ in range(6))
    linhas = []
    for i, linha in enumerate(TECLAS_JOGO):
        teclas = "".join(f'<button type="button" class="tecla" data-tecla="{c}">{c.upper()}</button>' for c in linha)
        if i == 0:
            teclas += '<button type="button" class="tecla larga" data-acao="apagar" aria-label="Apagar">⌫</button>'
        if i == 2:
            teclas += '<button type="button" class="tecla larga" data-acao="enter">Enter</button>'
        linhas.append(f'<div class="teclado-linha">{teclas}</div>')
    corpo = f"""<section class="box hero">
  <div class="box-h jogo-topo"><h2>jogo palavra do dia</h2>
    <button type="button" class="ajuda-btn" id="ajuda-abrir" aria-label="Como jogar" aria-haspopup="dialog">?</button></div>
  <div class="box-c jogo" id="jogo" style="--colunas:{n}">
    <p class="jogo-aviso" id="jogo-aviso" aria-live="polite"></p>
    <div class="grade" id="grade" role="table" aria-label="Tentativas">{grade}</div>
    <div class="teclado" id="teclado" aria-label="Teclado">{"".join(linhas)}</div>
    <div class="jogo-fim" id="jogo-fim" aria-live="polite" hidden></div>
    <noscript><p>O jogo precisa de JavaScript para funcionar.</p></noscript>
  </div>
</section>
<dialog class="ajuda-modal" id="ajuda" aria-labelledby="ajuda-titulo">
  <h2 id="ajuda-titulo">Como jogar</h2>
  <p>Descubra a palavra do dia, de <b>{n} letras</b>, em até <b>6 tentativas</b>. Só valem palavras que existem (acento não faz diferença).</p>
  <ul class="ajuda-dicas">
    <li><span class="amostra certa" aria-hidden="true">&#10003;</span> <b>Verde:</b> a letra está na palavra e no lugar certo.</li>
    <li><span class="amostra presente" aria-hidden="true">&#9680;</span> <b>Amarelo:</b> a letra está na palavra, mas em outro lugar.</li>
    <li><span class="amostra ausente" aria-hidden="true">&#10005;</span> <b>Cinza:</b> a letra não está na palavra.</li>
  </ul>
  <p>No fim da partida, você vê a palavra e a receita do blog ligada a ela. Volte amanhã para uma palavra nova.</p>
  <form method="dialog"><button class="ajuda-fechar">Entendi</button></form>
</dialog>"""
    return pagina(titulo=f"Jogo da palavra do dia — {NOME}",
                  descricao=f"Descubra a palavra do dia, de {n} letras, em 6 tentativas. No fim, uma receita do {NOME} ligada à palavra.",
                  caminho="/palavra-do-dia/", corpo=corpo, jogo_pagina=True,
                  js_extra=f'<script src="{url("/assets/jogo.js")}?v={hash_arquivo(STATIC / "jogo.js")}" defer></script>\n')


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

{b}/jogo.json
  Cache-Control: public, max-age=0, must-revalidate

{b}/dicionario/*
  Cache-Control: public, max-age=31536000, immutable

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
    if DICIONARIO.exists():   # dicionário do jogo: só os arquivos de palavras, em /dicionario/
        shutil.copytree(DICIONARIO, DIST / "dicionario")

    # imagens de compartilhamento
    try:
        import PIL  # noqa: F401
        tem_pillow = True
    except ImportError:
        tem_pillow = False
        avisos.append("Pillow não instalado: imagens de compartilhamento não foram geradas (pip install pillow)")
    otimizar_imagens(posts, tem_pillow)
    og_site = url_abs("/og/site.jpg")
    if tem_pillow:
        gerar_card(NOME, SITE.get("slogan", ""), "", DIST / "og" / "site.jpg")

    CTX["posts"] = posts
    d_jogo = hoje()
    escolhida = palavra_do_dia(posts, d_jogo)
    jogo = dados_jogo(escolhida, d_jogo) if escolhida else None
    CTX["jogo"] = jogo

    # páginas das receitas
    for r in posts:
        if r.get("imagem") and not tem_pillow:
            og = url_abs("/img/" + r["imagem"])
        elif tem_pillow:
            fundo = ROOT / "img" / r["imagem_original"] if r.get("imagem") else None
            gerar_card(r["titulo"], r["resumo"], f"{r['tempo']}   •   {r['porcoes']}", DIST / "og" / f"{r['slug']}.jpg", fundo, "doce" in r["tags"])
            og = url_abs(f"/og/{r['slug']}.jpg")
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

    # jogo da palavra do dia (só se houver ao menos 2 palavras)
    if jogo:
        escrever("jogo.json", json.dumps(jogo, ensure_ascii=False, separators=(",", ":")))
        escrever("palavra-do-dia/index.html", pagina_jogo(jogo))

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
    if jogo:
        urls.append(("/palavra-do-dia/", d_jogo.isoformat()))
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
