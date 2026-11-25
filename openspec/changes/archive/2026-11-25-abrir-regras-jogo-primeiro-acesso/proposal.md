# Proposal

## Why

As regras do jogo da palavra do dia ficam só no modal do botão "?". Quem chega pela primeira vez pode não notar o botão e não entender como jogar. Abrir o modal sozinho no primeiro acesso resolve isso sem poluir as visitas seguintes.

## What Changes

- Na primeira visita a `/palavra-do-dia/`, o modal de regras abre automaticamente.
- O navegador guarda no `localStorage` que a pessoa já viu as regras; nas próximas visitas o modal não abre sozinho.
- O botão "?" continua abrindo o modal a qualquer momento.
- Sem mudança no HTML gerado pelo `build.py` nem no formato de `jogo.json`; só comportamento em `static/jogo.js`.

## Capabilities

### New Capabilities
- `jogo-ajuda-primeiro-acesso`: abertura automática do modal de regras na primeira visita ao jogo e registro local de que já foi exibido.

### Modified Capabilities

## Impact

- Código: `static/jogo.js` (bloco "modal de ajuda").
- Dados no navegador: nova chave no `localStorage`, separada da chave do progresso (`cc_jogo`).
- Sem impacto em build, deploy, `posts.json` ou SEO.
- Depende do modal de regras da change `add-jogo-palavra-do-dia` (ainda não arquivada, por isso esta change tem capability própria em vez de modificar a dela).
