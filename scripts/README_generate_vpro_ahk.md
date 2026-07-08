# Generate VPro AHK from LibreDWG JSON

Script Python que converte JSONs do LibreDWG em scripts AutoHotkey v2 para automatizar entrada de coordenadas no VPro/SecPro.

## Funcionalidade

1. **Leitura de JSONs**: Processa recursivamente por LWPOLYLINE em arquivos JSON do LibreDWG
2. **Seleção de polilinha**: Escolhe a LWPOLYLINE com maior número de pontos
3. **Expansão de arcos**: Converte bulges em segmentos retos usando:
   - `theta = 4 * atan(bulge)`
   - `radius = chord / (2 * sin(theta/2))`
   - Discretiza cada arco em N segmentos
4. **Normalização de coordenadas**:
   - `x0 = (xmin + xmax) / 2`
   - `y0 = ymin`
   - Resultado: `(x - x0, y - y0)`
5. **Remoção de duplicatas**: Remove pontos consecutivos duplicados
6. **Formato brasileiro**: Converte para vírgula decimal (ex.: `0,300`)
7. **Geração de script AHK**: Cria hotkey F8 para digitar coordenadas no VPro

## Uso

### Uso padrão
```bash
python3 scripts/generate_vpro_ahk_from_libredwg.py
```

Processa todos os JSONs em `section/json/` e gera AHKs em `section/ahk/`.

### Com parâmetros customizados
```bash
python3 scripts/generate_vpro_ahk_from_libredwg.py \
  --input-dir section/json \
  --output-dir section/ahk \
  --segments-per-arc 30 \
  --decimals 4
```

### Parâmetros

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--input-dir` | `section/json` | Diretório com JSONs do LibreDWG |
| `--output-dir` | `section/ahk` | Diretório para salvar AHKs gerados |
| `--segments-per-arc` | `20` | Número de segmentos por arco (maior = mais preciso) |
| `--decimals` | `3` | Casas decimais no formato brasileiro |

## Estrutura dos arquivos AHK gerados

Cada arquivo `.ahk` contém:

```autohotkey
#Requires AutoHotkey v2.0
SetKeyDelay(30, 30)

; Coordenadas do botão "+"
PLUS_X := 38
PLUS_Y := 137

; Modo de navegação: "tab_tab", "down_left" ou "click_x_cell"
AFTER_PLUS_MODE := "click_x_cell"

; Constantes para modo "click_x_cell"
X_CELL_X := 135
X_CELL_Y_FIRST := 181
ROW_HEIGHT := 19

coords := [
    ["0,300", "0,000"],
    ["0,400", "0,150"],
    ...
]

F8:: {
    CoordMode("Mouse", "Window")
    for i, row in coords {
        SendText(row[1])
        Send("{Tab}")
        SendText(row[2])
        if i < coords.Length {
            Click(PLUS_X, PLUS_Y)
            Sleep(80)
            
            ; 3 modos de navegação configuráveis
            if AFTER_PLUS_MODE = "tab_tab" {
                Send("{Tab}")
                Send("{Tab}")
            }
            else if AFTER_PLUS_MODE = "down_left" {
                Send("{Down}")
                Send("{Left}")
            }
            else if AFTER_PLUS_MODE = "click_x_cell" {
                clickY := X_CELL_Y_FIRST + (i - 1) * ROW_HEIGHT
                Click(X_CELL_X, clickY)
                Sleep(50)
            }
        }
    }
}
```

### Modos de Navegação

O script AHK gerado oferece **3 modos configuráveis** para navegar após criar uma nova linha:

| Modo | Comando | Vantagem | Desvantagem |
|------|---------|----------|------------|
| `"tab_tab"` | `Send("{Tab}")` x2 | Simples, rápido | Pode falhar se grid tiver foco especial |
| `"down_left"` | `Send("{Down}")`, `Send("{Left}")` | Alternativa com setas | Menos previsível que Tab/Click |
| `"click_x_cell"` | Clica direto na célula | ⭐ **Mais robusto e preciso** | Requer calibração com Window Spy |

**Modo padrão**: `"click_x_cell"` (recomendado)

Se o script não funcionar bem, edite `AFTER_PLUS_MODE` no arquivo `.ahk` e tente outro modo.

## Como usar o script AHK no VPro/SecPro

1. Instale [AutoHotkey v2](https://www.autohotkey.com/) na máquina Windows
2. Abra o VPro/SecPro e navegue até a seção onde deseja inserir coordenadas
3. Clique UMA VEZ no botão "+" para criar a primeira linha
4. Clique na célula **x(m)** da linha 1
5. Pressione **F8** no teclado
6. O script digitará todas as coordenadas automaticamente

### Ajuste de posição do clique

Se o clique no botão "+" não acertar, use o **Window Spy** do AutoHotkey:

1. Abra AutoHotkey → Tools → Window Spy
2. Mova o mouse sobre o botão "+" no VPro
3. Anote os valores `X` e `Y` mostrados
4. Edite o arquivo `.ahk` e atualize:
   ```autohotkey
   PLUS_X := 38      ; altere para o valor X correto
   PLUS_Y := 137     ; altere para o valor Y correto
   ```

## Funções do script Python

### `find_lwpolylines(obj)`
Procura recursivamente por objetos com `"entity": "LWPOLYLINE"` no JSON.

**Retorna**: Lista de dicionários LWPOLYLINE encontrados.

### `arc_points_from_bulge(p1, p2, bulge, n)`
Expande um arco (definido por bulge) em N segmentos retos.

**Entrada**:
- `p1`: Ponto inicial (x, y)
- `p2`: Ponto final (x, y)
- `bulge`: Valor de bulge do segmento
- `n`: Número de segmentos

**Retorna**: Lista de pontos que descrevem o arco

### `expand_polyline(points, bulges, segments_per_arc)`
Expande polilinha inteira, convertendo arcos em segmentos.

**Retorna**: Lista de pontos 2D

### `dedup(points, tol=1e-9)`
Remove pontos consecutivos duplicados.

**Retorna**: Lista de pontos sem duplicatas

### `fmt_br(x, decimals)`
Formata número com padrão brasileiro (vírgula decimal).

**Exemplo**: `fmt_br(0.3, 3)` → `"0,300"`

### `normalize(coords)`
Normaliza coordenadas para ficarem próximas da origem.

**Retorna**: Lista de coordenadas normalizadas

### `generate_ahk(coords, decimals)`
Gera código AutoHotkey v2 com hotkey F8.

**Retorna**: String com conteúdo completo do arquivo `.ahk`

## Exemplo de saída

```
Processando 2 arquivo(s) de section/json...
[OK] LA25.json → LA25.ahk (130 pontos)
[WARN] Nenhuma LWPOLYLINE encontrada em section/json/coordenada_la26.json

