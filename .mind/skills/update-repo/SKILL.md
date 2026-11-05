---
name: update-repo
version: "1.0"
repo: standalone
description: >
  Atualiza o .mind/ de cada repositório filho para refletir o estado atual e, quando executada
  a partir do MindHub, as visões agregadas do MindHub. Lê o scope/assets.yaml para descobrir os repos,
  verifica quais já foram onboardados, lê o código-fonte deles com rg e abre um PR no repo filho
  com atualizações factuais.
  Nunca altera .mind/skills/ em nenhum repo filho — as skills locais pertencem ao time do repo.
  USE PARA: documentação desatualizada, divergência entre docs e código, .mind desatualizado,
  atualizar topologia, atualizar overview, status de onboarding mudou, novo repo adicionado,
  componente mudou de arquitetura.
argument-hint: >
  Opcional: asset:<id> para limitar a um grupo de ativos (padrão: todos do scope/assets.yaml).
  Opcional: repo:<nome-curto> para limitar a um repo específico.
  Exemplo de tags: skill:update-repo; skill:update-repo repo:my-app-web
triggers:
  - "atualizar repo"
  - "atualizar o .mind"
  - "atualizar mindhub"
  - "atualizar documentação"
  - "documentação desatualizada"
  - "docs não batem com o código"
  - "sincronizar docs"
  - "update repo"
  - "mind out of date"
scope:
  allowed:
    - ".mind/context/**"
    - ".mind/topology/**"
    - ".mind/lessons/**"
    - "docs/components/**"             # somente no MindHub (Passo 4)
    - ".mind/agent-bootstrap.md"      # criado se faltar; regenerado se a versão do template mudou
    - ".github/copilot-instructions.md" # criado se faltar; bloco mind regenerado se a versão do template mudou
    - ".github/pull_request_template.md" # criado se faltar; copiado de .mind/instructions/pull_request_template.md
    - "CLAUDE.md"                       # criado se faltar (raramente muda)
    - ".github/workflows/copilot-setup-steps.yml"  # atualizado quando a versão do template é mais nova
    - ".github/workflows/mind-pr-finalizer.yml"  # atualizado quando a versão do template é mais nova
  forbidden:
    - ".mind/scope/assets.yaml"        # o escopo de ativos é mantido por humanos
    - ".mind/_global/**"               # contexto de runtime somente leitura — nunca commitar
    - ".mind/decisions/**"
    - ".mind/skills/**"
    - ".mind/workflows/**"
    - ".mind/manifest.yaml"
    - ".mind/standards/**"             # os padrões são mantidos por humanos
    - ".gitignore"                       # nunca sobrescrever — o arquivo é do time do repo; só acréscimo, via Passo 0 do corpo da issue
    - "src/**"
    - "**/*.java"
    - "**/*.gradle"
    - "**/pom.xml"
---

# update-repo — Atualizar a Documentação dos Repositórios Filhos

Sincroniza o `.mind/` de cada repositório onboardado com o estado real do código-fonte e, quando
executada a partir do **MindHub** (a base central de conhecimento do projeto), atualiza as visões
agregadas do MindHub (`docs/components/`, `topology/`, visão geral do projeto).

- Os Passos 1.5 a 3b atuam no `.mind/` de cada repo filho (conhecimento local do repo).
- Os Passos 0–1, 4, 5 e 6 atuam no MindHub; no modo standalone eles são pulados.

É uma skill de **ler código, escrever documentação**. Nunca altera código de produção, testes nem arquivos de build.

---

## Passo 0: Montar a lista de repos alvo (MindHub)

Leia o `scope/assets.yaml` do MindHub, se existir; no modo standalone o único repo é o atual.

### 0a. Verificar o test-scope

Se `test-scope` estiver definido no `assets.yaml`:

```
GET https://api.github.com/search/repositories?q=org:<github-org>+topic:<test-scope>&per_page=100
Authorization: Bearer $GITHUB_TOKEN
```

