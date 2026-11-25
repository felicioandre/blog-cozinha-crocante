# Proposal

## Why

O blog só tem motivo para a pessoa voltar quando ela procura uma receita. Um jogo diário no estilo Termo (https://term.ooo/) cria um hábito de volta ao site todo dia, e cada palavra pode levar a uma receita, o que gera mais visitas às páginas com links de afiliado.

## What Changes

- Nova página `/jogo/` com o jogo da palavra do dia: palavra de 4 a 10 letras (o tamanho muda de um dia para o outro), 6 tentativas, dicas por cor (letra certa no lugar certo, letra existe em outro lugar, letra ausente) e teclado na tela.
- A palavra do dia é sempre ligada a uma receita do blog. Ao acertar ou errar, a página mostra a palavra e um link para a receita correspondente.
- Só palavras que existem podem ser digitadas: cada tentativa é conferida num dicionário em português. Tentativa com palavra inexistente é recusada e não gasta tentativa.
- Dicionário **dentro do repositório**, em arquivos minificados por tamanho de palavra (`static/dicionario/4.txt` a `10.txt`). O site não depende de nenhum serviço externo em tempo de execução nem de build. A base é a lista MIT [fserb/pt-br](https://github.com/fserb/pt-br) (léxico, conjugações e palavras de frequência com ICF até 18, mais plurais e femininos regulares), com crédito no repositório.
- As palavras das receitas fazem parte do dicionário. Se a `palavra` de uma receita ainda não estiver nos arquivos, o `--check` e o build avisam com erro e um script offline a acrescenta nos arquivos do repositório.
- Novo campo opcional `palavra` em cada receita do `posts.json` (4 a 10 letras, única entre as receitas). Só receitas publicadas e com `palavra` entram no sorteio.
- O build sorteia a palavra de hoje pela data (determinístico, mesma lógica de `escolhas_do_dia()`) e grava só a palavra de hoje em `dist/jogo.json`, com o tamanho. O cron diário das 07h do `pages.yml` já atualiza o site. A pessoa só baixa o dicionário do tamanho da palavra do dia.
- Link para o jogo no menu lateral e no sitemap. O progresso fica no `localStorage`, por data.
- `build.py --check` valida o campo `palavra` (formato, unicidade, presença no dicionário) e avisa quando há poucas palavras.
- Cabeçalho de cache para `/jogo.json` no `_headers` do Cloudflare (sempre revalidar), como já é feito com `busca.json`.
- Preencher `palavra` nas receitas existentes: **a lista de palavras será proposta para aprovação antes de gravar no `posts.json`**.

## Capabilities

### New Capabilities
- `palavra-do-dia-selecao`: campo `palavra` das receitas (4 a 10 letras), validação no build e sorteio diário da palavra (uma por receita, sem repetir a de ontem, só receitas já publicadas).
- `dicionario-do-jogo`: dicionário em português guardado no repositório, por tamanho de palavra, com as palavras das receitas incluídas e um script para gerar e atualizar os arquivos.
- `jogo-palavra-do-dia`: página `/jogo/` com as regras do jogo, teclado, grade de tamanho variável, conferência no dicionário, estado salvo no navegador e link para a receita ao fim da partida.

### Modified Capabilities

Nenhuma. Ainda não há specs em `openspec/specs/`.

## Impact

- `posts.json`: campo novo e opcional `palavra` (não quebra receitas existentes; mostrar a mudança antes de alterar).
- `build.py`: validação em `carregar_posts()`, função de sorteio, `pagina_jogo()`, `dist/jogo.json`, cópia de `static/dicionario/` para `dist/`, menu em `lateral_esq()`, sitemap e `_headers`. Hoje o build só copia arquivos soltos de `static/`; subpastas precisam ser copiadas.
- `static/`: novo `jogo.js`, estilos do jogo em `style.css` e a pasta `dicionario/` (7 arquivos, ~3 MB sem compressão e menos de 1 MB comprimidos; cada visita baixa só um, de 6 a ~260 KB comprimido). `app.js` não muda.
- `scripts/dicionario.py` (novo): gera os arquivos a partir da lista `fserb/pt-br` e sincroniza as palavras das receitas sem rede.
- `README.md`: documentar o campo `palavra`, o jogo, o dicionário e o crédito/licença da lista.
- Sem novas dependências de execução (o script usa só a biblioteca padrão do Python). Não altera `pages.yml`: o cron diário já atualiza o site.

## Fora de escopo

- Placar, ranking, compartilhamento de resultado e modo difícil.
- Palavras com menos de 4 ou mais de 10 letras, ou com hífen/espaço.
- Dicas de ajuda (revelar letra) e número de tentativas variável pelo tamanho da palavra.
- Atualizar o dicionário automaticamente a partir do GitHub: a atualização é manual, com o script.
