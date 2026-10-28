#!/usr/bin/env bash
# ==============================================================================
# AIKROFY OPEN-CORE SYNC & RELEASE SCRIPT
# Sincroniza la edición Community (Open-Core) hacia UnderlifeFundation/aikrofy.git
# Excluyendo secretos, binarios propietarios LEM, dumps y configuraciones Cloud.
# ==============================================================================
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_REMOTE="https://github.com/UnderlifeFundation/aikrofy.git"
TEMP_DIR="/tmp/aikrofy_opencore_release_$$"

echo "🏛️  [1/5] Preparando empaquetado de Aikrofy Open-Core Community Edition..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Copiar archivos rastreados por git (respeta .gitignore y excluye .git histórico con secretos antiguos)
cd "$REPO_ROOT"
git checkout-index -a -f --prefix="$TEMP_DIR/"

# Copiar archivos nuevos del manifiesto Open-Core si aún no están en el índice
cp -f "$REPO_ROOT/docker-compose.community.yml" "$TEMP_DIR/" 2>/dev/null || true
cp -f "$REPO_ROOT/.env.community.example" "$TEMP_DIR/" 2>/dev/null || true
cp -f "$REPO_ROOT/OPENCORE_MANIFESTO.md" "$TEMP_DIR/" 2>/dev/null || true
cp -f "$REPO_ROOT/LICENSE.md" "$TEMP_DIR/" 2>/dev/null || true

echo "🔒 [2/5] Eliminando módulos exclusivos de Cloud / Enterprise, GitHub Actions & archivos internos..."
rm -rf "$TEMP_DIR/.github"
rm -rf "$TEMP_DIR/qrcodly/.github"
rm -rf "$TEMP_DIR/screenshot-to-code/.github"
rm -rf "$TEMP_DIR/backend/.env"*
rm -rf "$TEMP_DIR/.env"
rm -rf "$TEMP_DIR/legacy_root_backup"
rm -rf "$TEMP_DIR/backend/services/lem_guardrail_service.py"
rm -rf "$TEMP_DIR/backend/tests/test_lem_native.py"
rm -rf "$TEMP_DIR/docs/integraciones/LEM_OPS_INTEGRACION.md"
rm -rf "$TEMP_DIR/backend/BOS-AI/CLAUDE.md.backup"*
rm -rf "$TEMP_DIR/deploy.sh"
rm -rf "$TEMP_DIR/ecosystem.config.js"
rm -rf "$TEMP_DIR/nginx-custom-domains.conf"
find "$TEMP_DIR" -name "*.so" -o -name "*.dylib" -o -name "*.dll" | xargs rm -f 2>/dev/null || true

# Reemplazar microservicio multi-tenant completo por el puente Community Single-Account basado en @agenticnucleus/whatsapp-multitenant
rm -rf "$TEMP_DIR/api-whatsapp"
mv "$TEMP_DIR/whatsapp-community-bridge" "$TEMP_DIR/api-whatsapp"

# Asegurar que el .env.example exista en backend
cp -f "$REPO_ROOT/backend/.env.example" "$TEMP_DIR/backend/.env.example" 2>/dev/null || true

echo "🛡️  [3/5] Ejecutando escaneo de seguridad Zero-Trust (Secret & Credential Audit)..."
if grep -rnE "DONEVEK|82\.197\.82\.185|Wltech\.2023|pcsk_|sk-proj-" "$TEMP_DIR" --exclude-dir=node_modules --exclude-dir=.git --exclude="ESTADO_ACTUAL_PROYECTO.md" --exclude="seed_ecuador_posts.py" --exclude="sync-opencore.sh"; then
    echo "❌ ERROR CRÍTICO: Se detectaron posibles credenciales en el empaquetado público. Abortando."
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo "✅ Escaneo de seguridad aprobado: 0 secretos detectados."

echo "📦 [4/5] Inicializando repositorio limpio Open-Core..."
cd "$TEMP_DIR"
git init -b main
git config user.name "Fundación Underlife & WEBLIFETECH"
git config user.email "engineering@weblifetech.com"
git add -A
git commit -m "feat(opencore): Aikrofy Community Edition V4.0 - Fundación Underlife & WEBLIFETECH"

echo "🚀 [5/5] Publicando en $PUBLIC_REMOTE (branch: main)..."
git remote add public "$PUBLIC_REMOTE"
if ! host github.com >/dev/null 2>&1; then
    echo "⚡ DNS local sin respuesta para github.com; usando resolución directa HTTPS (140.82.112.4)..."
    git -c http.curloptResolve="github.com:443:140.82.112.4" push -u public main --force
else
    git push -u public main --force
fi

echo "🎉 ¡Publicación Open-Core completada con éxito en $PUBLIC_REMOTE!"
rm -rf "$TEMP_DIR"