- Colete a lista de `full_name` resultante — é o **conjunto permitido** desta execução.
- Toda a descoberta de repos seguinte (passo 0b) deve ser intersectada com esse conjunto.
- Registre no log: `[test-scope] Restricting to repos with topic '<test-scope>': <lista separada por vírgulas>`
- Se a busca por tópico não retornar nenhum repo, pare e informe: `No repos found with topic '<test-scope>'. Verify the topic is applied in GitHub and the token has read:org scope.`

Se `test-scope` **não** estiver definido, o conjunto permitido não tem restrição.

### 0b. Descobrir os repos de cada ativo

Para cada bloco de ativo, descubra os repos pela busca de prefixo da API do GitHub:

```
GET https://api.github.com/search/repositories?q=org:<github-org>+<repo-prefix>+in:name&per_page=100
Authorization: Bearer $GITHUB_TOKEN
```

- Exige a variável de ambiente `GITHUB_TOKEN` (declarada como `github-api.token-env` no `assets.yaml`) com escopo `read:org`
- Extraia os campos `full_name`; tire o prefixo `<github-org>/` para obter os nomes curtos
- Remova os repos listados em `exclude-repos` daquele ativo
- **Se o test-scope estiver definido:** remova todo repo que NÃO estiver no conjunto permitido do passo 0a

Monte o conjunto final: `repos = {nome-do-repo, branch-padrão}` para todo repo encontrado, no escopo e não excluído.

---

## Passo 1: Verificar o status de onboarding de cada repo descoberto

Um repo está **onboardado** se `.mind/context/overview.md` existir na branch padrão.
Não registre nem persista o status de onboarding no `assets.yaml` — verifique em tempo de execução.

Para cada repo descoberto:
1. Verifique se `.mind/context/overview.md` existe, pela API do GitHub ou por um clone raso
2. Se sim → adicione à **FILA DE SINCRONIZAÇÃO**
3. Se não → pule; registre na descrição do PR como "ainda não onboardado", com link para rodar o `onboard-repo`

```
FILA DE SINCRONIZAÇÃO: repos em que .mind/context/overview.md existe na branch padrão
```

---

## Passo 1.5: Validar o schema do manifest.yaml de cada repo da FILA DE SINCRONIZAÇÃO

> [!IMPORTANT]
> **Rode esta verificação antes de processar qualquer repo.** A skill `update-repo` não consegue corrigir um manifest corrompido — ele está na lista `forbidden`. Um manifest ruim deve ser corrigido por uma pessoa antes que esta skill continue.

Para cada repo da FILA DE SINCRONIZAÇÃO, leia `.mind/manifest.yaml` e verifique a primeira linha que não é comentário:

```bash
head -5 .mind/manifest.yaml | grep -q '^ai-knowledge-base:'
```

- **PASSOU** (`ai-knowledge-base:` encontrado) → siga para o Passo 2 com este repo.
- **FALHOU** (a primeira chave é `schema-version:`, `asset:`, `repo:` ou qualquer outra) → **pule este repo** e emita:

  ```
  ⚠️  SCHEMA INCOMPATÍVEL: <org>/<repo>/.mind/manifest.yaml usa o schema plano antigo.
      O update-repo não consegue corrigir — manifest.yaml está na lista forbidden.
      Ação necessária: peça a uma pessoa que rode `skill:onboard-repo repo:<nome-curto>` para regenerar
      o manifest, ou que o substitua manualmente pelo schema ai-knowledge-base: do template do
      Passo 2 do SKILL.md do onboard-repo.
  ```

  Registre o repo na descrição do PR, numa seção `## ⚠️ Schema Incompatível — Ação Manual Necessária`.

---

## Passo 1.5b: Completar os arquivos de agente

Para cada repo da FILA DE SINCRONIZAÇÃO, verifique se os quatro arquivos de instrução de agente
criados pelos Passos 14a a 14d do `onboard-repo` existem. Crie os que faltarem. Este passo atualiza
repos onboardados com o template antigo sem exigir um novo onboarding completo.

