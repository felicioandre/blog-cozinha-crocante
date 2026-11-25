# Tasks

## 1. Dicionário no repositório

- [x] 1.1 Criar `scripts/dicionario.py` com o modo `regenerar`: baixa `lexico`, `conjugações` e `icf` de `fserb/pt-br` para uma pasta temporária, normaliza (minúsculas, sem acento), mantém `^[a-z]{4,10}$`, usa `icf` com score ≤ 18, gera plurais/femininos regulares do `lexico` e grava `static/dicionario/4.txt` a `10.txt` (ordenados, sem repetição). Verificar rodando o comando e conferindo que cada arquivo só tem linhas do tamanho do nome, sem duplicatas, e que `frango`, `queijo`, `casas`, `ovos`, `legumes`, `assados`, `bolos`, `batatas` e `tomates` existem.
- [x] 1.2 Acrescentar ao script o modo `sincronizar` (offline, só biblioteca padrão): lê o `posts.json` e inclui em ordem nos arquivos as `palavra`s que faltam. Verificar com uma cópia do `posts.json` com `shakshuka` (a palavra aparece em `9.txt`) e rodando o comando duas vezes (a segunda não muda nenhum arquivo, `git status` limpo).
- [x] 1.3 Registrar a origem: `static/dicionario/LICENSE-pt-br.txt` com o link, o copyright e o texto da licença MIT de `fserb/pt-br`. Verificar o conteúdo contra o `LICENSE` do repositório de origem.
- [x] 1.4 Commitar os 7 arquivos gerados. Verificar o tamanho total em disco (esperado ~3 MB) e que `git diff --stat` mostra só `static/dicionario/` e `scripts/`.

## 2. Validação e sorteio no build

- [x] 2.1 Em `carregar_posts()` ([build.py](../../../build.py)), validar `palavra` opcional: 4 a 10 letras do alfabeto português, unicidade sem acento/maiúsculas e presença no `static/dicionario/<n>.txt` correspondente; erro cita o slug e o comando `python3 scripts/dicionario.py sincronizar`. Verificar com um `posts.json` temporário (em outra pasta) com palavra de 3 letras, de 11 letras, `air-fryer`, duplicadas e `shakshuka` sem sincronizar: `python3 build.py --check` falha em cada caso, e passa com o `posts.json` atual.
- [x] 2.2 Criar `palavra_do_dia(posts, d)` ao lado de `escolhas_do_dia()`, só com receitas visíveis que têm `palavra`, sem repetir a de ontem. Verificar com `BUILD_DATE` em 5 dias seguidos: mesmo dia gera sempre a mesma palavra e dias consecutivos geram palavras diferentes.
- [x] 2.3 Em `main()`, gravar `dist/jogo.json` (`data`, `palavra`, `tamanho`, `slug`, `titulo`) só com a palavra de hoje; com menos de 2 palavras, avisar e pular `jogo.json` e a página. Verificar com `python3 build.py` e `grep` em `dist/` provando que as palavras das outras receitas não aparecem em `jogo.json`.
- [x] 2.4 Copiar `static/dicionario/` para `dist/dicionario/` (cópia recursiva só dessa pasta, sem mudar o resto) e acrescentar `{BASE}/jogo.json` com `max-age=0, must-revalidate` e `{BASE}/dicionario/*` com cache longo em `cabecalhos_cloudflare()`. Verificar com `python3 build.py` e `ls dist/dicionario`, e com `DEPLOY_TARGET=cloudflare python3 build.py` e `grep -E "jogo.json|dicionario" dist/_headers`.

## 3. Palavras das receitas

- [x] 3.1 Montar a lista proposta (slug → palavra de 4 a 10 letras ligada ao prato, sem repetir, variando os tamanhos) e **mostrar ao usuário antes de alterar o `posts.json`**. Verificar com a aprovação explícita da lista.
- [x] 3.2 Gravar `palavra` nas receitas aprovadas, sem remover nenhum link de afiliado nem mudar slugs, e rodar `python3 scripts/dicionario.py sincronizar`. Verificar com `python3 build.py --check` (OK, sem erro) e `git diff posts.json` mostrando só linhas `palavra` adicionadas.

## 4. Página do jogo

