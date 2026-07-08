# Relatorio - LA25_region_r12_20gon.dxf

Fonte: `section/json/LA25.json`
Saida: `section/DXF/LA25_region_r12_20gon.dxf`
Finalidade: REGION / SUBTRACT / MASSPROP no AutoCAD; referencia geometrica simples.

## Geometria

- Centro vertical (y_c) usado (validado a partir do arco original): 0.125105 m
- Centros horizontais nominais usados: [-0.4625, -0.23125, 0.0, 0.23125, 0.4625]
- Centros horizontais computados a partir da fonte (para conferencia): [(-0.43954, 0.12504), (-0.22053, 0.12507), (-2e-05, 0.1251), (0.22, 0.12514), (0.44001, 0.12517)]
- Raio nominal usado: 0.098 m (raio computado na fonte: ~0.0850 m - a tarefa pede o nominal, nao o exato)
- Poligono por alveolo: 20 lados
- Numero de pontos do contorno externo: 24
- Numero de pontos por furo (20-gon): 20

## Leitura estrutural com ezdxf

- Versao DXF: AC1009
- Entidades: {'POLYLINE': 6}
- POLYLINE: 6 (esperado 6)
- Fechadas: [True, True, True, True, True, True]
- Bounding box: (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)

## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)

- Comandos executados: ['dxf2dwg -y -o section/reports/LA25_region_r12_20gon_roundtrip.dwg section/DXF/LA25_region_r12_20gon.dxf', 'dwgread -O JSON -o section/reports/LA25_region_r12_20gon_roundtrip.json section/reports/LA25_region_r12_20gon_roundtrip.dwg', 'jq empty section/reports/LA25_region_r12_20gon_roundtrip.json']
- Entidades no round-trip: {'BLOCK': 2, 'ENDBLK': 2, 'POLYLINE_2D': 6, 'SEQEND': 6, 'VERTEX_2D': 124}
- POLYLINE/POLYLINE_2D no round-trip: 6
- Fechadas (round-trip): [True, True, True, True, True, True]
- SEQEND: 6, VERTEX: 124
  - dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG para JSON de origem R12, ver process_vpro_dxf.roundtrip_validate_r12): comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o section/reports/LA25_region_r12_20gon_roundtrip.json section/reports/LA25_region_r12_20gon_roundtrip.dwg
veja log em section/reports/LA25_region_r12_20gon_roundtrip.dwgread.log
  - jq empty / json.load: OK - validado com jq

## Shapely (Polygon com furos)

- Valido (is_valid): True
- Area: 0.147130 m^2
- Centroide: (-2.655362580965275e-05, 0.12334968283274478)

## Comparacao com 5 furos circulares ideais (diametro 0.196 m)

- Area (20-gon): 0.147130 m^2
- Area (circulo ideal): 0.144667 m^2
- Erro relativo de area: 1.7026%
- Centroide (20-gon): (-2.655362580969946e-05, 0.12334968283274525)
- Centroide (circulo ideal): (-2.7005730907790485e-05, 0.12331978892590023)
- Ix (20-gon): 1.22459887e-03 m^4
- Ix (circulo ideal): 1.21287950e-03 m^4
- Erro relativo de Ix: 0.9662%
- Iy (20-gon): 1.82983747e-02 m^4
- Iy (circulo ideal): 1.80232252e-02 m^4
- Erro relativo de Iy: 1.5266%

Preview gerado em `section/preview/LA25_region_r12_20gon.png`.

**Resultado: estrutura OK**
