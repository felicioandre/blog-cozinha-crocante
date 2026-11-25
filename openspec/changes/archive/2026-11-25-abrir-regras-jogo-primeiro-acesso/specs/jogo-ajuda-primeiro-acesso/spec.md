# Spec Delta

## Purpose

Mostrar as regras do jogo da palavra do dia automaticamente na primeira visita de cada pessoa, lembrando localmente que já foram exibidas para não repetir o aviso.

## ADDED Requirements

### Requirement: Modal abre sozinho na primeira visita
Na primeira visita a `/palavra-do-dia/` em um navegador, o modal de regras MUST abrir automaticamente ao carregar a página, sem que a pessoa clique no botão "?".

#### Scenario: Primeira visita
- **WHEN** a pessoa abre `/palavra-do-dia/` e o navegador não tem registro de regras já vistas
- **THEN** o modal de regras abre sozinho
- **AND** nenhuma letra é digitada na grade enquanto o modal estiver aberto

#### Scenario: Fechar o modal
- **WHEN** a pessoa clica em "Entendi", fora da caixa ou aperta Esc
- **THEN** o modal fecha e o jogo fica pronto para jogar

### Requirement: Registro de que as regras foram vistas
Ao abrir o modal automaticamente, o site MUST gravar no `localStorage` do navegador que as regras já foram exibidas, em chave própria, independente do progresso das partidas.

#### Scenario: Registro gravado
- **WHEN** o modal abre sozinho pela primeira vez
- **THEN** o `localStorage` passa a ter o registro de regras vistas

#### Scenario: Progresso não afeta o registro
- **WHEN** a partida do dia é concluída ou a data muda
- **THEN** o registro de regras vistas continua gravado

### Requirement: Visitas seguintes não abrem o modal
Se o registro de regras vistas existir, o modal MUST NOT abrir automaticamente. O botão "?" MUST continuar abrindo o modal.

#### Scenario: Segunda visita
- **WHEN** a pessoa volta a `/palavra-do-dia/` com o registro gravado
- **THEN** o modal não abre sozinho

#### Scenario: Reabrir pelo botão
- **WHEN** a pessoa clica no botão "?"
- **THEN** o modal de regras abre, haja ou não registro

### Requirement: Falha do localStorage não quebra o jogo
Se o navegador bloquear o `localStorage`, o jogo MUST funcionar normalmente e o modal MUST abrir sozinho nas visitas em que o registro não puder ser lido.

#### Scenario: Armazenamento bloqueado
- **WHEN** a leitura ou a gravação no `localStorage` lança erro
- **THEN** não há erro visível, o modal abre e o jogo segue funcionando
