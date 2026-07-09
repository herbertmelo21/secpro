# Black-box findings — VPRO/SecPro (caderno de laboratório)

Registro de engenharia reversa por caracterização (characterization testing)
do comportamento do VPRO/SecPro. Cada achado tem um **status**:

- **CONFIRMADO** — observado diretamente no VPRO real, reproduzível.
- **HIPÓTESE** — premissa de trabalho consistente com as observações, mas o
  mecanismo interno não foi verificado.
- **NÃO CARACTERIZADO** — comportamento observado sem explicação de causa.
- **PENDENTE** — próximo experimento a executar.

Evidência primária: `outputs/autohotkey/LA25_draw_polyline_simplified.log`
(o AHK roda pelo caminho UNC `\\wsl.localhost\...`, então `A_ScriptDir` cai
dentro do repo e o log fica gravado no WSL — funciona como flight recorder
de cada tentativa; arquivo ignorado pelo Git, achados transcritos aqui).

---

## 1. Geometria aceita pelo VPRO

### 1.1 Uma única poligonal caminhável — CONFIRMADO (fluxo manual)
O VPRO ("Seção poligonal") só aceita a seção como UMA polilinha contínua,
desenhada ponto a ponto como à mão: cada ponto continua a borda a partir do
anterior. Foi assim que o preenchimento manual histórico funcionou.

### 1.2 Alvéolos NUNCA como loops fechados independentes — CONFIRMADO (premissa validada)
Os 5 alvéolos da LA25 não são furos separados: a borda desce por um canal
("furinho") de **1 mm**, contorna o alvéolo por dentro e volta pelo mesmo
canal. Fechar o alvéolo como CIRCLE/ARC/loop separado quebra a importação.
O canal é intencional e não pode ser "corrigido".

### 1.3 Ordenação por ângulo/centróide gera cordas — CONFIRMADO (negativo)
Reordenar vértices por ângulo em torno do centróide cria segmentos
atravessando o interior (cordas). O VPRO valida incrementalmente e rejeita.
Sessão de 2026-07-08 produziu artefatos assim; foram removidos
(commits `e6105e1`/`aa243a4`).

### 1.4 Rota DXF: R12 com 1 POLYLINE, sem CIRCLE/ARC/bulge — HIPÓTESE
Toda a família de writers R12 (`process_vpro_dxf.py`) existe sob a premissa
de que o importador DXF do VPRO prefere POLYLINE 2D única, discretizada
(sem bulge), AC1009. **A importação de DXF no VPRO real nunca foi
confirmada nesta investigação** — a rota operacional atual é o AHK.

---

## 2. Grid de coordenadas (tela "Seção poligonal")

### 2.1 Tab embaralha x/y — CONFIRMADO (2026-07-09, ~10:00)
Navegar com `Tab` entre células NÃO segue x→y→(próxima linha)x. Resultado
observado: linha 2 recebia y1 em x, x2 em y, e assim por diante (defasagem
em cascata). Correção que funciona: **setas** — digitar x, `{Right}`,
digitar y, `{Down}` + `{Left}` para a próxima linha.

### 2.2 Digitar durante criação/validação de linha perde pontos — CONFIRMADO (09:46)
No modo "cria linha e digita em seguida", o VPRO ainda estava
validando/criando a linha quando o script continuava: células ficavam com
x preenchido e y vazio, ou o valor caía na linha errada (ex.: x do ponto 12
aparecendo na linha 10). Correção: **duas fases** — criar TODAS as linhas
primeiro (`+` N−1 vezes, pausa de **700 ms** por clique), depois preencher.

### 2.3 Cadência segura de criação de linha ≈ 700 ms — CONFIRMADO
Fase 1 com 189 cliques no `+` levou ~2min14s (≈710 ms/linha) duas vezes,
sem perda aparente de linha (log 10:10 e 10:28).

### 2.4 Limite prático de pontos: para de aceitar perto de ~180 — NÃO CARACTERIZADO
Dois runs completos de 190 linhas (10:10–10:17 e 10:28–10:35) terminaram
com o AHK reportando sucesso, mas a tabela **parou de aceitar valores por
volta do ponto 180**. Causa desconhecida (limite de linhas do grid? do
modelo? viewport?). **Decisão operacional: trabalhar com ≤160 pontos.**
O artefato atual (`section/ahk/LA25.ahk`) tem **150 pontos** — margem de ~30.

