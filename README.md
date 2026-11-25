# Cozinha Crocante

Blog de receitas rápidas (air fryer e frigideira), publicado no GitHub Pages.

As receitas ficam em **`posts.json`**. O script `build.py` transforma esse arquivo em um site estático
(uma página HTML por receita, com URL amigável e prévia para redes sociais) na pasta `dist/`.
O GitHub Actions roda o build e publica o site automaticamente a cada `git push`.

## Por que gerar páginas em vez de montar tudo no navegador?

WhatsApp, Facebook, X, Pinterest e o Google **não executam JavaScript** ao ler um link.
Se a receita fosse montada no navegador a partir do JSON, o link compartilhado não teria título,
descrição nem imagem. Por isso cada receita vira um HTML pronto, com Open Graph, JSON-LD de receita
(rich results do Google), `sitemap.xml` e imagem de compartilhamento (1200×630) própria.
A busca por ingredientes continua no navegador, lendo `busca.json` (índice leve gerado do `posts.json`).

## Estrutura

```
posts.json          receitas (fonte única). É o único arquivo que você edita no dia a dia
affiliates.json     links de afiliado por produto (por ora só Mercado Livre)
site.json           nome, domínio (url) e base do site
build.py            gerador do site
static/             CSS, JS, favicon e fontes usadas nas imagens de compartilhamento
img/                fotos das receitas (opcional)
.github/workflows/  publicação automática (GitHub Pages ou Cloudflare Pages)
scripts/            purge_cloudflare.py: limpa o cache do Cloudflare depois de cada deploy
dist/               saída do build (não vai para o Git)
```

URLs geradas:

- `/` home · `/categoria/air-fryer/` · `/categoria/frigideira/` · `/categoria/salgados/` · `/categoria/sobremesas/`
- `/receitas/<slug>/` cada receita (o `slug` do `posts.json` é a URL)
- `/og/<slug>.jpg` imagem de compartilhamento · `/sitemap.xml` · `/robots.txt` · `/404.html`

## Publicar pela primeira vez

1. Crie um repositório no GitHub (público; Pages em repositório privado exige plano pago) e envie estes arquivos:
   ```bash
   git init && git add . && git commit -m "Cozinha Crocante"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
   git push -u origin main
   ```
2. No GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Aguarde o workflow **Publicar no GitHub Pages** (aba Actions). O site abre em
   `https://SEU_USUARIO.github.io/SEU_REPOSITORIO/`.

> Enquanto você usa o endereço `github.io/SEU_REPOSITORIO/` (sem domínio próprio), ajuste o `site.json`:
> `"url": "https://SEU_USUARIO.github.io"` e `"base": "/SEU_REPOSITORIO"`.

## Domínio próprio

1. Compre o domínio e ajuste o `site.json`: `"url": "https://SEUDOMINIO.com.br"` e `"base": ""`.
   O build cria o arquivo `CNAME` sozinho.
