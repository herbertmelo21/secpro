# Teste manual recomendado - variantes 20-gon da LA25

## 1. AutoCAD (REGION / SUBTRACT / MASSPROP)

Arquivo: `section/DXF/LA25_region_r12_20gon.dxf`

1. Abrir o DXF no AutoCAD (ou compativel).
2. Selecionar as 6 POLYLINE (1 contorno externo + 5 furos) e rodar `REGION`.
3. Rodar `SUBTRACT`: selecionar a regiao do contorno externo como objeto-fonte, e as 5
   regioes dos furos como objetos a subtrair.
4. Rodar `MASSPROP` na regiao resultante e conferir:
   - Area: comparar com `section/reports/LA25_region_r12_20gon_report.md`
     (secao "Comparacao com 5 furos circulares ideais").
   - Centroide.
   - Momentos de inercia (Ix, Iy).

## 2. VPRO

Testar nesta ordem:

1. `section/DXF/LA25_vpro_slots_r12_20gon_5mm.dxf` (fenda mais larga, 5 mm).
2. `section/DXF/LA25_vpro_slots_r12_20gon_2mm.dxf` (fenda mais estreita, 2 mm).

Para cada um, observar:
- O VPRO consegue importar sem erro?
- A secao aparece com os 5 furos poligonais corretamente reconhecidos como vazios (nao
  como material)?
- Ha diferenca perceptivel de comportamento entre a fenda de 5 mm e a de 2 mm?

Reportar o resultado da comparacao 2mm vs 5mm para decidir qual largura de fenda usar
daqui para frente.

Nenhum destes arquivos deve ser chamado de "VPRO-safe" antes desse teste manual -
apenas "VPRO legacy candidate" (round-trip LibreDWG e leitura ezdxf OK, mas o VPRO em si
ainda nao foi testado).
