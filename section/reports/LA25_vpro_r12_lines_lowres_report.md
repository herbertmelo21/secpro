# Relatorio DXF legacy R12 (r12-lines-lowres) - LA25_vpro_r12_lines_lowres

Fonte: `section/json/LA25.json`
Saida: `section/DXF/LA25_vpro_r12_lines_lowres.dxf`
Writer: `r12-lines-lowres`
Segmentos por semicircunferencia usados na discretizacao: 20

## Selecao da entidade (mesma geometria do preview LA25_vpro.png, sem recalculo)

- Entidade fonte selecionada: LWPOLYLINE index=153 handle=[0, 2, 2713]
- Numero de pontos apos discretizacao/limpeza: 230
- Bounding box local: (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)
- Largura: 1.2501 m
- Altura: 0.2502 m

## Leitura estrutural com ezdxf (versao, entidades, bbox)

- Versao DXF: AC1009 (esperado AC1009)
- Entidades no arquivo: {'LINE': 230}
- (modo LINE: sem conceito de 'fechada' unico)
- Bounding box (ezdxf): (-0.62504023783913, 0.0, 0.62504023783913, 0.2502175179652113)

## Round-trip LibreDWG (dxf2dwg + dwgread -O JSON + jq empty)

- Comandos executados: ['dxf2dwg -y -o section/reports/LA25_vpro_r12_lines_lowres_roundtrip.dwg section/DXF/LA25_vpro_r12_lines_lowres.dxf', 'dwgread -O JSON -o section/reports/LA25_vpro_r12_lines_lowres_roundtrip.json section/reports/LA25_vpro_r12_lines_lowres_roundtrip.dwg', 'jq empty section/reports/LA25_vpro_r12_lines_lowres_roundtrip.json']
- Entidades no round-trip: {'BLOCK': 2, 'ENDBLK': 2, 'LINE': 230}
- Entidades tipo POLYLINE/POLYLINE_2D no round-trip: 0
- Fechada (round-trip): None
- Bounding box (round-trip): None
  - dwgread -O JSON reportou 'ERROR: iconv' (limitacao conhecida do LibreDWG para JSON de origem R12 - ver nota da funcao); comando reportou erro na saida: /usr/local/bin/dwgread -O JSON -o section/reports/LA25_vpro_r12_lines_lowres_roundtrip.json section/reports/LA25_vpro_r12_lines_lowres_roundtrip.dwg
veja log em section/reports/LA25_vpro_r12_lines_lowres_roundtrip.dwgread.log
  - jq empty / json.load: OK - validado com jq

Preview gerado em `section/preview/LA25_vpro_r12_lines_lowres.png`.

**Resultado: estrutura OK - VPRO legacy candidate (NAO declarar VPRO-safe; validar importando no VPRO antes de confiar neste arquivo)**