- [x] 4.1 Criar `pagina_jogo()` em [build.py](../../../build.py): HTML completo com título, descrição, canonical via `url_abs()`, regras curtas, grade 6×N de hoje, teclado em `<button>`, `<noscript>` e links internos por `url()`. Item "Jogo do dia" em `lateral_esq()` e `/palavra-do-dia/` no sitemap, só quando houver jogo. Verificar com `python3 build.py` e `dist/jogo/index.html` com a grade, o teclado e o `?v=<hash>` do script, e com `BASE_PATH=/teste python3 build.py` mantendo os links corretos.
- [x] 4.2 Criar `static/jogo.js`: carregar `jogo.json` com `cache: "no-cache"`, montar a grade 6×`tamanho`, entrada pelo teclado físico e pelo da tela (Enter, Backspace), 6 tentativas e aviso de linha incompleta. Verificar abrindo `python3 -m http.server 8000 -d dist` e jogando uma partida completa.
- [x] 4.3 Carregar `dicionario/<tamanho>.txt?v=<hash>` num `Set` e recusar tentativa que não existe (aviso, letras mantidas, tentativa não contada); sem acento e sem diferença de maiúsculas; falha de carga mostra mensagem e bloqueia tentativas. Verificar digitando uma palavra inexistente, uma existente sem acento e bloqueando o arquivo do dicionário nas ferramentas do navegador.
- [x] 4.4 Implementar as dicas em duas passadas (certa/presente/ausente, com letra repetida) e a cor das teclas pela melhor dica. Verificar com os exemplos "arroz"/"amora", "arroz"/"rorro" e "limão"/"limao" do spec, no console do navegador ou numa partida com `jogo.json` ajustado à mão em `dist/`.
- [x] 4.5 Implementar o fim da partida (acerto e erro): mostrar a palavra com acento e o link "Ver receita: <título>" para `/receitas/<slug>/`, bloqueando novas letras. Verificar acertando na tentativa 3 e errando 6 vezes: link correto nos dois casos.
- [x] 4.6 Salvar o progresso no `localStorage` por data (chave `cc_jogo`), descartando o de dias anteriores e com `try/catch` em todo acesso. Verificar recarregando no meio da partida, reabrindo após terminar, trocando a `data` do `jogo.json` e bloqueando o `localStorage` nas ferramentas do navegador.
- [x] 4.7 Tratar falha do `fetch` do `jogo.json` com mensagem em português e link para a página inicial. Verificar renomeando `dist/jogo.json` temporariamente e recarregando a página.
- [ ] 4.8 Estilos do jogo em [static/style.css](../../../static/style.css): grade com colunas por `--colunas`, células, teclado, cores com forma/texto além da cor, responsivo em 360 px de largura com palavra de 10 letras. Verificar visualmente com `BUILD_DATE` em dias com palavras de 4 e de 10 letras, em 360 px e em desktop, e a navegação só com o teclado.
- [ ] 4.9 Acessibilidade: `aria-label` por célula ("a, letra certa"), região `aria-live` para mensagens e foco visível nas teclas. Verificar inspecionando o DOM de uma tentativa confirmada.

## 5. Documentação e fechamento

- [x] 5.1 Documentar no [README.md](../../../README.md) o campo `palavra` na tabela de campos (4 a 10 letras, única, no dicionário), o sorteio diário, o dicionário (onde fica, como `sincronizar` e `regenerar`) e o crédito/licença da lista `fserb/pt-br`. Verificar relendo a seção e rodando os comandos citados.
- [x] 5.2 Verificação final: `python3 build.py --check`, `python3 build.py` e, com `BUILD_DATE` em dias diferentes, conferir `dist/jogo.json`, `dist/dicionario/`, o sitemap e o menu. Verificar que nenhuma página existente ficou com link quebrado nem teve link de afiliado removido (`git diff --stat` sem mudanças em `affiliates.json`).

## 6. Ajustes de interface depois do primeiro teste

- [x] 6.1 Página em `/palavra-do-dia/`, link "Palavra do dia" no menu do topo, página de uma coluna sem rodapé e com a altura da janela. Verificar abrindo `/palavra-do-dia/` e conferindo `dist/sitemap.xml` e o menu.
- [x] 6.2 Carregar `jogo.js` só nessa página e usar `data-acao` nos botões do teclado, com apagar ao lado do P e Enter ao lado do M. Verificar carregando a página por HTTP no jsdom e clicando nas teclas até acertar a palavra.
- [x] 6.3 Regras em modal (`<dialog>`) com botão "?", sem o título "Descubra a palavra do dia", rótulo "Jogo palavra do dia" e aba "O que tenho em casa?" oculta até 760 px nessa página. Verificar abrindo o modal no jsdom e conferindo a regra `@media (max-width:760px)` no CSS.

## Workflow follow-up

- Seguir AGENTS.md: branch nova a partir da `main` atualizada, commits no padrão commitizen e abrir a PR ao fazer o push.
- Arquivar a change após a revisão e o deploy.
