# Relatorio de validacao de secoes

## LA25.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): OK - dxf2dwg + dwgread -O JSON OK, JSON valido
- Entidades: {'LINE': 1, 'LWPOLYLINE': 1}
- LWPOLYLINE: 1
- CIRCLE: False, ARC: False, LINE: True
- $INSUNITS: 4 (6 = metros)
- Bounding box: x=[3725.4361, 3726.6862] y=[1753.6819, 1753.9321] (largura=1.2501 m, altura=0.2502 m)
- AVISO: \$INSUNITS diferente de 6 (metros) - conferir unidade do desenho.
  - ERRO: pontos consecutivos coincidentes nos indices [1, 6, 11, 16]
  - ERRO: segmentos de comprimento zero nos indices [1, 6, 11, 16]

**Resultado: FALHOU**

## coordenada_la26.dxf

- Round-trip LibreDWG (dxf2dwg + dwgread -O JSON): OK - dxf2dwg + dwgread -O JSON OK, JSON valido
- Entidades: {'LWPOLYLINE': 1}
- LWPOLYLINE: 1
- CIRCLE: False, ARC: False, LINE: False
- $INSUNITS: 6 (6 = metros)
- Bounding box: x=[-0.6250, 0.6250] y=[0.0000, 0.2650] (largura=1.2500 m, altura=0.2650 m)
  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero

### Checagens especificas LA26
  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero
  - OK - largura 1.2500 m dentro da tolerancia de 1.25 m
  - OK - altura 0.2650 m dentro da tolerancia de 0.265 m
  - OK - sem diagonais grandes conectando alveolos
  - AVISO: 6 recortes/alveolos detectados, esperado 5 (heuristica de contagem, revisar visualmente se divergente)

**Resultado: PASSOU**

