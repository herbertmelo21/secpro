#!/usr/bin/env bash
set -euo pipefail

# Script para executar arquivo AutoHotkey v2 do WSL no Windows
# Uso: bash scripts/run_vpro_ahk_from_wsl.sh [caminho/para/arquivo.ahk]
#
# Exemplo:
#   bash scripts/run_vpro_ahk_from_wsl.sh                    # usa LA25.ahk padrão
#   bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/LA25.ahk

AHK_FILE="${1:-section/ahk/LA25.ahk}"

# ═══════════════════════════════════════════════════════════════════════════
# 1. VERIFICAR SE O ARQUIVO AHK EXISTE
# ═══════════════════════════════════════════════════════════════════════════

if [[ ! -f "$AHK_FILE" ]]; then
  echo "[ERRO] Arquivo AHK não encontrado: $AHK_FILE"
  echo ""
  echo "Verifique se o caminho está correto. Exemplo:"
  echo "  bash scripts/run_vpro_ahk_from_wsl.sh section/ahk/LA25.ahk"
  exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════
# 2. PROCURAR AUTOHOTKEY V2 NO WINDOWS
# ═══════════════════════════════════════════════════════════════════════════

CANDIDATES=(
  "/mnt/c/Program Files/AutoHotkey/v2/AutoHotkey64.exe"
  "/mnt/c/Program Files/AutoHotkey/AutoHotkey64.exe"
  "/mnt/c/Program Files/AutoHotkey/AutoHotkey.exe"
)

AHK_EXE=""

for exe in "${CANDIDATES[@]}"; do
  if [[ -f "$exe" ]]; then
    AHK_EXE="$exe"
    break
  fi
done

if [[ -z "$AHK_EXE" ]]; then
  echo "[ERRO] AutoHotkey v2 não encontrado no Windows."
  echo ""
  echo "Locais procurados:"
  for exe in "${CANDIDATES[@]}"; do
    echo "  ✗ $exe"
  done
  echo ""
  echo "Solução:"
  echo "  1. Baixe AutoHotkey v2 em: https://www.autohotkey.com/"
  echo "  2. Instale no Windows em: C:\\Program Files\\AutoHotkey"
  echo "  3. Tente novamente"
  exit 1
fi

# ═══════════════════════════════════════════════════════════════════════════
# 3. CONVERTER CAMINHO LINUX PARA WINDOWS
# ═══════════════════════════════════════════════════════════════════════════

AHK_FILE_WIN="$(wslpath -w "$AHK_FILE")"

# ═══════════════════════════════════════════════════════════════════════════
# 4. EXIBIR INFORMAÇÕES E INSTRUÇÕES
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  AutoHotkey v2 - Executando Script AHK do Windows             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Arquivo AHK encontrado:"
echo "   Linux:   $AHK_FILE"
echo "   Windows: $AHK_FILE_WIN"
echo ""
echo "🔧 AutoHotkey encontrado:"
echo "   $AHK_EXE"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 5. INSTRUÇÕES DE USO
# ═══════════════════════════════════════════════════════════════════════════

echo "📋 INSTRUÇÕES:"
echo ""
echo "1. ✓ Certifique-se de que o VPro/SecPro está aberto no Windows"
echo "     e a janela está VISÍVEL"
echo ""
echo "2. ✓ Navegue até a tabela de coordenadas no VPro/SecPro"
echo ""
echo "3. ✓ Clique UMA VEZ no botão \"+\" para criar a PRIMEIRA linha"
echo ""
echo "4. ✓ Clique na célula x(m) da primeira linha"
echo ""
echo "5. ⏳ Aguarde o script AHK carregar (próximo passo)"
echo ""
echo "6. 🔴 Quando o AHK estiver carregado, pressione F8 para iniciar"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 6. EXECUTAR AUTOHOTKEY
# ═══════════════════════════════════════════════════════════════════════════

echo "Carregando script AHK no Windows..."
echo ""

"$AHK_EXE" "$AHK_FILE_WIN" &
AHK_PID=$!

sleep 1

echo "✓ AHK carregado (PID: $AHK_PID)"
echo ""
echo "Agora pressione F8 para preencher as coordenadas."
echo "Para parar o script, pressione Ctrl+C nesta janela ou feche a"
echo "janela do VPro/SecPro."
echo ""

# Manter script em foreground para que Ctrl+C funcione
wait $AHK_PID 2>/dev/null || true

echo ""
echo "✓ Script AHK finalizado."
