#!/usr/bin/env python3
"""
Dicionário do jogo da palavra do dia (static/dicionario/<n>.txt, n = 4 a 10).

Uso:
  python3 scripts/dicionario.py regenerar    # baixa fserb/pt-br (precisa de rede) e recria os 7 arquivos
  python3 scripts/dicionario.py sincronizar  # offline: acrescenta as palavras de posts.json que faltam

Origem: https://github.com/fserb/pt-br (licença MIT, ver static/dicionario/LICENSE-pt-br.txt).
Só usa a biblioteca padrão do Python.
"""
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "static" / "dicionario"
POSTS = ROOT / "posts.json"

ORIGEM = "https://raw.githubusercontent.com/fserb/pt-br/master/"
ARQUIVOS_ORIGEM = ["lexico", "conjugações", "icf"]
ICF_MAX = 18.0                      # corte de raridade escolhido: palavras acima disso saem
TAMANHOS = range(4, 11)
FORMA = re.compile(r"^[a-z]{4,10}$")


def normalizar(s):
    """minúsculas, sem acento, sem espaços nas bordas"""
    s = unicodedata.normalize("NFD", s.strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def baixar(nome):
    url = ORIGEM + urllib.parse.quote(nome)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8").splitlines()


def formas_regulares(verbete):
    """plurais e femininos regulares de um verbete (sem acento)"""
    w = verbete
    if len(w) < 3 or not w.isalpha():
        return set()
    out = {w + "s"}
    if w[-1] in "rzsl":
        out.add(w + "es")
    if w.endswith("o"):
        out.update({w[:-1] + "a", w[:-1] + "os", w[:-1] + "as"})
    if w.endswith("e"):
        out.add(w + "s")
    if w.endswith("a"):
        out.add(w + "s")
    return out


def palavras_receitas():
    """palavra de cada receita (normalizada), se houver"""
    if not POSTS.exists():
        return set()
    posts = json.loads(POSTS.read_text("utf-8"))
    return {normalizar(r["palavra"]) for r in posts if r.get("palavra")}


def ler_arquivo(n):
    p = DIR / f"{n}.txt"
    if not p.exists():
        return set()
    return {l for l in p.read_text("utf-8").splitlines() if l}


def escrever_arquivo(n, palavras):
    DIR.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(sorted(palavras)) + "\n"
    (DIR / f"{n}.txt").write_text(texto, "utf-8")


def regenerar():
    lexico_bruto = baixar("lexico")
    conj_bruto = baixar("conjugações")
    icf_bruto = baixar("icf")

    lexico = {normalizar(l) for l in lexico_bruto if l.strip()}
    base = set(lexico)
    base.update(normalizar(l) for l in conj_bruto if l.strip())
    for l in icf_bruto:
        if "," not in l:
            continue
        palavra, score = l.rsplit(",", 1)
        try:
            if float(score) <= ICF_MAX:
                base.add(normalizar(palavra))
        except ValueError:
            continue
    for v in list(lexico):
        base.update(formas_regulares(v))
    base |= palavras_receitas()

    for n in TAMANHOS:
        escrever_arquivo(n, {w for w in base if len(w) == n and FORMA.match(w)})
        print(f"{n}.txt: {len(ler_arquivo(n))} palavras")


def sincronizar():
    faltam = []
    for palavra in sorted(palavras_receitas()):
        if not FORMA.match(palavra):
            print(f"ERRO: '{palavra}' tem tamanho ou caracteres fora do permitido (4 a 10, a-z)")
            sys.exit(1)
        n = len(palavra)
        atual = ler_arquivo(n)
        if palavra not in atual:
            atual.add(palavra)
            escrever_arquivo(n, atual)
            faltam.append(f"{palavra} -> {n}.txt")
    if faltam:
        print("Acrescentadas:\n  " + "\n  ".join(faltam))
    else:
        print("Nada a acrescentar: todas as palavras das receitas já estão no dicionário.")


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "regenerar":
        regenerar()
    elif modo == "sincronizar":
        sincronizar()
    else:
        print(__doc__)
        sys.exit(2)