2. No painel do domínio, crie os registros DNS conforme a documentação do GitHub
   (https://docs.github.com/pages/configuring-a-custom-domain-for-your-github-pages-site):
   registros **A** do domínio raiz apontando para os IPs do GitHub Pages
   (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153) e um **CNAME** de `www`
   para `SEU_USUARIO.github.io`.
3. No GitHub: **Settings → Pages → Custom domain**, informe o domínio e marque **Enforce HTTPS**
   quando liberar (pode levar alguns minutos).

O `site.json` é o que define as URLs canônicas, o sitemap e as imagens de compartilhamento.
Se ele estiver com um domínio diferente do real, os links compartilhados apontam para o lugar errado.

## Adicionar uma receita

Acrescente um objeto no fim de `posts.json` e faça o push. Campos:

| campo | exemplo / regra |
|---|---|
| `slug` | `"cuscuz-na-frigideira"`: vira `/receitas/cuscuz-na-frigideira/`. Só minúsculas, números e hífens. Não mude depois de publicar. |
| `publicado` | `"2026-11-14"`. Se for data futura, a receita só entra no site nesse dia (o workflow roda todo dia às 07h). |
| `titulo`, `resumo` | título e descrição (o resumo aparece na prévia das redes e no Google) |
| `emoji`, `cor` | ilustração do card, `"#RRGGBB"` claro, e também a cor da imagem de compartilhamento |
| `tags` | `airfryer` ou `frigideira`, mais `salgado` ou `doce` |
| `tempo`, `porcoes`, `nivel` | `"25 min"` (ou `"1 h 10 min"`), `"4 porções"`, `"Fácil"` |
| `chave` | ingredientes que contam na busca. Use `a\|b` para alternativas: `"mel\|açúcar mascavo"` |
| `opc` | ingredientes opcionais (não contam na busca) |
| `ingredientes`, `passos`, `dica` | texto da receita |
| `produtos` | utensílios: `{ "nome", "nota", "busca" }`. `busca` é a chave em `affiliates.json` |
| `imagem` | (opcional) arquivo em `img/`, por exemplo `"frango.jpg"`. Passa a ser a foto do card e da prévia nas redes |
| `video` | (opcional) `{ "url": "...", "canal": "..." }` link para o vídeo original no YouTube |
| `palavra` | (opcional) palavra do jogo da palavra do dia: 4 a 10 letras, sem espaço ou hífen, única entre as receitas e presente no dicionário (`static/dicionario/<tamanho>.txt`). Receita sem `palavra` fica fora do jogo |

Para conferir os dados sem gerar nada: `python3 build.py --check`. O build para com mensagem clara se algo estiver errado.

## Jogo da palavra do dia

A página `/jogo/` sorteia uma palavra por dia entre as receitas publicadas com `palavra`. A palavra não repete a do dia anterior, e ao acertar ou errar o jogo mostra um link para a receita ligada a ela. Com menos de 2 receitas com `palavra`, o jogo não é gerado.

- Só são aceitas tentativas que existem no dicionário. Palavra inexistente é recusada e não gasta tentativa.
- O dicionário fica no repositório, em `static/dicionario/4.txt` a `10.txt`, um arquivo por tamanho. O site não depende de serviços externos.
- Se `python3 build.py --check` disser que a `palavra` de uma receita não está no dicionário, rode `python3 scripts/dicionario.py sincronizar` e faça commit do resultado.
- `python3 scripts/dicionario.py regenerar` recria os 7 arquivos a partir da lista [fserb/pt-br](https://github.com/fserb/pt-br) (licença MIT, ver `static/dicionario/LICENSE-pt-br.txt`). Precisa de internet e só é preciso para atualizar a base.
- Mudar `palavra` ou adicionar receitas no mesmo dia pode trocar a palavra de hoje.

## Links de afiliado

Em `affiliates.json`, cada produto tem o campo `ml`. Cole o link gerado no programa de afiliados do Mercado Livre.
Campo vazio = botão leva para uma busca comum na loja (sem comissão). O build lista no final os produtos sem nenhum link.

## Testar no seu computador

```bash
pip install pillow
python3 build.py
python3 -m http.server 8000 -d dist
# abra http://localhost:8000
```

Se o `site.json` tiver `base` diferente de vazio, use `BASE_PATH= python3 build.py` para testar na raiz.

## Fotos e imagem de compartilhamento

Sem foto, o build gera para cada receita uma imagem 1200×630 com título, tempo e porções.
Com foto própria (`"imagem": "arquivo.jpg"` + arquivo em `img/`), a foto vira o fundo da imagem de compartilhamento (recortada em 1200×630, com degradê escuro para o texto branco ficar legível). Use uma imagem horizontal de pelo menos 1200×630.
Fotos reais aumentam muito o clique nas redes e ajudam a receita a aparecer com destaque no Google.

## CDN e cache (Cloudflare)

O GitHub Pages já usa um CDN, mas sempre responde com `Cache-Control: max-age=600` e não dá para mudar isso.
Para ter controle do cache (e uma CDN própria, gratuita), há dois caminhos. A escolha é a variável
`DEPLOY_TARGET` do repositório (**Settings → Secrets and variables → Actions → Variables**).

| | A) GitHub Pages + Cloudflare na frente | B) Cloudflare Pages |
|---|---|---|
| `DEPLOY_TARGET` | não definir (ou `github`) | `cloudflare` |
| Onde o site fica | GitHub Pages; o Cloudflare só faz cache e DNS | Cloudflare (hospedagem e CDN juntos) |
| Cache após novo post | o workflow limpa o cache do Cloudflare sozinho | cada deploy substitui tudo, sem limpar nada |
| Cabeçalhos de cache | só pelas Cache Rules do painel | arquivo `_headers` gerado pelo build |
| HTTPS | frágil: ver "pegadinhas" abaixo | automático |
| Custo | $0 | $0 |

**Recomendação:** o caminho B é mais simples e mais robusto (menos peças, sem problema de certificado, sem purge).
O caminho A vale se você quiser manter tudo no GitHub Pages.

### Passo comum: colocar o domínio no Cloudflare

1. Crie uma conta gratuita em cloudflare.com e use **Add a site** com o seu domínio (plano Free).
2. No registrador do domínio (por exemplo o Registro.br para `.com.br`), troque os servidores DNS (nameservers) pelos dois que o Cloudflare indicar.
   O Cloudflare Registrar vende domínios a preço de custo, mas confira em cloudflare.com/tld-policies se ele aceita a sua extensão.

### Caminho A: GitHub Pages + Cloudflare

1. **DNS**: crie os registros do GitHub Pages (seção "Domínio próprio" acima) no Cloudflare, primeiro com a nuvem **cinza** (DNS only).
   Em **Settings → Pages** do GitHub informe o domínio e espere o certificado HTTPS. Só depois ligue o proxy (nuvem **laranja**).
