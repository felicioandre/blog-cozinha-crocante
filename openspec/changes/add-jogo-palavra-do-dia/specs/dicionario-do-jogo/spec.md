# Spec Delta

## Purpose

Garantir que o jogo só aceite palavras que existem em português, usando um dicionário guardado no próprio repositório, que inclui as palavras das receitas e pode ser atualizado sem depender de serviços externos.

## ADDED Requirements

### Requirement: Dicionário fica no repositório
O dicionário MUST ficar versionado no repositório, em um arquivo por tamanho de palavra (`static/dicionario/4.txt` a `10.txt`). Nem o build nem o site em execução MUST depender de download de fontes externas.

#### Scenario: Build sem rede
- **WHEN** o build roda sem acesso à internet
- **THEN** `dist/dicionario/` contém os arquivos de 4 a 10 letras e o build conclui

#### Scenario: Site em execução
- **WHEN** a pessoa joga em `/palavra-do-dia/`
- **THEN** o dicionário vem do próprio site, sem requisição para outros domínios

### Requirement: Formato dos arquivos
Cada arquivo MUST ter uma palavra por linha, só com letras a–z minúsculas e sem acento, ordenadas, sem repetição e todas com o tamanho do nome do arquivo. Os arquivos MUST ser gerados pelo script, nunca editados à mão.

#### Scenario: Arquivo de 6 letras
- **WHEN** se abre `static/dicionario/6.txt`
- **THEN** toda linha tem exatamente 6 letras minúsculas entre a e z, sem repetição e em ordem alfabética

### Requirement: Conteúdo do dicionário
O dicionário MUST reunir o léxico e as conjugações da lista `fserb/pt-br` e as palavras de `icf` com score de até 18, acrescentar os plurais e femininos regulares dos verbetes do léxico e remover acentos. Palavras com letras fora de a–z (hífen, número) ou fora de 4 a 10 letras ficam de fora.

#### Scenario: Palavras comuns presentes
- **WHEN** se consulta o dicionário
- **THEN** `frango`, `queijo`, `casas`, `ovos`, `legumes`, `assados`, `bolos`, `batatas` e `tomates` existem

#### Scenario: Palavra de ICF alto fica de fora
- **WHEN** uma palavra aparece só em `icf` com score acima de 18
- **THEN** ela não entra no dicionário

#### Scenario: Palavra sem acento
- **WHEN** a lista traz `limão`
- **THEN** o dicionário guarda `limao`

### Requirement: Palavras das receitas fazem parte do dicionário
Toda `palavra` das receitas MUST existir no dicionário do repositório, mesmo que não conste na lista de origem (por exemplo `shakshuka`). Se faltar alguma, o build MUST falhar com erro que cita a palavra, o slug e o comando que a acrescenta.

#### Scenario: Palavra de receita fora da lista de origem
- **WHEN** uma receita tem `"palavra": "shakshuka"` e o dicionário não a tem
- **THEN** `python3 build.py --check` termina com erro citando `shakshuka`, o slug da receita e o comando de sincronização

#### Scenario: Depois de sincronizar
- **WHEN** o script de sincronização é executado
- **THEN** `shakshuka` é acrescentada a `static/dicionario/9.txt`, em ordem
- **AND** `python3 build.py --check` passa

### Requirement: Atualização do dicionário por script
O repositório MUST ter um script único com dois modos: regenerar os arquivos a partir da lista `fserb/pt-br` (precisa de rede) e sincronizar as palavras das receitas nos arquivos existentes (offline, sem outras dependências além da biblioteca padrão do Python). Os dois modos MUST ser idempotentes.

#### Scenario: Sincronizar sem mudança
- **WHEN** o modo de sincronização roda com todas as palavras das receitas já presentes
- **THEN** nenhum arquivo muda

#### Scenario: Regenerar
- **WHEN** o modo de regeneração roda com rede
- **THEN** os 7 arquivos são recriados com o corte de ICF 18 e as palavras das receitas continuam presentes

### Requirement: Crédito e licença da lista de origem
O repositório MUST registrar a origem do dicionário (`fserb/pt-br`, licença MIT) e o texto da licença junto dos arquivos ou no README.

#### Scenario: Atribuição
- **WHEN** se lê o README ou `static/dicionario/`
- **THEN** há menção à fonte, ao link do projeto e à licença MIT