```bash
# Check existence
test -f .mind/agent-bootstrap.md || echo "MISSING: agent-bootstrap.md"
test -f CLAUDE.md                  || echo "MISSING: CLAUDE.md"
grep -q 'mind-managed' .github/copilot-instructions.md 2>/dev/null \
  || echo "MISSING: copilot-instructions.md mind block"
test -f .github/pull_request_template.md || echo "MISSING: pull_request_template.md"
```

**Se `.mind/agent-bootstrap.md` não existir:**
Crie a partir do template do Passo 14a do `onboard-repo`.
- Substitua `<nome-curto>` pelo nome curto real do repo.
- Na seção Skills: leia `.mind/skills/_index.md` para listar as skills específicas do repo.
  Se o `_index.md` não existir ou estiver vazio, escreva `_(nenhuma ainda — veja a skill `onboard-repo`)_` como placeholder.

**Se `.mind/agent-bootstrap.md` existir mas com versão de template antiga:**
1. Leia o marcador `<!-- agent-bootstrap-template-version: N.N -->` no bloco do template do Passo 14a
   dentro de `.mind/skills/onboard-repo/SKILL.md`.
2. Compare com o mesmo marcador dentro do `.mind/agent-bootstrap.md` do repo filho.
3. Se a versão do SKILL.md for mais nova (ou o arquivo do filho não tiver marcador) → regenere o
   `agent-bootstrap.md` a partir do template atual do Passo 14a, substituindo `<nome-curto>` pelo nome
   curto real do repo. Faça stage junto com as outras atualizações do PR deste repo.

**Seja o arquivo novo ou regenerado — preencha sempre a partir do `_index.md`:**
- Leia `.mind/skills/_index.md` no repo filho.
- **Se o `_index.md` não existir ou não tiver a seção `## Arquivos de Contexto Disponíveis`** (formatos
  antigos têm só `## Available Skills` ou o título em inglês `## Available Context Files`):
  - Liste os arquivos de `.mind/` que existem no disco (ex.: `ls .mind/**/*.md`).
  - Recrie a tabela `## Arquivos de Contexto Disponíveis` no `_index.md` a partir desses arquivos, com
    uma descrição de uma linha para cada (tirada do título do arquivo ou da primeira linha não vazia).
  - Salve o `_index.md` atualizado — faça stage no PR junto com as outras mudanças.
  - Use esse `_index.md` recriado como fonte para os passos abaixo.
- Substitua a lista da seção `## Contexto sempre carregado` por TODOS os arquivos da tabela
  "Arquivos de Contexto Disponíveis" do `_index.md` (caminho + descrição), omitindo os que não existem no disco.
- Substitua a linha específica do repo na tabela `## Skills` pelos nomes reais das skills e pelas
  descrições de uma linha da tabela "Skills" do `_index.md`.
- Se o `_index.md` não existir **e** não houver arquivos de `.mind/` no disco, mantenha a lista padrão
  de 6 arquivos do template.

**Se `CLAUDE.md` não existir:**
Crie a partir do template do Passo 14c do `onboard-repo`. Nunca sobrescreva um `CLAUDE.md` existente.

**Se `.github/pull_request_template.md` não existir:**
Copie literalmente de `.mind/_global/instructions/pull_request_template.md`
(baixado para o workspace do repo filho pelo `copilot-setup-steps.yml`).
Se esse arquivo também não existir, use `.mind/instructions/pull_request_template.md`.

Se `.github/pull_request_template.md` já existir mas não tiver a seção Declaração de Uso de IA,
acrescente essa seção a partir do template de origem. Nunca sobrescreva o conteúdo existente do template de PR.

**Se `.github/copilot-instructions.md` não tiver um bloco `<!-- mind-managed`:**
Acrescente o bloco mind-managed do Passo 14b do `onboard-repo` ao final do arquivo.
Se o arquivo não existir, crie-o a partir desse template.
Nunca sobrescreva nem remova conteúdo existente que não seja do mind.

