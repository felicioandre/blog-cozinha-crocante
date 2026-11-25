# Tasks

## 1. Abertura automática no primeiro acesso

- [x] 1.1 Em [static/jogo.js](../../../static/jogo.js), extrair `abrirModalAjuda()` do clique do "?" mantendo o fallback sem `showModal`; verificar que o botão "?" ainda abre o modal.
- [x] 1.2 Adicionar a chave `cc_jogo_ajuda`: ao carregar, se não existir (ou a leitura falhar), chamar `abrirModalAjuda()` e gravar o registro, tudo em `try/catch`; verificar no navegador com `localStorage` limpo que o modal abre sozinho e a chave passa a existir.
- [x] 1.3 Verificar que o modal não reabre ao recarregar, que o "?" continua funcionando, que digitar não preenche a grade com o modal aberto e que o jogo funciona com `localStorage` bloqueado.

## 2. Validação

- [x] 2.1 Rodar `python3 build.py --check` e `python3 build.py`, servir `dist/` com `python3 -m http.server 8000 -d dist` e conferir os cenários da spec em `/palavra-do-dia/` (desktop e celular).

## Workflow follow-up

- Branch nova a partir da `main` atualizada, commits no padrão commitizen e PR aberta ao fazer o push.
- Arquivar a change após o merge.