2. **SSL/TLS** (no Cloudflare): modo **Full** (não "Full (strict)") e ative **Always Use HTTPS**.
   O GitHub não emite nem renova o certificado quando o proxy está ligado; em "strict" o site pode sair do ar quando o certificado vencer.
3. **Cache Rules** (Caching → Cache Rules). O Cloudflare não guarda HTML nem JSON por padrão, então são necessárias estas regras
   (as condições não se sobrepõem, de propósito):

   | Regra | Quando (expressão) | Cache | Edge TTL | Browser TTL |
   |---|---|---|---|---|
   | version | `http.request.uri.path eq "/version.json"` | Bypass cache | | |
   | assets | `starts_with(http.request.uri.path, "/assets/")` | Eligible for cache | 1 mês | 1 ano |
   | imagens | `starts_with(http.request.uri.path, "/og/") or starts_with(http.request.uri.path, "/img/")` | Eligible for cache | 1 mês | 1 dia |
   | páginas | `not starts_with(http.request.uri.path, "/assets/") and not starts_with(http.request.uri.path, "/og/") and not starts_with(http.request.uri.path, "/img/") and http.request.uri.path ne "/version.json"` | Eligible for cache | 1 dia (ignorar o cache-control da origem) | 5 minutos |

   Os arquivos de `/assets/` têm `?v=<hash>` na URL (o build muda o hash quando o arquivo muda), por isso podem ficar um ano no cache.
   O Edge TTL de 1 dia nas páginas é só uma rede de segurança: o normal é o workflow limpar o cache a cada deploy.
4. **Token e IDs**: no Cloudflare, **My Profile → API Tokens → Create Token → Custom**, com a permissão
   **Zone → Cache Purge → Purge** restrita ao seu domínio. O **Zone ID** está na página Overview do domínio.
5. No GitHub (**Settings → Secrets and variables → Actions**): secret `CLOUDFLARE_API_TOKEN` e variável `CLOUDFLARE_ZONE_ID`.

Pronto: a cada push (e na execução diária das 07h) o workflow publica no GitHub Pages, espera o build novo aparecer, limpa o cache do
Cloudflare, confere a página inicial e repete se ainda estiver velha (`scripts/purge_cloudflare.py`). Sem `CLOUDFLARE_ZONE_ID`, esse passo é ignorado.

### Caminho B: Cloudflare Pages

1. No Cloudflare: **Workers & Pages → Create → Pages → Upload assets**, crie um projeto vazio (por exemplo `cozinha-crocante`)
   e, no projeto, **Custom domains** para ligar o seu domínio (com o domínio no Cloudflare, o DNS e o HTTPS são automáticos).
2. Crie um token em **My Profile → API Tokens** com a permissão **Account → Cloudflare Pages → Edit**. Anote também o **Account ID**.
3. No GitHub: secrets `CLOUDFLARE_API_TOKEN` e `CLOUDFLARE_ACCOUNT_ID`; variáveis `DEPLOY_TARGET` = `cloudflare` e `CLOUDFLARE_PAGES_PROJECT` = nome do projeto.
4. Faça um push. O build roda no GitHub Actions (com `DEPLOY_TARGET=cloudflare`, que gera o `_headers`) e o resultado é enviado ao Cloudflare.
   O GitHub Pages pode ser desligado (Settings → Pages).

Limites do plano gratuito do Cloudflare Pages: largura de banda e requisições estáticas ilimitadas, até 20.000 arquivos por deploy e 25 MiB por arquivo.

### Como conferir se o cache está funcionando

```bash
curl -sI https://SEUDOMINIO.com.br/ | grep -iE "cf-cache-status|^age|cache-control"
```

- `cf-cache-status: HIT` = veio do cache do Cloudflare; `MISS` = foi buscar na origem (esperado na primeira vez e logo após um deploy).
- `DYNAMIC` nas páginas HTML = a regra "páginas" não está valendo (revise a expressão).

### Pegadinhas

- Se o purge falhar, as páginas ficam velhas até o Edge TTL (1 dia). Rode o workflow de novo (**Actions → Run workflow**) ou limpe manualmente em **Caching → Configuration → Purge Everything**.
- O limite do plano gratuito para purge é de 5 requisições por minuto; o script usa poucas por deploy.
- WhatsApp, Facebook e X guardam a prévia de cada link por conta própria. Se mudar título ou imagem de uma receita já compartilhada, renove a prévia no Sharing Debugger do Facebook.
- Nunca ponha `/version.json` em cache: o script usa esse arquivo para saber se o deploy novo já está no ar.

## Observações

- As fontes em `static/fonts/` (DejaVu) são usadas só para desenhar as imagens de compartilhamento; licença livre.
- Com centenas de receitas, a home deve ganhar paginação. O gerador está pronto para receber essa mudança.
- Páginas de política de privacidade e consentimento de cookies serão necessárias se você ativar anúncios ou ferramentas de análise.
