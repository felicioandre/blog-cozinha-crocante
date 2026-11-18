#!/usr/bin/env python3
"""
Limpa o cache do Cloudflare depois de um deploy no GitHub Pages.

Por que não simplesmente chamar a API de purge logo depois do deploy?
O GitHub Pages leva um tempo para publicar e tem cache próprio. Se o Cloudflare for limpo
cedo demais, ele busca a versão ANTIGA na origem e guarda de novo. Por isso o script:

  1. espera /version.json (com um parâmetro único, que ignora caches) mostrar o build novo;
  2. manda o Cloudflare limpar o cache (purge everything);
  3. confere se a página inicial, pelo endereço normal, já mostra o build novo.
     Se ainda estiver velha, espera, limpa de novo e confere outra vez.

Variáveis de ambiente:
  SITE_URL, BASE_PATH      site publicado (ex.: https://cozinhacrocante.com e "")
  BUILD_ID                 id do build atual (o mesmo usado no build.py)
  CLOUDFLARE_ZONE_ID       ID da zona (Overview do domínio, no painel do Cloudflare)
  CLOUDFLARE_API_TOKEN     token com permissão Zone > Cache Purge > Purge
  Opcionais: CLOUDFLARE_API_BASE, PURGE_ESPERA_ORIGEM (tentativas), PURGE_INTERVALO (segundos),
             PURGE_RODADAS (máximo de purges)
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SITE = os.environ["SITE_URL"].rstrip("/") + os.environ.get("BASE_PATH", "").rstrip("/")
BUILD = os.environ["BUILD_ID"]
ZONE = os.environ["CLOUDFLARE_ZONE_ID"]
TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
API = os.environ.get("CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4").rstrip("/")
TENTATIVAS_ORIGEM = int(os.environ.get("PURGE_ESPERA_ORIGEM", "30"))
INTERVALO = float(os.environ.get("PURGE_INTERVALO", "10"))
RODADAS = int(os.environ.get("PURGE_RODADAS", "6"))
UA = "cozinha-crocante-deploy"


def get(url, **headers):
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def build_publicado_na_origem(i):
    try:
        return json.loads(get(f"{SITE}/version.json?cb={BUILD}-{i}")).get("build")
    except Exception as e:
        print(f"  (tentativa {i}: {type(e).__name__}: {e})")
        return None


def build_da_home():
    try:
        m = re.search(r'<meta name="build-id" content="([^"]*)"', get(f"{SITE}/"))
        return m.group(1) if m else None
    except Exception as e:
        print(f"  (home: {type(e).__name__}: {e})")
        return None


def purge():
    req = urllib.request.Request(
        f"{API}/zones/{ZONE}/purge_cache",
        data=json.dumps({"purge_everything": True}).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo = json.load(r)
    except urllib.error.HTTPError as e:
        corpo = {}
        try:
            corpo = json.load(e)
        except Exception:
            pass
        print(f"ERRO: a API do Cloudflare respondeu HTTP {e.code}: {json.dumps(corpo.get('errors', corpo))}")
        print("Confira o CLOUDFLARE_ZONE_ID e se o token tem a permissão Zone > Cache Purge > Purge.")
        sys.exit(1)
    if not corpo.get("success"):
        print("ERRO: purge recusado:", json.dumps(corpo.get("errors", corpo)))
        sys.exit(1)


def main():
    print(f"Site: {SITE} | build esperado: {BUILD}")

    # 1) esperar o deploy aparecer na origem
    for i in range(1, TENTATIVAS_ORIGEM + 1):
        if build_publicado_na_origem(i) == BUILD:
            print(f"Deploy novo visível na origem (tentativa {i}).")
            break
        time.sleep(INTERVALO)
    else:
        print("::warning::O deploy novo não apareceu na origem a tempo; limpando o cache mesmo assim.")

    # 2) e 3) limpar e conferir (repete se a página inicial ainda estiver velha)
    for rodada in range(1, RODADAS + 1):
        purge()
        print(f"Cache do Cloudflare limpo (rodada {rodada}).")
        time.sleep(min(INTERVALO, 5))
        visto = build_da_home()
        if visto == BUILD:
            print("Conferido: a página inicial já mostra o build novo.")
            return
        print(f"A página inicial ainda mostra '{visto}'. Aguardando para limpar de novo.")
        time.sleep(INTERVALO * 3)

    print(f"::warning::Cache limpo {RODADAS}x, mas a página inicial ainda não mostra o build {BUILD}. "
          "Pode ser cache do próprio GitHub Pages (até ~10 min); verifique o site e, se preciso, limpe manualmente.")


if __name__ == "__main__":
    main()
