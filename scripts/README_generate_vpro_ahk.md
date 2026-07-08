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

PLUS_X := 38
PLUS_Y := 137

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
            Send("{Tab}")
            Send("{Tab}")
        }
    }
}
```

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

### Clique no "+" não funciona
- Use Window Spy para ajustar `PLUS_X` e `PLUS_Y`
- Aumente `SetKeyDelay(30, 30)` se o VPro não conseguir acompanhar a digitação
- Aumente `Sleep(80)` se o clique no "+" não funcionar

## Histórico

- **v1.0** (2026-07-08): Versão inicial
  - Suporte a LWPOLYLINE com bulges
  - Normalização de coordenadas
  - Formato brasileiro (vírgula decimal)
  - Hotkey F8 para entrada automática no VPro