**Se `.github/copilot-instructions.md` já tiver um bloco `<!-- mind-managed`:**
Compare o conteúdo do bloco com o template atual do Passo 14b no SKILL.md do `onboard-repo`.
Se forem diferentes (ex.: instruções atualizadas, linhas acrescentadas/removidas) → substitua só o
conteúdo entre `<!-- mind-managed` e `<!-- end mind-managed block -->` pelo template atual.
Preserve todo o conteúdo que não é do mind, acima e abaixo do bloco.

> Faça stage dos arquivos de agente completados junto com as outras atualizações, no mesmo PR deste repo.

---

## Passo 1.5c: (não usado no modo standalone)

Nenhuma sincronização de templates de workflow é feita.

---

## Passo 2: Ler o conteúdo de `.mind/` de cada repo onboardado

Para cada repo da FILA DE SINCRONIZAÇÃO:

Clone ou busque o repo (use `GITHUB_TOKEN` para repos privados):
```
git clone --depth 1 https://$GITHUB_TOKEN@github.com/<org>/<repo>.git /tmp/<short-name>
cd /tmp/<short-name>
```

**Método padrão de extração — use `rg` (ripgrep), não amostragem de arquivos:**
o `rg` é exaustivo (varre todos os arquivos), reproduzível e está disponível nos runners do GitHub Actions.
Rode os blocos relevantes abaixo antes de ler qualquer arquivo de `.mind/`.

```bash
# === Versions — always run ===
rg 'sourceCompatibility|JavaVersion\.' build.gradle --no-filename 2>/dev/null
rg "id ['\"]org.springframework.boot['\"] version" -g '*.gradle' -o --no-filename 2>/dev/null | head -3

# === Scoped repo dependencies — always run ===
rg '<internal-group-prefix-1>|<internal-group-prefix-2>' -g '*.gradle' --no-filename 2>/dev/null

# === REST entry points ===
rg '@(RestController|Controller)' -g '*.java' -l 2>/dev/null
rg '@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\(' \
  -g '*.java' -n 2>/dev/null | head -40

# === External-interface controller detection ===
# Controllers that implement interfaces from external JARs have their URL paths
# defined in those JAR interfaces — rg cannot see them in local source.
# Detect: list implemented interfaces → subtract locally-defined interfaces → remainder are external.
rg 'class \w+(?:\s+extends\s+\w+)?\s+implements\s+(\w[\w,\s]*)' \
  -g '*.java' -g '*Controller*' \
  -r '$1' -o --no-filename 2>/dev/null | tr ',' '\n' | sed 's/[[:space:]]//g' | sort -u
rg '^\s*(?:public\s+)?interface\s+(\w+)' \
  -g '*.java' -r '$1' -o --no-filename 2>/dev/null | sort -u
# Interfaces in the first list NOT in the second → path defined in external JAR.
# For each: check docs/ and README for the actual path; flag in overview.md as
# <!-- Needs Human Confirmation — path defined in external JAR: <InterfaceName> -->

# === Kafka topics ===
rg 'topics\s*=\s*[\{"]([A-Za-z0-9._\$-]+)' -g '*.java' -r '$1' -o --no-filename 2>/dev/null | sort -u
rg '"name"\s*:\s*"([^"]+)"' -g '*.avsc' -r '$1' -o --no-filename 2>/dev/null | sort -u
rg 'topic' -g '*.yml' -g '*.yaml' -n 2>/dev/null | grep -vi '#' | head -15

# === DB tables ===
rg '@Table\(name\s*=\s*"([^"]+)"' -g '*.java' -r '$1' -o --no-filename 2>/dev/null | sort -u

# === Application config ===
rg 'spring\.application\.name|server\.servlet\.context-path' \
  -g '*.yml' -g '*.yaml' -g '*.properties' -n 2>/dev/null | head -5

# === Configuration reference (mirrors onboard-repo Block B) ===
# All application / bootstrap property files outside /test/
find . -name 'application*.properties' -o -name 'application*.yml' \
       -o -name 'bootstrap*.properties' -o -name 'bootstrap*.yml' \
  | grep -v '/test/' | sort

# All distinct property keys across main resources
rg '^\s*[a-z][\w.-]+\s*[=:]' \
  -g 'application*.properties' -g 'application*.yml' \
  -g 'bootstrap*.properties' -g 'bootstrap*.yml' \
  -g '!**/test/**' -o --no-filename 2>/dev/null | sort -u | head -80

# Profile-specific config files
find . -name 'application-*.properties' -o -name 'application-*.yml' | sort

# @ConfigurationProperties classes
rg '@ConfigurationProperties' -g '*.java' -n 2>/dev/null | head -30

# @Value injections — exact property names the code reads
rg '@Value\(\s*"\$\{([^}]+)\}"' -g '*.java' -r '$1' -o --no-filename 2>/dev/null | sort -u | head -50

# @ConditionalOnProperty / @Profile — feature flags and profile gates
rg '@ConditionalOnProperty|@Profile' -g '*.java' -n 2>/dev/null | head -30

# Environment-variable driven properties
rg '\$\{[A-Z_]{3,}\}|\$\{env\.' -g '*.properties' -g '*.yml' -o --no-filename 2>/dev/null | sort -u | head -20
rg '^ENV ' docker/Dockerfile 2>/dev/null | head -20

# === Enumerated types & strategy catalogue (java-service / java-library only) ===
# Surface every enum that encodes a business rule, mode, or selectable algorithm.
# Skip for angular-app, python-service, db-schema, iac.

# All enum names in non-test Java source
rg '^\s*(public\s+)?enum\s+(\w+)' -g '*.java' -r '$2' -o --no-filename 2>/dev/null | sort -u

# Constants declared inside each enum (non-test files)
rg -g '*.java' -l '^\s*(public\s+)?enum\s+' 2>/dev/null | grep -v 'test\|Test' | while read f; do
  echo "=== $f ==="
  grep -n '^\s*[A-Z][A-Z0-9_]*\s*[,;(]' "$f" | head -30
done

# Factory/switch dispatch on enum or String config values
rg 'switch\s*\(\w*\)|case\s+[A-Z_]{3,}\s*:' \
  -g '*.java' -n 2>/dev/null | grep -v 'test\|Test\|//\|^\s*\*' | head -40

# Concrete strategy/calculator implementations
rg 'class\s+\w+\s+(extends|implements)\s+\w*(Calculat|Round|Strateg|Processor|Evaluator|Resolver|Handler|Provider|Formatter|Converter)\w*' \
  -g '*.java' -o --no-filename 2>/dev/null | sort | head -30
```

