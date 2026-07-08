# Relatorio VPRO-safe DXF - LA25

Fonte: `/tmp/LA25_test.json`
Saida: `section/DXF/LA25_vpro.dxf`

## Selecao da entidade

- Entidade selecionada: LWPOLYLINE index=153 handle=[0, 2, 2713]
- Entidades ignoradas (nao LWPOLYLINE): {'BLOCK': 3, 'ENDBLK': 3, 'LINE': 1}

## Geometria original

- Numero original de pontos (vertices): 39
- Numero original de bulges: 39 (nao-zero: 9)
- Bounding box original (vertices, coords absolutas do DWG): (3725.436076946484, 1753.68192361816, 3726.686157422162, 1753.9321411361252)
- Bounding box original apos discretizar arcos (coords absolutas): (3725.436076946484, 1753.68192361816, 3726.686157422162, 1753.9321411361252)
- Numero final de pontos apos discretizacao e limpeza: 1030

## Ordenacao VPRO-safe

- Numero de pontos na polilinha final: 1030
- Area orientada ANTES da reordenacao: -0.181811
- Area orientada DEPOIS da reordenacao: -0.181811
- Ponto inicial (superior esquerdo): (0.599999, 0.250218)
- Sentido: horario (CW)
- Maior salto entre pontos consecutivos: 1.200071 m (entre ponto 1029 e 0)

## Geometria local (sem escala aplicada)

- Bounding box local: (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)
- Largura: 1.2501 m
- Altura: 0.2502 m

## Validacao geometrica (local, pos-reordenacao)

  - OK - sem pontos consecutivos coincidentes
  - OK - sem segmentos de comprimento zero

## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON)

- Comandos executados: ['dxf2dwg -y -o /tmp/process_vpro_dxf_jnshtz3m/LA25_vpro.dwg section/DXF/LA25_vpro.dxf', 'dwgread -O JSON -o /tmp/process_vpro_dxf_jnshtz3m/LA25_vpro.json /tmp/process_vpro_dxf_jnshtz3m/LA25_vpro.dwg']
- Entidades no DXF final (round-trip): {'BLOCK': 2, 'ENDBLK': 2, 'LWPOLYLINE': 1}
- LWPOLYLINE no round-trip: 1
- Fechada (closed): True
- Bounding box (round-trip): (-0.62504023783913, 0.0, 0.62504023783913, 0.25021751796521)
  - dxf2dwg AVISO (conhecido, nao fatal): 'Duplicate handle' no dicionario ACAD_MATERIAL padrao do ezdxf (nao relacionado a geometria da secao); rc=0 e DWG gerado normalmente - ver section/reports/LA25_vpro.dxf2dwg.log
  - validacao JSON (jq/json.load): OK - validado com jq
  - round-trip: OK - sem pontos consecutivos coincidentes
  - round-trip: OK - sem segmentos de comprimento zero

Preview gerado em `section/preview/LA25_vpro.png`.

Imagem de validacao VPRO-safe gerada em `section/reports/LA25_vpro_safe_order.png`.
CSV com coordenadas gerado em `section/reports/LA25_vpro_safe_coords.csv`.

**Resultado: PASSOU - VPRO-safe**
