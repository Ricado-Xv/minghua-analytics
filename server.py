"""
茗花智能汇报系统 - Web 服务器入口
同时启动原版数据 API 和进化版 Web 服务
"""
import os
import sys
import subprocess
import threading
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 启动原版数据 API
def start_data_api():
    """启动原版数据 API 服务"""
    data_api_path = Path(PROJECT_ROOT) / 'src' / 'data_api.py'
    if data_api_path.exists():
        # 在子进程中运行
        subprocess.Popen(
            [sys.executable, str(data_api_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(Path(PROJECT_ROOT).parent)
        )
        print("📡 原版数据 API 已启动 (端口 8081)")
    else:
        print("⚠️  未找到原版 data_api.py")

# 启动 FastAPI
def start_evolution_server():
    """启动进化版 Web 服务"""
    import yaml
    from fastapi import FastAPI
    from fastapi.responses import FileResponse, JSONResponse
    import uvicorn

    from minghua_evo.api import router

    frontend_dist = os.path.join(PROJECT_ROOT, "frontend", "dist")

    app = FastAPI(title="茗花智能汇报系统", description="可自我进化的智能汇报Web应用", version="0.1.0")
    app.include_router(router)

    @app.get("/viewer.html")
    async def serve_viewer():
        """服务原版数据查看器页面"""
        viewer_path = os.path.join(PROJECT_ROOT, "src", "templates", "viewer.html")
        if os.path.exists(viewer_path):
            return FileResponse(viewer_path, media_type="text/html")
        return JSONResponse({"error": "Not found"}, status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_static(full_path: str):
        if full_path.startswith('api/'):
            return JSONResponse({"error": "Not found"}, status_code=404)
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return JSONResponse({"error": "Not found"}, status_code=404)

    @app.get("/", include_in_schema=False)
    async def root():
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "茗花智能汇报系统 API", "version": "0.1.0", "docs": "/docs"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # 加载配置
    config_file = os.path.join(PROJECT_ROOT, "minghua_evo", "config", "settings.yaml")
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 3001)

    print(f"🚀 启动茗花智能汇报系统...")
    print(f"   进化版访问: http://localhost:{port}")
    print(f"   API 文档: http://localhost:{port}/docs")

    uvicorn.run(app, host=host, port=port)


def main():
    # 先启动原版数据 API
    start_data_api()
    
    # 等待一下让 API 启动
    import time
    time.sleep(1)
    
    # 启动进化版服务器
    start_evolution_server()


if __name__ == "__main__":
    main()