Depois leia os arquivos de `.mind/` existentes no repo para comparar com a saída do `rg` (pule sem erro os que não existirem):
- `.mind/context/overview.md` — propósito do componente, pontos de entrada, classes principais, Referência de Configuração
- `.mind/context/domain.md` — glossário de domínio (termos, siglas, contratos)
- `.mind/context/business-logic.md` — fluxos passo a passo, mapa de acesso a dados, cache, tipos enumerados
- `.mind/diagrams/cloud-architecture.md` e `.mind/diagrams/data-flow.md` — implantação, fluxos de requisição e de eventos
- `.mind/topology/dependency-graph.md` — dependências declaradas de compilação/runtime, tópicos, tabelas
- `.mind/topology/external-resources.md` — serviços chamados e consumidores deste repo
- `.mind/devops/overview.md` — pipelines, quality gates, testes
- `.mind/instructions/code-patterns.md` — convenções de nomenclatura, padrões, tabelas de configuração do repo (ex.: configuração de cache)
- `.mind/instructions/security.md` — autenticação, autorização, logging, segredos

São os arquivos criados pelo `onboard-repo` (Passos 3 a 11). Se o repo tiver arquivos extras em
`.mind/` (ex.: `lessons/`, `decisions/`), leia-os como contexto, mas só altere o que `scope.allowed` permite.

Extraia fatos, não opiniões:
- Tipo do componente, propósito, principais APIs/tópicos/tabelas
- Versões de tecnologia (Java, Spring Boot, Gradle)
- Dependências declaradas de outros repositórios do projeto
- Qualquer aviso explícito de descontinuação ou aposentadoria