Arquivos AHK gerados em: /home/user/projects/secpro/section/ahk
```

## Notas importantes

- **Precisão**: Aumentar `--segments-per-arc` gera mais pontos (mais preciso mas mais lento no VPro)
- **Formato**: Sempre usa vírgula decimal (padrão brasileiro), independente do locale do sistema
- **Validação**: Se nenhuma LWPOLYLINE for encontrada, o arquivo AHK não é gerado
- **Deduplicação**: Pontos duplicados são removidos automaticamente
- **Fechamento**: Se o último ponto for igual ao primeiro, é removido automaticamente

## Troubleshooting

### Nenhuma LWPOLYLINE encontrada
- Verifique se o JSON é de fato um arquivo LibreDWG convertido
- Use `jq` ou similar para inspecionar a estrutura do JSON:
  ```bash
  grep -i "LWPOLYLINE" section/json/*.json
  ```

### Coordenadas fora de escala
- Verifique a unidade do DXF original (`$INSUNITS` nos DXF)
- A normalização assume que as coordenadas estão em metros

### Script AHK não funciona corretamente

#### Problema: Clique no "+" não acerta a posição
1. Use Window Spy do AutoHotkey para encontrar as coordenadas exatas
2. Edite `PLUS_X` e `PLUS_Y` no arquivo `.ahk`
3. Tente novamente pressionando F8

#### Problema: Navegação falhando após criar linha
1. Tente mudar `AFTER_PLUS_MODE`:
   - Padrão: `"click_x_cell"` (mais preciso)
   - Alternativa 1: `"tab_tab"` (usa Tab)
   - Alternativa 2: `"down_left"` (usa setas)

2. Se escolher `"click_x_cell"`, calibre as constantes com Window Spy:
   - `X_CELL_X`: posição X da célula x(m)
   - `X_CELL_Y_FIRST`: posição Y da primeira linha
   - `ROW_HEIGHT`: altura de cada linha (diference entre Y de linhas consecutivas)

#### Problema: Digitação muito rápida ou lenta
- Aumente `SetKeyDelay(30, 30)` se o VPro não conseguir acompanhar
- Diminua se parecer lento demais
- Exemplo: `SetKeyDelay(50, 50)` para mais lento

#### Problema: Clique no "+" muito lento ou rápido
- Edite `Sleep(80)` após `Click(PLUS_X, PLUS_Y)`
- Aumente para 150-200ms se o grid não responder rápido o suficiente
- Diminua para 50ms se parecer muito lento

## Histórico

- **v1.0** (2026-07-08): Versão inicial
  - Suporte a LWPOLYLINE com bulges
  - Normalização de coordenadas
  - Formato brasileiro (vírgula decimal)
  - Hotkey F8 para entrada automática no VPro