### 2.5 Viewport após criar 190 linhas — NÃO CARACTERIZADO
Após 189 inserções, o clique em (135, 181) iniciou o preenchimento na
linha 1 e a ordem saiu correta (até o teto do item 2.4). Sugere que o
viewport permanece no topo durante inserções, mas o mecanismo não foi
investigado. Não depender disso além do fluxo atual.

### 2.6 Formato de entrada — CONFIRMADO (precedente manual + runs)
- Vírgula decimal pt-BR (`0,441`), 3 casas decimais.
- Título da janela: `Seção poligonal` (match parcial).
- Preparação manual antes do F8: criar a linha 1 no `+` e clicar na célula
  x(m) da linha 1 (instruções do `run_vpro_ahk_from_wsl.sh`).

### 2.7 Linha de fechamento (último ponto = primeiro) — HIPÓTESE
O AHK repete o 1º ponto na última linha (precedente do fluxo manual que
funcionou). Não caracterizado se o VPRO exige, tolera ou auto-fecha.
Observar na próxima validação.

---

## 3. Interpretação de pontos e geometria

### 3.1 190 pontos geometricamente bons ≠ variante operacional
A variante de 190 pontos (erro de área 0,010%) é geometricamente excelente,
mas **não é a variante final** enquanto o teto prático do VPRO for ~180:
a variante operacional é a de **150 pontos** (`--max-vpro-points 160`,
circle_points=24, erro de área 0,0102%, Ix 0,0082%, Iy 0,0089%).

### 3.2 Resolução do grid = 3 casas (1 mm)
Vértices a menos de 1 mm colidem após arredondamento; o gerador remove
linhas consecutivas idênticas (1 colisão na LA25). O canal de 1 mm
(0,440 vs 0,441) sobrevive exatamente na resolução do grid.

---

## 4. Cronologia dos experimentos (log de 2026-07-09)

| Hora | Variante | Estratégia | Resultado |
|---|---|---|---|
| 09:46 | 190 pts | legado (cria linha + digita) | abortado ~75; perdia/embaralhava pontos |
| 10:00 | 190 pts | precreate + **Tab** | abortado ~25; Tab embaralha x/y |
| 10:10 | 190 pts | precreate + **setas** | completo em 7min35s; ordem correta; parou de aceitar ~180 |
| 10:28 | 190 pts | precreate + setas | reproduzido: completo, mesmo teto ~180 |
| — | **150 pts** | precreate + setas | **PENDENTE — nunca executado** (não existe `section/ahk/LA25.log`) |

---

## 5. Apêndice — armadilhas do AutoHotkey v2 (tooling, não VPRO)

- `for i := 2 to total` não existe em v2 → usar `Loop (total - 1)` + `A_Index`.
- Função e variável global com mesmo nome colidem (case-insensitive):
  `Abortar`/`abortar` quebrou → renomeado `AbortarExecucao`/`g_abort`.
- Erro `Missing "` num `ToolTip` com string longa/símbolos foi resolvido
  simplificando a string para ASCII — **causa raiz não confirmada**;
  manter strings do template simples por segurança.
- `MsgBox` em v2 usa `(texto, título, opções)` — a ordem do v1 quebra.
- Executar o .ahk direto do caminho UNC do WSL funciona e faz o log cair
  no repo (útil como registro de experimento).

---

## 6. Próximos experimentos (PENDENTE)

1. **Rodar `section/ahk/LA25.ahk` (150 pts)** e conferir visualmente as
   150 linhas no VPRO — critério de release (questionário I.1).
2. Conferir se A/Ix/Iy calculados pelo VPRO batem com
   `section/reports/LA25_vpro_limited_160.md`.
3. Caracterizar o teto: testar 160, 170, 175 linhas para achar o limite
   exato (bisseção) — só depois de o fluxo de 150 estar validado.
4. Observar o comportamento da linha de fechamento (item 2.7).
5. (Opcional) Testar a rota DXF importando
   `section/DXF/LA25_vpro_simplified_160.dxf` — decidiria o item 1.4.
