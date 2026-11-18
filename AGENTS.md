# Cozinha Crocante

Blog de receitas rápidas (air fryer e frigideira), monetizado com afiliados.

## Stack e deploy
- Site estático, receitas renderizadas a partir de `posts.json`
- Deploy no Cloudflare Pages via GitHub Actions (push na `main` publica)
- Cada receita precisa de URL amigável (slug) para compartilhar

## Regras
- Responda sempre em português do Brasil
- Receitas: título, tempo, ingredientes, modo de preparo, link de afiliado quando houver
- Nunca remova links de afiliado existentes
- Antes de alterar a estrutura do `posts.json`, mostre o que vai mudar
- Sempre crie uma branch nova a partir da main atualizada.
- Sempre faça commits utilizando o padrão commitizen

## Ambiente
- Windows 11 + WSL (Ubuntu); rode comandos no WSL

## Visão geral

Blog de receitas em português (Cozinha Crocante): gerador de site estático em Python, sem framework. O conteúdo e a interface estão em pt-BR; mantenha esse idioma em textos, mensagens e comentários. O README.md tem a documentação completa de publicação, domínio e Cloudflare.

## Comandos

```bash
python3 build.py --check          # valida posts.json/affiliates.json sem gerar nada (não há suíte de testes nem linter)
pip install pillow                # só necessário para as imagens de compartilhamento (sem Pillow o build avisa e segue)
python3 build.py                  # gera dist/
python3 -m http.server 8000 -d dist
BASE_PATH= python3 build.py       # testa na raiz quando site.json tem "base" diferente de vazio
```

Variáveis de ambiente do build: `SITE_URL`, `BASE_PATH`, `BUILD_DATE` (AAAA-MM-DD, simula outra data para testar receitas agendadas), `BUILD_ID`, `DEPLOY_TARGET` (`github` ou `cloudflare`, esta gera `_headers`).

## Arquitetura

Tudo é gerado por [build.py](build.py) (um único arquivo, sem templates externos: o HTML é montado com f-strings em `pagina()`, `pagina_receita()`, `card()`, etc.). Entradas:

- `posts.json`: fonte única das receitas. `carregar_posts()` valida o schema (campos obrigatórios, slug, cor `#RRGGBB`, tags em `CATEGORIAS`, formato de `tempo`) e aborta com erro. Receitas com `publicado` futuro são filtradas; o workflow roda todo dia às 07h para publicá-las.
- `affiliates.json`: mapa `produto -> {ml: link}`; o campo `busca` de cada produto da receita é a chave. Sem link, cai para uma busca no Mercado Livre (`LOJAS`) sem `rel="sponsored"`.
- `site.json`: nome, `url`, `base`, slogan, cor. Define URLs canônicas, sitemap e imagens OG; `CNAME` é gerado a partir dele.
- `static/` é copiado para `dist/assets/` e referenciado com `?v=<md5>` (`hash_arquivo`), por isso pode ter cache longo. `static/fonts/` (DejaVu) é só para as imagens OG. `img/` (fotos opcionais) vai para `dist/img/`.

Pontos que exigem ler mais de um lugar:

- **Páginas pré-renderizadas por SEO/redes sociais**: crawlers não rodam JS, então cada receita é HTML completo com Open Graph, JSON-LD (Recipe, BreadcrumbList) e uma imagem 1200×630 própria (`gerar_card`). Não mova a renderização para o navegador.
- **Busca por ingredientes** é client-side: `build.py` escreve `dist/busca.json` (campos `chave`, `opc` etc.) e [static/app.js](static/app.js) o consome. A gaveta de busca (`GAVETA`) é HTML do build; `TEMPEROS` conta como ingrediente já disponível. Mudou campos do índice ou ids/classes da gaveta → ajuste `app.js` e `style.css` juntos.
- **Sintaxe de `chave`**: `"a|b"` significa alternativas; `relacionadas()` e o JSON-LD também usam `chave`.
- **`BASE` vs. `url()`/`url_abs()`**: todo link interno deve passar por `url()` (e links canônicos por `url_abs()`) para funcionar com site em subcaminho do github.io.
- **Layout de três colunas** (`lateral_esq`/`lateral_dir`) usa `CTX["posts"]`, preenchido em `main()` antes de renderizar; "sorte do dia" e "recados" variam com a data do build.

## Deploy

[.github/workflows/pages.yml](.github/workflows/pages.yml) faz o build e publica (GitHub Pages por padrão, Cloudflare Pages se a variável `DEPLOY_TARGET=cloudflare`). [scripts/purge_cloudflare.py](scripts/purge_cloudflare.py) limpa o cache do Cloudflare e confere `/version.json` (nunca deve ser cacheado). `dist/` e `__pycache__/` não vão para o Git.

## Convenções

- Não altere o `slug` de receitas já publicadas (é a URL).
- Para adicionar receita, basta um novo objeto em `posts.json`; rode `python3 build.py --check` antes do push.
- Só Mercado Livre é usado como loja de afiliados; novas lojas entram em `LOJAS` e em `affiliates.json`.