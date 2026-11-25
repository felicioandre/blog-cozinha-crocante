# Spec Delta

## Purpose

Oferecer uma página de jogo diário no estilo Termo, em que a pessoa descobre a palavra do dia e, no fim da partida, é levada à receita do blog ligada a essa palavra.

## ADDED Requirements

### Requirement: Página do jogo
O site MUST ter a página `/palavra-do-dia/`, com título, regras curtas, grade de 6 linhas e uma coluna por letra da palavra do dia, e teclado na tela. A página MUST ser HTML completo gerado no build (título, descrição e link canônico), sem depender do JavaScript para existir, e MUST aparecer no menu lateral e no `sitemap.xml`.

#### Scenario: Acesso à página
- **WHEN** a pessoa abre `/palavra-do-dia/`
- **THEN** vê a grade vazia de 6 linhas, com o número de colunas igual ao tamanho da palavra do dia, e o teclado
- **AND** o menu lateral tem um link para o jogo

#### Scenario: Tamanho diferente a cada dia
- **WHEN** a palavra do dia tem 8 letras
- **THEN** a grade tem 6 linhas por 8 colunas e a tentativa só é confirmada com 8 letras

#### Scenario: Indexação
- **WHEN** o build conclui
- **THEN** `dist/sitemap.xml` lista a URL canônica de `/palavra-do-dia/`

### Requirement: Tentativas
A pessoa MUST ter até 6 tentativas. Cada tentativa tem exatamente o tamanho da palavra do dia, digitada no teclado físico ou no da tela e confirmada com Enter.

#### Scenario: Tentativa incompleta
- **WHEN** a pessoa aperta Enter com menos letras que o tamanho da palavra
- **THEN** a linha não é confirmada
- **AND** a página avisa que faltam letras

#### Scenario: Apagar letra
- **WHEN** a pessoa aperta Backspace antes de confirmar
- **THEN** a última letra da linha atual é apagada

#### Scenario: Letras com acento
- **WHEN** a palavra do dia é "limão" e a pessoa digita "limao"
- **THEN** a tentativa acerta a palavra
- **AND** a palavra exibida ao fim da partida mantém o acento

### Requirement: Só palavras que existem
Ao confirmar uma tentativa, a página MUST conferir a palavra no dicionário do tamanho da palavra do dia. Palavra que não existe MUST ser recusada com um aviso, sem gastar tentativa e sem apagar as letras digitadas. A conferência não distingue acento nem maiúsculas.

#### Scenario: Palavra inexistente
- **WHEN** a pessoa confirma "xqzwkj" numa palavra de 6 letras
- **THEN** a linha continua editável, a tentativa não é contada e a página avisa que a palavra não existe

#### Scenario: Palavra existente sem acento
- **WHEN** a pessoa digita "limao" e o dicionário tem "limao"
- **THEN** a tentativa é aceita

#### Scenario: Palavra de receita
- **WHEN** a palavra do dia é "shakshuka", que só existe no dicionário por ser palavra de receita
- **THEN** a pessoa consegue digitar e acertar "shakshuka"

#### Scenario: Dicionário indisponível
- **WHEN** o arquivo do dicionário do dia não carrega
- **THEN** a página mostra uma mensagem em português dizendo que não consegue conferir as palavras agora, e não aceita tentativas

### Requirement: Dicas por cor
Ao confirmar uma tentativa, cada letra MUST receber uma de três dicas: certa (posição correta), presente (existe em outra posição) ou ausente. Letra repetida na tentativa só conta como presente quantas vezes aparece na palavra. O teclado na tela MUST refletir a melhor dica de cada letra. A dica MUST NÃO depender só de cor (também por forma ou texto acessível).

#### Scenario: Letra no lugar certo
- **WHEN** a palavra é "arroz" e a tentativa é "amora"
- **THEN** a primeira letra "a" é marcada como certa
- **AND** a segunda letra "m" é marcada como ausente

#### Scenario: Letra repetida
- **WHEN** a palavra é "arroz" e a tentativa é "rorro"
- **THEN** o número de letras "r" marcadas como certas ou presentes nunca passa de 2

#### Scenario: Teclado
- **WHEN** uma letra foi marcada como ausente e depois como certa em outra tentativa
- **THEN** a tecla mostra a dica certa

### Requirement: Fim da partida e link para a receita
A partida MUST terminar quando a pessoa acerta ou usa as 6 tentativas. Nos dois casos a página MUST mostrar a palavra do dia e um link para a receita ligada a ela, usando o título da receita.

#### Scenario: Acerto
- **WHEN** a pessoa acerta a palavra na tentativa 3
- **THEN** a página mostra a mensagem de acerto, a palavra e o link "Ver receita: <título>"
- **AND** o link leva a `/receitas/<slug>/`
- **AND** o teclado e a grade não aceitam mais letras

#### Scenario: Erro
- **WHEN** a pessoa erra as 6 tentativas
- **THEN** a página revela a palavra e mostra o link para a receita

### Requirement: Progresso salvo por dia
A página MUST guardar no navegador as tentativas do dia, para a pessoa poder fechar e voltar sem perder a partida. Quando a data de `jogo.json` mudar, o progresso do dia anterior MUST ser descartado e uma nova partida começa. Se o armazenamento do navegador estiver indisponível, o jogo MUST funcionar sem salvar.

#### Scenario: Recarregar a página
- **WHEN** a pessoa fez 2 tentativas e recarrega a página no mesmo dia
- **THEN** as 2 tentativas continuam na grade com as mesmas dicas

#### Scenario: Partida já terminada
- **WHEN** a pessoa já terminou a partida do dia e reabre a página
- **THEN** vê a grade final, a palavra e o link para a receita
- **AND** não pode jogar de novo no mesmo dia

#### Scenario: Novo dia
- **WHEN** a pessoa abre a página e a data em `jogo.json` é diferente da data do progresso salvo
- **THEN** a grade começa vazia

#### Scenario: Armazenamento bloqueado
- **WHEN** o navegador bloqueia o `localStorage`
- **THEN** o jogo funciona normalmente, mas o progresso se perde ao recarregar

### Requirement: Falha ao carregar a palavra
Se `jogo.json` não carregar, a página MUST mostrar uma mensagem em português e um link para a página inicial, sem erro visível de script.

#### Scenario: jogo.json indisponível
- **WHEN** a requisição de `/jogo.json` falha
- **THEN** a página mostra uma mensagem de que o jogo está indisponível agora
- **AND** oferece o link para a página inicial

### Requirement: Uso com teclado, celular e leitor de tela
O jogo MUST ser jogável só com o teclado e caber em telas de 360 px de largura, inclusive com palavras de 10 letras. A grade e as mensagens MUST ser anunciáveis por leitor de tela (letras, posição e dica de cada tentativa).

#### Scenario: Palavra de 10 letras no celular
- **WHEN** a palavra do dia tem 10 letras e a tela tem 360 px de largura
- **THEN** a grade inteira e o teclado ficam visíveis sem rolagem horizontal

#### Scenario: Anúncio da dica
- **WHEN** uma tentativa é confirmada
- **THEN** cada célula expõe a letra e a dica em texto acessível (por exemplo, "a, letra certa")