### Passo 2b: Atualizar `.mind/context/code-graph.md` a partir do grafo gerado

O grafo de código é gerado pelo Tree-sitter no setup e colocado em
`.mind/_global/code-graph.md`. Se esse arquivo existir e for mais novo que o
`code-graph.md` commitado, substitua a versão commitada.

```bash
# Check if the pre-built graph is available
test -f .mind/_global/code-graph.md && echo "GRAPH AVAILABLE" || echo "GRAPH ABSENT"
```

**Se existir**: copie para `.mind/context/code-graph.md` e depois confira/atualize as duas
seções escritas pelo agente (NÃO as sobrescreva às cegas):

- `## Referência de Configuração` — atualize se as chaves de propriedade mudaram
- `## Notas de Implementação Relevantes` — atualize se os padrões de arquitetura mudaram

Se `.mind/context/code-graph.md` ainda não existir no repo (onboarding antigo),
crie do zero seguindo o template do Passo 5b do onboard-repo.

**Se não existir**: deixe o `code-graph.md` existente como está; registre na descrição do PR
que a análise Tree-sitter não estava disponível (implante o `copilot-setup-steps.yml` v3.0).

---

## Passo 3: Identificar as diferenças

Compare os fatos extraídos com o conteúdo atual **deste repo**:

| O que verificar | Onde comparar | Destino da atualização |
|---|---|---|
| Propósito e arquitetura do componente | `.mind/context/overview.md` | Tabela `Onboarding Status` + descrição do componente |
| Versão do Java e do Spring Boot do repo (MindHub) | `topology/repos.md` do MindHub | Linha correspondente na tabela de repos |
| Dependências declaradas do repo | `.mind/topology/dependency-graph.md` | Bloco de dependências daquele repo |
| Nova lição ou padrão encontrado | `.mind/lessons/` | Novo arquivo `.md`, se ainda não documentado |
| Conteúdo de docs/components/ (MindHub) | `docs/components/<repo>/component.md` do MindHub | Substituir as seções desatualizadas (Visão Geral, Entradas, Saídas) |
| Propriedades de configuração | Saída do `rg` vs `## Referência de Configuração` no `overview.md` + tabelas de configuração em `instructions/code-patterns.md` | Atualizar a Referência de Configuração de `docs/components/<repo>/component.md`; se o `.mind/context/overview.md` do próprio repo alvo estiver desatualizado, enfileirar um PR no repo alvo (ver Passo 5b) |
| Perfis Spring / gates `@Profile` | Saída do `rg @Profile` vs tabela de variantes de perfil no `overview.md` | Mesmos destinos da linha de propriedades de configuração acima |
| Interfaces de controllers em JARs externos | Saída da detecção de interfaces externas vs tabela `## Interfaces Externas Principais` no `.mind/context/overview.md` do repo filho | Para cada controller de interface externa recém-detectado que não estiver na tabela, acrescente uma linha com `<!-- Needs Human Confirmation — path defined in external JAR: <NomeDaInterface> -->` via PR no repo alvo (Passo 5b) |
| Tipos enumerados e catálogo de estratégias | Saída da extração de enums vs tabela `## Tipos Enumerados e Catálogo de Estratégias` no `business-logic.md` (só java-service / java-library) | Se a seção não existir, crie; se as constantes ou as classes de despacho mudaram, atualize as linhas. Omita para tipos de repo que não sejam Java. |

**Regras das diferenças:**
- Registre só mudanças sustentadas por evidência dos arquivos-fonte
- Se algo for incerto, marque `<!-- Needs Human Confirmation -->`
- NÃO acrescente arquitetura futura especulativa, funcionalidades "planejadas" nem notas de evolução
- NÃO mexa em `.mind/decisions/`, `.mind/skills/`, `.mind/workflows/`, `.mind/standards/`

---

## Passo 3b: Atualizar `.mind/context/code-graph.md`

