# palavra-do-dia-selecao Specification

## Purpose

Define como cada receita recebe uma palavra de jogo e como o site escolhe, a cada dia, a palavra do dia ligada a uma receita já publicada.

## Requirements

### Requirement: Receita pode ter uma palavra de jogo
O build MUST aceitar o campo opcional `palavra` em cada receita do `posts.json`, com 4 a 10 letras. Receita sem `palavra` continua válida e fica fora do jogo.

#### Scenario: Receita com palavra válida
- **WHEN** uma receita tem `"palavra": "frango"`
- **THEN** `python3 build.py --check` aceita a receita

#### Scenario: Palavra longa válida
- **WHEN** uma receita tem `"palavra": "abacaxi"` ou `"palavra": "brigadeiro"`
- **THEN** `python3 build.py --check` aceita a receita

#### Scenario: Receita sem palavra
- **WHEN** uma receita não tem o campo `palavra`
- **THEN** `python3 build.py --check` aceita a receita
- **AND** a receita nunca é sorteada como palavra do dia

### Requirement: Palavra tem formato válido
O build MUST rejeitar `palavra` que não tenha entre 4 e 10 letras do alfabeto português (a–z, com ou sem acento), sem espaços, números ou hífens.

#### Scenario: Palavra curta demais
- **WHEN** uma receita tem `"palavra": "ovo"` (3 letras)
- **THEN** `build.py --check` termina com erro citando o slug da receita e o campo `palavra`

#### Scenario: Palavra longa demais
- **WHEN** uma receita tem `"palavra": "hamburgueres"` (11 letras)
- **THEN** `build.py --check` termina com erro citando o slug da receita

#### Scenario: Palavra com caractere inválido
- **WHEN** uma receita tem `"palavra": "air-fryer"`
- **THEN** `build.py --check` termina com erro citando o slug da receita

### Requirement: Palavra é única entre as receitas
O build MUST rejeitar duas receitas com a mesma `palavra`, comparando sem acento e sem diferenciar maiúsculas de minúsculas, para que cada palavra leve a uma única receita.

#### Scenario: Palavras repetidas
- **WHEN** duas receitas têm `"palavra": "bolos"` e `"palavra": "BOLOS"`
- **THEN** `build.py --check` termina com erro citando os dois slugs

#### Scenario: Palavras que só diferem no acento
- **WHEN** uma receita tem `"palavra": "sírio"` e outra tem `"palavra": "sirio"`
- **THEN** `build.py --check` termina com erro citando os dois slugs

### Requirement: Palavra do dia sai de uma receita publicada
O build MUST sortear a palavra do dia apenas entre as receitas já publicadas (campo `publicado` até a data do build) que tenham `palavra`. A escolha MUST depender só da data, de modo que o mesmo dia gere sempre a mesma palavra.

#### Scenario: Mesmo dia, mesma palavra
- **WHEN** o build roda duas vezes com `BUILD_DATE=2026-12-01`
- **THEN** as duas execuções gravam a mesma palavra do dia

#### Scenario: Receita agendada fica de fora
- **WHEN** uma receita tem `palavra` mas `publicado` em data futura à do build
- **THEN** essa palavra não é sorteada

#### Scenario: Palavra muda no dia seguinte
- **WHEN** o build roda com `BUILD_DATE=2026-12-01` e depois com `BUILD_DATE=2026-12-02`
- **THEN** a palavra do dia 02 é diferente da palavra do dia 01

#### Scenario: Tamanho varia entre os dias
- **WHEN** a palavra de um dia tem 6 letras e a do dia seguinte tem 9
- **THEN** cada `jogo.json` traz o `tamanho` correspondente à palavra do dia

### Requirement: Só a palavra de hoje é publicada
O build MUST gravar em `dist/jogo.json` apenas a palavra de hoje, com a data do dia, o tamanho, o slug e o título da receita ligada. O site NÃO PODE publicar a lista das palavras futuras.

#### Scenario: Conteúdo do jogo.json
- **WHEN** o build conclui
- **THEN** `dist/jogo.json` tem `data`, `palavra`, `tamanho`, `slug` e `titulo` do dia
- **AND** `dist/` não contém nenhum arquivo que ligue as palavras das outras receitas às suas receitas (o dicionário tem só palavras, sem slug)

#### Scenario: Poucas palavras disponíveis
- **WHEN** menos de 2 receitas publicadas têm `palavra`
- **THEN** o build não grava `dist/jogo.json`, não gera a página `/jogo/` e avisa no console

### Requirement: Jogo é atualizado todo dia
O `dist/jogo.json` MUST ser servido sempre revalidado, para a palavra de hoje aparecer assim que o deploy diário publicar.

#### Scenario: Cabeçalho no Cloudflare
- **WHEN** o build roda com `DEPLOY_TARGET=cloudflare`
- **THEN** o `_headers` gerado define `Cache-Control: public, max-age=0, must-revalidate` para `/jogo.json`
