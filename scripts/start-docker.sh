#!/bin/bash
# =============================================================
# start-docker.sh
# 打开项目时自动检查并启动 Docker 和 docker-compose 服务
# =============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

# 核心 compose 服务，用于判断是否已在运行
CORE_SERVICE="postgres"

# ─── 颜色输出 ────────────────────────────────────────────────
info()    { echo "[INFO]  $*"; }
success() { echo "[OK]    $*"; }
warn()    { echo "[WARN]  $*"; }
error()   { echo "[ERROR] $*" >&2; }

# ─── 1. 检查 Docker daemon ───────────────────────────────────
check_docker() {
    docker info &>/dev/null
}

start_docker() {
    info "Docker 未运行，尝试启动..."

    # WSL2 环境下优先用 service，fallback 到 systemctl
    if command -v service &>/dev/null; then
        sudo service docker start
    elif command -v systemctl &>/dev/null; then
        sudo systemctl start docker
    else
        error "无法自动启动 Docker，请手动启动 Docker Desktop 后重试。"
        exit 1
    fi

    info "等待 Docker 就绪（最多 60 秒）..."
    for i in $(seq 1 30); do
        if check_docker; then
            success "Docker 已就绪"
            return 0
        fi
        sleep 2
    done

    error "Docker 启动超时，请检查 Docker 安装是否正常。"
    exit 1
}

# ─── 2. 检查 docker-compose 服务 ────────────────────────────
compose_service_running() {
    docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running" 2>/dev/null \
        | grep -q "^${CORE_SERVICE}$"
}

start_compose() {
    info "启动 docker-compose 服务（后台模式）..."
    docker compose -f "$COMPOSE_FILE" up -d
    success "所有服务已启动"

    info "当前服务状态："
    docker compose -f "$COMPOSE_FILE" ps
}

# ─── 主流程 ─────────────────────────────────────────────────
main() {
    echo "======================================================"
    echo " Data Platform — 环境自检"
    echo "======================================================"

    # Step 1: Docker daemon
    if check_docker; then
        success "Docker 已在运行"
    else
        start_docker
    fi

    # Step 2: Compose 服务
    if compose_service_running; then
        success "docker-compose 服务已在运行，无需重启"
    else
        warn "docker-compose 服务未运行"
        start_compose
    fi

    echo "======================================================"
    success "环境就绪！"
    echo "======================================================"
}

main "$@"