**Grafo de código gerado previamente** — não escreva estes arquivos à mão. Eles são produzidos pelo
`mind-code-graph.py` (análise Tree-sitter), que roda no `copilot-setup-steps` antes de o sandbox do
agente começar, e ficam em `.mind/_global/code-graph.md` e `.mind/_global/code-graph.json`.

```bash
ls .mind/_global/code-graph.md 2>/dev/null && echo "code graph available" || echo "absent"
```

### Se `.mind/_global/code-graph.md` existir

Copie literalmente os dois arquivos gerados, Markdown e JSON:

```bash
cp .mind/_global/code-graph.md  .mind/context/code-graph.md
# Also retain the raw JSON for tooling and consolidation workflows
[[ -f .mind/_global/code-graph.json ]] && cp .mind/_global/code-graph.json .mind/context/code-graph.json
```

Acrescente estas duas seções **depois** do conteúdo gerado:

1. **`## Referência de Configuração`** — principais nomes de propriedades e variáveis de ambiente
   tirados da sua fact-sheet do `rg` (só nome da chave + propósito; evite colar blocos YAML inteiros).
2. **`## Notas de Implementação Relevantes`** — 3 a 8 tópicos destacando padrões não óbvios
   (ex.: "Toda escrita no banco é adiada para um consumidor Kafka", "O cache é preenchido sob demanda
   no primeiro miss", "Todas as chamadas de auditoria são síncronas na thread do chamador — risco de performance").

Se `.mind/context/code-graph.md` já existir, **substitua-o por inteiro** pelo novo conteúdo
gerado + as duas seções complementares (a análise Tree-sitter é a fonte oficial e substitui
qualquer versão anterior do arquivo).

### Se `.mind/_global/code-graph.md` não existir

Pule este passo — não crie esboço nem placeholder.

---

## Passo 4: Atualizar `docs/components/<repo>/component.md` no MindHub

Para cada repo sincronizado:

1. Se `docs/components/<nome-curto>/component.md` não existir — crie a partir do template:

```markdown
---
component: <nome-curto>
repo: <nome-completo-do-repo>
owner-team: <detectado no CODEOWNERS ou README>
tech-stack: [<stack detectada>]
type: overview
title: <Título do Componente>
description: <2 a 3 frases: o que o componente faz, quem o chama, o que produz.>
resource: <nome-completo-do-repo>
tags: [overview, <tipo-do-repo>, <id-do-ativo>]
timestamp: <AAAA-MM-DDT00:00:00Z>
depends-on: [<de .mind/topology/dependency-graph.md>]
---

# <Título do Componente>

> **Dono:** <time> | **Repo:** <repo> | **Tipo:** <tipo> | **Última atualização:** <AAAA-MM>

## Visão Geral
<Derivada de .mind/context/overview.md — no máximo 2 a 3 frases>

## Entradas Principais
<Endpoints REST / tópicos Kafka consumidos / leituras no banco>

## Saídas Principais
<Respostas REST / tópicos Kafka produzidos / escritas no banco>

## Tecnologia
<Versão do Java, versão do Spring Boot, frameworks principais>

## Referência de Configuração

> Origem: `application*.properties/yml`, `@ConfigurationProperties` e injeções `@Value`.
> Propriedades injetadas pelo SCC são indicadas na coluna Origem.

| Propriedade | Padrão | Propósito | Origem |
|---|---|---|---|
| `<chave.da.propriedade>` | `<valor ou —>` | <propósito em uma linha> | SCC / variável de ambiente / application.yml |

**Variantes de perfil:**

| Perfil | Arquivo | Propósito |
|---|---|---|
| `<perfil>` | `application-<perfil>.yml` | <o que sobrescreve> |

> Marque `<!-- Needs Human Confirmation -->` nas propriedades cujo padrão ou origem não puder ser confirmado pelo código-fonte.

## Padrões Conhecidos
<De .mind/instructions/code-patterns.md — padrões específicos do repo>
```

2. Se `docs/components/<nome-curto>/component.md` já existir:
   - Atualize só as seções com mudanças factuais
   - Preserve os blocos `<!-- human-maintained -->` sem tocá-los
   - Atualize a data de `Última atualização` no cabeçalho

---

## Passo 5b: Abrir PRs nos repos alvo para divergências de configuração

Depois de processar todos os repos da FILA DE SINCRONIZAÇÃO, para cada repo em que a **Referência de Configuração** mudou (propriedades novas ou removidas detectadas pelo `rg` vs o conteúdo atual de `.mind/context/overview.md`):

1. **Clone** o repo alvo (ou reaproveite o clone do Passo 2)
2. **Atualize** `.mind/context/overview.md` — renove as tabelas de `## Referência de Configuração` com as chaves, padrões e origens recém-extraídos
3. **Atualize** `.mind/instructions/code-patterns.md` — renove as tabelas de configuração embutidas (ex.: tabela de configuração de cache Infinispan, propriedade de dialeto do Hibernate)
4. **Abra um PR** no repo alvo:
   - Branch: `feature/mind-config-sync-<AAAA-MM>`
   - Título: `[mind] Sincronizar Referência de Configuração — <AAAA-MM>`
   - Corpo: liste as propriedades alteradas e qual extração do `rg` as revelou
5. **NÃO** mexa em código-fonte, testes ou arquivos de build do repo alvo
6. **NÃO** sobrescreva nenhuma seção marcada `<!-- human-maintained -->`
7. **NÃO** mexa em `.mind/skills/` do repo filho — as skills locais pertencem ao time do repo e nunca são alteradas por esta skill

> Se o repo alvo já tiver uma branch `feature/mind-config-sync-*` aberta, faça force-push nela em vez de criar uma nova branch.

---

## Passo 5: Atualizar os arquivos de topologia do MindHub

Depois de processar todos os repos da FILA DE SINCRONIZAÇÃO:

**`topology/repos.md`:**
- Atualize as colunas de versão do Java/Spring Boot se uma versão mais nova for detectada
- Acrescente linhas para repos descobertos que ainda não estão listados
- Observação: o status de onboarding é determinado em tempo de execução — não mantenha uma coluna de status aqui

**`topology/dependency-graph.md`:**
- Se o `.mind/topology/dependency-graph.md` de um repo mostrar uma dependência que ainda não está no grafo, acrescente-a
- Se uma dependência listada antes foi removida (não está mais no `build.gradle`), marque-a com `# removed`

**`context/overview.md`:**
- Corrija as descrições de componentes que mudaram de fato

---

## Passo 6: Abrir um PR

Faça stage só dos arquivos de `scope.allowed` acima. Faça o commit com:
```
[update-repo] Sync .mind/ documentation — <date>
```

A descrição do PR deve incluir:
- **Repos sincronizados:** lista dos repos processados
- **Repos pulados (não onboardados):** lista com link para rodar `skill:onboard-repo repo:<nome>`
- **Repos pulados (falha na descoberta):** lista com o motivo
- **Principais mudanças:** lista do que foi atualizado e por quê
- **Itens Needs Human Confirmation:** as seções marcadas como incertas

---

## Limites — NUNCA mexa nestes itens

- Qualquer arquivo de código-fonte (`.java`, `.gradle`, `.xml`, `.ts`, `.py`)
- Qualquer arquivo fora de `scope.allowed`
- Qualquer seção marcada `<!-- human-maintained -->`
- O diretório `.mind/_global/` — contexto de runtime somente leitura baixado pelo `copilot-setup-steps.yml`; nunca deve entrar em stage nem em commit. Antes do stage: `git rm -r --cached .mind/_global/ 2>/dev/null || true`
- O diretório `.mind/decisions/`
- O diretório `.mind/skills/` (no MindHub e em qualquer repo filho — as skills dos times nunca são alteradas)
- O diretório `.mind/workflows/`
- `.gitignore` — o arquivo é do time do repo. A entrada `.mind/_global/` é acrescentada só pelo comando de acréscimo do Passo 0 do corpo da issue, nunca por esta skill.

Na dúvida, deixe um comentário no PR e não altere a seção.
