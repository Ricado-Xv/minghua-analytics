"""
茗花智能汇报系统 - Web 服务器入口
"""
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 导入路由
from minghua_evo.api import router
from minghua_evo.api.reports import router as reports_router

# 前端 dist 目录
frontend_dist = os.path.join(PROJECT_ROOT, "frontend", "dist")

# 创建 FastAPI 应用
app = FastAPI(
    title="茗花智能汇报系统",
    description="可自我进化的智能汇报Web应用",
    version="0.1.0"
)

# 注册 API 路由
app.include_router(router)
app.include_router(reports_router)


# 处理静态文件请求
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_static(full_path: str):
    """静态文件服务 - 支持 SPA"""
    
    # 如果是 API 请求，返回 404
    if full_path.startswith('api/'):
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    # 尝试获取文件
    file_path = os.path.join(frontend_dist, full_path)
    
    # 如果文件存在，直接返回
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # 否则返回 index.html（用于 SPA）
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/", include_in_schema=False)
async def root():
    """根路径返回 index.html"""
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": "茗花智能汇报系统 API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


def main():
    """启动服务"""
    # 加载配置
    import yaml
    config_file = os.path.join(PROJECT_ROOT, "minghua_evo", "config", "settings.yaml")
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8888)

    print(f"🚀 启动茗花智能汇报系统...")
    print(f"   访问地址: http://localhost:{port}")
    print(f"   API 文档: http://localhost:{port}/docs")

    uvicorn.run(
        app,
        host=host,
        port=port
    )


if __name__ == "__main__":
    main()
