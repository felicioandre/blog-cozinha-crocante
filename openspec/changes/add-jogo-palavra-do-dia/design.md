# Design

## Context

O site é gerado por um único `build.py`, com HTML em f-strings, e não tem framework nem testes automatizados. Pontos que moldam a solução:

- `escolhas_do_dia()` já faz sorteio determinístico pela data (`random.Random(data.isoformat())`) e o cron diário das 07h de `pages.yml` reconstrói o site. O jogo reaproveita esse mecanismo.
- `busca.json` é um índice gerado no build e lido por `static/app.js`, com `Cache-Control: max-age=0, must-revalidate` no `_headers` do Cloudflare. O `jogo.json` segue o mesmo modelo.
- `carregar_posts()` valida o schema e aborta o build com erro. `obrig` lista os campos obrigatórios; um campo opcional como `imagem` é validado só se existir.
- O build copia para `dist/assets/` só os arquivos soltos de `static/` (`if f.is_file()`); subpastas como `static/fonts/` não são copiadas. O dicionário precisa de cópia recursiva.
- Links internos passam por `url()`/`url_abs()` e o CSS/JS são referenciados com `?v=<md5>`.
- Hoje 37 receitas existem e nenhuma tem `palavra`. A lista [fserb/pt-br](https://github.com/fserb/pt-br) (MIT) tem `lexico` (verbetes, sem plurais nem femininos), `conjugações` e `icf` (palavras de corpus com score de raridade, de 4,4 a 24,7; abaixo de 18 são palavras comuns, acima aparecem muitas raridades e erros de digitação). Medido com cortes de 4 a 10 letras e sem acento: léxico + conjugações + ICF ≤ 18 dão ~206 mil palavras; com plurais e femininos regulares, ~346 mil (~3 MB sem compressão, menos de 1 MB comprimidos nos 7 arquivos).

Ver proposal.md para a motivação.

## Goals / Non-Goals

**Goals:**
- Uma palavra por dia, ligada a uma receita publicada, igual para todas as pessoas.
- Só palavras que existem como tentativa, com dicionário versionado no próprio repositório.
- Jogo 100% no navegador, sem backend, sobre a infraestrutura de site estático atual.
- Não quebrar nenhuma receita existente e não mudar o comportamento de páginas já geradas.

**Non-Goals:**
- Impedir de verdade quem inspeciona o código de ver a palavra de hoje (aceitável para um jogo de blog).
- Dicionário perfeito: pode faltar uma palavra rara ou sobrar uma forma regular que não existe (ver riscos).
- Placar, ranking, compartilhamento e modos além de 6 tentativas.
- Atualização automática do dicionário pela rede: é uma tarefa manual com script.

## Decisions

### 1. Campo opcional `palavra` em `posts.json` (palavra curada, 4 a 10 letras)
Cada receita pode ter `"palavra": "frango"`. É validado em `carregar_posts()` só quando presente: regex `^[a-zà-ú]{4,10}$` sobre o valor em minúsculas, e unicidade comparando a forma normalizada (NFD sem acento, minúscula). A palavra **não** precisa existir na lista de origem, mas precisa estar no dicionário do repositório (decisão 3).

- **Alternativa: derivar de `chave`.** Rejeitada: poucas palavras ligadas ao prato, então o link para a receita ficaria arbitrário.
- **Alternativa: tamanho fixo de 5 letras.** Rejeitada pelo usuário: poucas opções de palavra.
- Sem `palavra` na lista obrigatória: receitas novas continuam publicáveis sem palavra.
- **Mudança de estrutura do `posts.json`:** conforme AGENTS.md, a mudança será mostrada antes de gravar. Para isso a tarefa 3.1 apresenta a lista proposta (slug → palavra) e só grava após aprovação.

### 2. Sorteio no build, só a palavra de hoje em `dist/jogo.json`
Nova função `palavra_do_dia(posts, d)` ao lado de `escolhas_do_dia()`:
- candidatas = receitas visíveis (já filtradas por `publicado`) com `palavra`;
- embaralha com `random.Random("jogo-" + d.isoformat())` e evita repetir a de ontem (mesma técnica de `escolhas_do_dia()`, com o prefixo `jogo-` para não correlacionar com a "sorte do dia").

Saída: `{"data": "AAAA-MM-DD", "palavra": "frango", "tamanho": 6, "slug": "...", "titulo": "..."}` em `dist/jogo.json`, em UTF-8 e com acento preservado. `tamanho` é o comprimento da palavra sem acento.

- **Alternativa: sorteio no navegador com a lista completa.** Rejeitada: entregaria todas as palavras futuras no código.
- **Cobertura:** a data vem de `hoje()` (America/Sao_Paulo), a mesma do resto do site. O cron das 07h BRT já reconstrói; não é preciso mexer em `pages.yml`.
- **Poucas palavras (< 2):** o build avisa, não gera `jogo.json` nem a página `/palavra-do-dia/`, e `lateral_esq()` não mostra o link.

### 3. Dicionário versionado em `static/dicionario/<n>.txt`, um arquivo por tamanho
Sete arquivos (`4.txt` a `10.txt`), uma palavra por linha, minúsculas, a–z sem acento, ordenadas e sem repetição. São "minificados" porque guardam só a palavra normalizada (sem score, acento nem metadados). Ficam no repositório para o build e o site não dependerem do GitHub de origem.

- O navegador baixa **só** `dicionario/<tamanho>.txt` do dia, com `?v=<hash>` calculado pelo build (`hash_arquivo`). Isso limita o download a de 6 a ~260 KB comprimidos por visita, e o arquivo pode ficar em cache longo.
- **Alternativa: um único arquivo com tudo.** Rejeitada: ~900 KB comprimidos para jogar com uma palavra de 5 letras.
- **Alternativa: validar por API externa.** Rejeitada: depende de rede e de terceiros, envia o que a pessoa digita.
- **Alternativa: lista dentro do `jogo.json`.** Rejeitada: o `jogo.json` precisa ser revalidado todo dia, e o dicionário quase nunca muda.
- Em memória, `jogo.js` transforma o arquivo em `Set` na primeira tentativa (ou antes, em segundo plano, logo após carregar o `jogo.json`).
- O `build.py` copia `static/dicionario/` para `dist/dicionario/` (cópia recursiva, só para essa pasta) e referencia cada arquivo com `?v=<hash>`.
- O `_headers` do Cloudflare não precisa de regra própria: o prefixo `/dicionario/` entra com cache longo, como `/assets/*`. Se o dicionário ficar em `/assets/dicionario/`, a regra existente já cobre.

### 4. Origem e geração do dicionário: `scripts/dicionario.py`
Script único, só com a biblioteca padrão do Python, com dois modos:
- `python3 scripts/dicionario.py regenerar`: baixa `lexico`, `conjugações` e `icf` de `fserb/pt-br`, normaliza (minúsculas, sem acento), mantém só `^[a-z]{4,10}$`, usa `icf` com score ≤ 18 (corte escolhido pelo usuário), gera plurais e femininos regulares a partir dos verbetes do `lexico`, acrescenta as palavras das receitas e grava os 7 arquivos. É o único comando que precisa de rede e só roda quando alguém decide atualizar o dicionário.
- `python3 scripts/dicionario.py sincronizar`: offline, lê o `posts.json`, acrescenta nos arquivos existentes as `palavra`s que faltam (mantendo a ordem) e não mexe em mais nada. É o remédio quando `build.py --check` avisar que a palavra de uma receita não está no dicionário.

Regras das formas regulares (sobre o verbete `w`): `w+s`; `w+es` se terminar em `r`, `z`, `s` ou `l`; se terminar em `o`: `w[:-1]+a`, `w[:-1]+os`, `w[:-1]+as`. Sem tentar tratar casos irregulares: exceções vão para as palavras das receitas (como `fofinha`) ou ficam de fora.

- **Alternativa: usar só `lexico` + `conjugações` + `icf`.** Rejeitada: num teste com 40 palavras comuns, 18 faltaram (`bolos`, `tomates`, `batatas`, `queijos`, `crocantes`, `assadas`, `rapida`).
- Licença: a lista é MIT. O README e um `static/dicionario/LICENSE-pt-br.txt` registram a origem, o link e o texto da licença (copyright de fserb).
- `build.py` NÃO baixa nada: só lê os arquivos do repositório. A regeneração não faz parte do `pages.yml`.

### 5. Palavra de receita sempre no dicionário
`carregar_posts()` (ou uma função chamada por ela) confere cada `palavra` normalizada contra o arquivo do tamanho correspondente. Se faltar, `--check` e o build terminam com erro: `<slug>: palavra 'shakshuka' não está em static/dicionario/9.txt. Rode: python3 scripts/dicionario.py sincronizar`. Assim a palavra do dia sempre pode ser digitada (a pessoa nunca fica sem poder ganhar) e o dicionário só cresce quando alguém roda o script e faz commit do resultado.

- **Alternativa: o build injeta a palavra no `dist/` sem mexer no repositório.** Rejeitada: o dicionário no repositório deixaria de ser a fonte da verdade e o arquivo em produção divergiria do versionado.
- **Vazamento aceito:** palavras de receitas publicadas que não estão na lista de origem ficam no arquivo do dicionário e podem ser descobertas por comparação com um dicionário geral. Afeta só palavras como `shakshuka`.

### 6. Página `/palavra-do-dia/` pré-renderizada, lógica em `static/jogo.js`
`pagina_jogo()` em `build.py` gera o HTML completo (título, descrição, canonical, grade com o tamanho de hoje e teclado como `<button>`), passando por `pagina()` para manter o layout de três colunas. A grade é refeita no navegador a partir do `tamanho` do `jogo.json` (cobre o caso de uma página em cache de ontem). A lógica fica num `static/jogo.js` próprio, carregado só nessa página com `?v=<hash>`. `app.js` (busca) e a gaveta não mudam.

- **Alternativa: estender `app.js`.** Rejeitada: acoplaria o jogo à busca e engordaria o JS de todas as páginas.
- A página deve existir mesmo sem JS (com `<noscript>` explicando que o jogo precisa de JavaScript).
- `jogo.js` busca `jogo.json` com `fetch(url, {cache: "no-cache"})`, usando `window.SITE.base` como o `app.js`.
- Layout: colunas definidas por CSS (`--colunas`), células com `aspect-ratio: 1`, largura que cabe 10 letras em 360 px.

### 7. Estado no `localStorage`, por data
Chave `cc_jogo` guarda `{data, tentativas: ["frango", ...]}`. Ao carregar, se `data` difere da de `jogo.json`, o estado é descartado. Todo acesso ao `localStorage` fica em `try/catch` (como `salvar()` em `app.js`), então navegador bloqueado só perde a persistência.

- A tentativa guardada é a string digitada normalizada; as dicas são recalculadas na carga, sem guardar o resultado.

### 8. Conferência de existência antes de avaliar
Ao confirmar uma linha, `jogo.js` normaliza a tentativa (`normalize('NFD')` sem diacríticos, como `norm()` no `app.js`) e a procura no `Set` do dicionário. Se não existir, mostra o aviso, mantém as letras e não conta a tentativa. A tentativa válida é avaliada pelo algoritmo de dicas (decisão 9). Se o arquivo do dicionário falhar ao carregar, a página mostra uma mensagem e não aceita tentativas (não aceitar qualquer coisa em silêncio).

### 9. Algoritmo de dicas em duas passadas
Passada 1 marca as letras certas e conta as letras restantes da palavra. Passada 2 marca presentes só enquanto houver letra sobrando. Isso trata repetições como no Termo/Wordle. A dica é expressa por classe CSS e por `aria-label` e símbolo (não só cor). A comparação usa a palavra sem acento; a palavra do dia com acento só é exibida ao fim.

### 10. Integração com o restante do build
- `lateral_esq()`: item de menu "Jogo do dia" só quando o jogo existe.
- Sitemap: `/palavra-do-dia/` entra com `lastmod` do dia do build.
- `cabecalhos_cloudflare()`: `{BASE}/jogo.json` com `max-age=0, must-revalidate`, igual `busca.json`; `/dicionario/*` com cache longo (arquivos com `?v=`).
- `README.md`: seção sobre o campo `palavra`, o dicionário e o script, e o crédito à lista de origem.

## Risks / Trade-offs

- [A palavra de hoje é visível em `jogo.json`] → aceito (blog, sem prêmio). Não publicamos palavras futuras. O arquivo não é indexado em nenhuma página.
- [Palavra válida recusada (rara, regional ou irregular)] → a lista cobre ~346 mil formas, mas nenhuma lista é perfeita. Mitigação: o script `sincronizar` e o `regenerar` são fáceis de rodar, e pode-se acrescentar palavras ao script como exceções. Aceito.
- [Forma regular que não existe aceita (ex.: plural de palavra sem plural)] → o requisito "apenas palavras que existem" fica um pouco menos estrito, em troca de aceitar `bolos`, `tomates` e `queijos`. Mitigação: só formas regulares do `lexico`; sem tentativas sem sentido (`xqzwkj`). Aceito.
- [Tamanho do repositório: ~3 MB de texto em 7 arquivos] → o Git comprime; mudanças futuras (regenerar) geram diffs grandes, mas raros. O download por visita é de um arquivo só.
- [Cache antigo mostra a palavra de ontem] → `Cache-Control` de revalidação no Cloudflare, `fetch` com `cache: "no-cache"` e a data dentro do JSON, que descarta o progresso velho. No GitHub Pages não dá para mudar cabeçalhos, então o `no-cache` do `fetch` é a defesa.
- [Mudar `palavra` de uma receita ou adicionar receitas muda a palavra do dia já sorteada] → o sorteio depende do conjunto de candidatas. Mitigação: documentar no README; mudar a lista no mesmo dia já pode trocar a palavra de hoje. Aceito.
- [Fuso: dia do jogo muda às 00h BRT, o deploy só às 07h] → entre 00h e 07h a palavra continua a de ontem, mas a data dentro do `jogo.json` ainda é a de ontem, então o progresso é coerente. Aceito; o cron pode ser adiantado depois.
- [Palavra de 10 letras em telas pequenas] → grade por CSS com `aspect-ratio` e `gap` pequenos; testar em 360 px.
- [Mudança de deploy] → esta mudança não altera `pages.yml`. O impacto no deploy é o `_headers` do Cloudflare e os novos arquivos em `dist/`.

## Migration Plan

1. Gerar o dicionário (`regenerar`) e commitar os arquivos, ainda sem `palavra` no `posts.json`: o build continua verde e o jogo fica oculto.
2. Implementar validação, sorteio e a cópia do dicionário. Com nenhuma `palavra`, nada muda no site.
3. Mostrar a lista proposta de palavras, receber aprovação, gravar `palavra` nas receitas e rodar `sincronizar` (acrescenta as que faltarem).
4. Gerar a página, testar localmente (`python3 build.py`, `python3 -m http.server 8000 -d dist`, `BUILD_DATE` para vários dias, com tamanhos de 4 e 10 letras).
5. Abrir PR; o push na `main` publica. Rollback: reverter o PR. Nenhum dado persistente do servidor é afetado, e o `localStorage` das pessoas fica inofensivo (chave ignorada).
