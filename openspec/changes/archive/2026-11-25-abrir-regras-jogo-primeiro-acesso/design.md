# Design

## Context

O modal é um `<dialog id="ajuda">` gerado em `pagina_jogo()` ([build.py](../../../build.py)). O [static/jogo.js](../../../static/jogo.js) já abre o modal no clique de `#ajuda-abrir` (com fallback `setAttribute('open')` se faltar `showModal`) e guarda o progresso em `localStorage` na chave `cc_jogo`, com `try/catch`. Ver proposal.md para a motivação.

## Goals / Non-Goals

**Goals:**
- Abrir o modal uma vez por navegador, na primeira visita.
- Reutilizar a função de abrir já usada pelo botão "?".

**Non-Goals:**
- Mudar texto, HTML ou estilo do modal.
- Sincronizar o registro entre dispositivos ou contas.
- Reabrir as regras quando o conteúdo mudar (sem versionamento do registro).

## Decisions

- **Chave própria `cc_jogo_ajuda`**, valor `'1'`. Alternativa: campo dentro de `cc_jogo`. Descartada porque o progresso é reescrito/zerado por data e o registro precisa sobreviver.
- **Gravar ao abrir, não ao fechar.** Quem recarrega sem fechar o modal não o vê de novo. Alternativa (gravar ao fechar) repetiria o aviso para quem sai antes.
- **Abrir no carregamento do script, sem esperar `jogo.json` e o dicionário.** O modal é HTML estático do build; não depende dos dados. Se o jogo travar, o modal ainda aparece sem prejudicar.
- **Extrair `abrirModalAjuda()`** usada pelo clique do "?" e pela abertura automática, mantendo o fallback sem `showModal`.
- Leitura e gravação dentro de `try/catch`; se a leitura falhar, trata como primeira visita.

## Risks / Trade-offs

- [Navegador bloqueia `localStorage`] → modal abre em toda visita; aceitável, a pessoa fecha em um clique.
- [Modal abre sobre o jogo e atrapalha teclado] → o handler de `keydown` já ignora teclas com `ajuda.open`; verificar o foco ao abrir.
- [Navegação anônima ou limpeza de dados] → modal volta a abrir; comportamento esperado.
