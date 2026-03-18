"""
FastAPI 路由
"""
import os
import sys
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from minghua_evo.core.intent_classifier import IntentClassifier
from minghua_evo.core.code_executor import CodeExecutor
from minghua_evo.core.conversation_logger import ConversationLogger
from minghua_evo.services.evolution_engine import EvolutionEngine

router = APIRouter()

_classifier = None
_executor = None
_logger = None
_engine = None


def get_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def get_executor() -> CodeExecutor:
    global _executor
    if _executor is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _executor = CodeExecutor(project_root)
    return _executor


def get_logger() -> ConversationLogger:
    global _logger
    if _logger is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        _logger = ConversationLogger(project_root)
    return _logger


def get_engine() -> EvolutionEngine:
    global _engine
    if _engine is None:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        permissions_config = os.path.join(project_root, "minghua_evo", "config", "permissions.yaml")
        _engine = EvolutionEngine(project_root, permissions_config=permissions_config)
    return _engine


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    reply: str
    data: Optional[Dict] = None
    render_type: str = "text"


class ScheduleRequest(BaseModel):
    enabled: bool
    cron: Optional[str] = None


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    classifier = get_classifier()
    executor = get_executor()
    logger = get_logger()

    intent = classifier.classify(request.message)
    result = executor.execute(intent.type.value, intent.params, intent.raw_message)

    logger.log(user_message=request.message, intent=intent.type.value, params=intent.params, reply=result.reply, success=result.success)

    return ChatResponse(intent=intent.type.value, reply=result.reply, data=result.data, render_type=result.render_type)


@router.get("/api/conversations")
async def get_conversations(limit: int = 100):
    logger = get_logger()
    conversations = logger.get_history(limit)
    return {"conversations": conversations}


@router.get("/api/conversations/export")
async def export_conversations(limit: int = 50):
    logger = get_logger()
    text = logger.export_for_ai(limit)
    return {"content": text}


@router.post("/api/evolve/trigger")
async def trigger_evolution():
    engine = get_engine()
    logger = get_logger()
    result = engine.trigger_manual(logger)
    return result


@router.post("/api/evolve/from-requirements")
async def trigger_evolution_from_requirements():
    """从需求池触发进化，生成需求和设计文档"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    requirements = collector.get_requirements()
    
    engine = get_engine()
    result = engine.trigger_from_requirements(requirements)
    
    return result


@router.post("/api/evolve/generate-requirements")
async def generate_requirements_doc():
    """只生成需求文档"""
    from minghua_evo.core.feedback_collector import get_collector
    from minghua_evo.core.requirements_doc_generator import RequirementsDocGenerator
    
    collector = get_collector()
    requirements = collector.get_requirements()
    
    if not requirements:
        return {"status": "completed", "message": "暂无新需求", "file": None}
    
    gen = RequirementsDocGenerator()
    result = gen.generate_from_requirements(requirements)
    
    return {
        "status": "completed",
        "message": "需求文档已生成",
        "file": result.get("requirements_file", "").split("/").pop() if result.get("success") else None
    }


@router.post("/api/evolve/generate-design")
async def generate_design_doc():
    """只生成设计文档"""
    from minghua_evo.core.feedback_collector import get_collector
    from minghua_evo.core.requirements_doc_generator import RequirementsDocGenerator
    
    collector = get_collector()
    requirements = collector.get_requirements()
    
    if not requirements:
        return {"status": "completed", "message": "暂无新需求", "file": None}
    
    gen = RequirementsDocGenerator()
    result = gen.generate_design_from_requirements(requirements)
    
    return {
        "status": "completed", 
        "message": "设计文档已生成",
        "file": result.get("design_file", "").split("/").pop() if result.get("success") else None
    }


@router.get("/api/evolve/progress")
async def get_evolution_progress():
    """获取进化进度"""
    engine = get_engine()
    return engine.get_progress()


@router.get("/api/evolve/status")
async def get_evolution_status():
    engine = get_engine()
    return {
        "running": engine.is_running,
        "last_run": engine.last_run,
        "current_version": engine.current_version,
        "schedule": engine.get_schedule_status()
    }


@router.post("/api/evolve/schedule")
async def set_evolution_schedule(request: ScheduleRequest):
    engine = get_engine()
    engine.set_schedule(cron_expr=request.cron, enabled=request.enabled)
    status = engine.get_schedule_status()
    return {"status": "scheduled" if request.enabled else "disabled", "cron": status["cron"]}


@router.get("/api/evolve/versions")
async def get_version_history():
    engine = get_engine()
    versions = engine.get_version_history()
    return {"versions": [{"version": v.version, "created_at": v.created_at, "title": v.title, "status": v.status} for v in versions]}


@router.get("/api/evolve/versions/{version}")
async def get_version_detail(version: str):
    engine = get_engine()
    detail = engine.get_version_detail(version)
    if not detail:
        raise HTTPException(status_code=404, detail="Version not found")
    return detail


@router.get("/api/permissions")
async def get_permissions():
    engine = get_engine()
    permissions = engine.permissions.get_all_permissions()
    return {"permissions": permissions}


# ========================================
# 意图反馈 API
# ========================================

class IntentFeedbackRequest(BaseModel):
    message: str  # 原始用户输入
    ai_intent: str  # AI 识别结果
    correct_intent: Optional[str] = None  # 正确意图（可选）
    user_input: Optional[str] = None  # 用户自定义输入（可选）
    comment: Optional[str] = None  # 备注


class NewRequirementRequest(BaseModel):
    original_message: str  # 用户原始输入
    requirement: str  # 用户描述的需求
    description: Optional[str] = None  # 详细说明（可选）


class BatchRequirementRequest(BaseModel):
    requirements: List[Dict]  # 批量需求 [{"requirement": "...", "description": "...", ...}]


@router.post("/api/feedback/requirement")
async def submit_new_requirement(request: NewRequirementRequest):
    """提交新功能需求"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    
    success = collector.add_requirement(
        original_message=request.original_message,
        requirement=request.requirement,
        description=request.description
    )
    
    if success:
        return {"status": "ok", "message": "需求已记录"}
    else:
        raise HTTPException(status_code=500, detail="需求保存失败")


@router.post("/api/feedback/requirements/batch")
async def submit_batch_requirements(request: BatchRequirementRequest):
    """批量提交需求（支持 txt 文件解析）"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    added = 0
    
    for req in request.requirements:
        success = collector.add_requirement(
            original_message=req.get('original_message', ''),
            requirement=req.get('requirement', ''),
            description=req.get('description')
        )
        if success:
            added += 1
    
    return {"status": "ok", "message": f"成功添加 {added} 条需求", "added": added}


@router.get("/api/feedback/requirement")
async def get_new_requirements():
    """获取所有新功能需求"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    requirements = collector.get_requirements()
    return {"requirements": requirements}


@router.post("/api/feedback/intent")
async def submit_intent_feedback(request: IntentFeedbackRequest):
    """提交意图识别反馈"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    
    # 使用用户自定义输入覆盖原始输入
    effective_message = request.user_input if request.user_input else request.message
    
    success = collector.add_feedback(
        message=effective_message,
        ai_intent=request.ai_intent,
        correct_intent=request.correct_intent,
        user_input=request.user_input,
        comment=request.comment
    )
    
    if success:
        return {"status": "ok", "message": "反馈已记录"}
    else:
        raise HTTPException(status_code=500, detail="反馈保存失败")


@router.get("/api/feedback/intent")
async def get_intent_feedbacks():
    """获取所有意图反馈"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    feedbacks = collector.get_feedbacks()
    return {"feedbacks": feedbacks}


@router.delete("/api/feedback/intent")
async def clear_intent_feedbacks():
    """清空所有反馈"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    collector.clear()
    return {"status": "ok", "message": "反馈已清空"}


# ========================================
# 反馈进化 API
# ========================================

@router.post("/api/evolve/feedback")
async def evolve_from_feedback():
    """从用户反馈生成需求设计文档"""
    from minghua_evo.core.feedback_analyzer import FeedbackAnalyzer
    
    analyzer = FeedbackAnalyzer()
    result = analyzer.evolve()
    
    return result


# ========================================
# 设计文档管理 API
# ========================================

class DesignDocRequest(BaseModel):
    filename: str
    reason: Optional[str] = None


@router.get("/api/design/docs")
async def list_design_docs():
    """列出所有设计文档"""
    from minghua_evo.core.design_doc_manager import DesignDocumentManager
    
    manager = DesignDocumentManager()
    docs = manager.list_documents()
    return {"documents": docs}


@router.post("/api/design/docs/confirm")
async def confirm_design_doc(request: DesignDocRequest):
    """确认设计文档"""
    from minghua_evo.core.design_doc_manager import DesignDocumentManager
    
    manager = DesignDocumentManager()
    success = manager.confirm_document(request.filename)
    
    if success:
        return {"status": "ok", "message": f"已确认: {request.filename}"}
    else:
        raise HTTPException(status_code=404, detail="文档不存在")


@router.post("/api/design/docs/reject")
async def reject_design_doc(request: DesignDocRequest):
    """驳回设计文档"""
    from minghua_evo.core.design_doc_manager import DesignDocumentManager
    
    manager = DesignDocumentManager()
    success = manager.reject_document(request.filename, request.reason or "")
    
    if success:
        return {"status": "ok", "message": f"已驳回: {request.filename}"}
    else:
        raise HTTPException(status_code=404, detail="文档不存在")


@router.post("/api/design/docs/execute")
async def execute_design_doc(request: DesignDocRequest):
    """执行已确认的设计文档"""
    from minghua_evo.core.auto_updater import AutoUpdater
    
    updater = AutoUpdater()
    result = updater.execute_design(request.filename)
    
    return result


# ========================================
# 文档查看 API
# ========================================

@router.get("/api/docs/list")
async def list_all_docs():
    """列出所有文档（需求+设计），从插件 design 目录读取"""
    import glob
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    design_dir = os.path.join(project_root, "minghua_evo", "design")
    
    all_docs = []
    
    # 从 design 目录获取版本化文档
    for f in glob.glob(os.path.join(design_dir, "requirements_*.md")):
        basename = os.path.basename(f)
        version = basename.replace("requirements_", "").replace(".md", "")
        is_latest = False  # 所有版本都是平等的，最新的在列表顶部
        
        all_docs.append({
            "filename": basename,
            "type": "requirements",
            "is_latest": is_latest,
            "version": version,
            "size": os.path.getsize(f),
            "modified": os.path.getmtime(f),
            "location": "design"
        })
    
    for f in glob.glob(os.path.join(design_dir, "design_*.md")):
        basename = os.path.basename(f)
        version = basename.replace("design_", "").replace(".md", "")
        is_latest = False
        
        all_docs.append({
            "filename": basename,
            "type": "design",
            "is_latest": is_latest,
            "version": version,
            "size": os.path.getsize(f),
            "modified": os.path.getmtime(f),
            "location": "design"
        })
    
    return {"documents": sorted(all_docs, key=lambda x: x["modified"], reverse=True)}


@router.get("/api/docs/versions/{doc_type}")
async def list_doc_versions(doc_type: str):
    """列出指定类型文档的所有版本"""
    import glob
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    design_dir = os.path.join(project_root, "minghua_evo", "design")
    
    versions = []
    pattern = f"{doc_type}_*.md"
    
    for f in glob.glob(os.path.join(design_dir, pattern)):
        basename = os.path.basename(f)
        version = basename.replace(f"{doc_type}_", "").replace(".md", "")
        versions.append({
            "filename": basename,
            "version": version,
            "modified": os.path.getmtime(f),
            "location": "design"
        })
    
    return {"versions": sorted(versions, key=lambda x: x["modified"], reverse=True)}


@router.get("/api/docs/summary")
async def get_docs_summary():
    """获取文档摘要"""
    from minghua_evo.core.doc_manager import get_doc_manager
    
    manager = get_doc_manager()
    return manager.get_summary()


@router.get("/api/docs/{filename}")
async def get_doc_content(filename: str):
    """获取文档内容，从插件 design 目录读取"""
    import glob
    
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    design_dir = os.path.join(project_root, "minghua_evo", "design")
    
    # 只从 design 目录查找
    filepath = os.path.join(design_dir, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文档不存在")
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"filename": filename, "content": content, "location": "design"}


# ========================================
# 配置管理 API
# ========================================

def load_full_settings() -> Dict:
    """加载完整配置"""
    import yaml
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(current_dir), "config", "settings.yaml")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}


@router.get("/api/config")
async def get_config():
    """获取系统配置"""
    settings = load_full_settings()
    
    # 返回数据源配置（隐藏敏感信息）
    dp_config = settings.get('data_provider', {})
    if 'http' in dp_config and 'token' in dp_config.get('http', {}):
        dp_config = dp_config.copy()
        dp_config['http'] = dp_config.get('http', {}).copy()
        dp_config['http']['token'] = "***"
    
    # 返回宿主系统配置
    host_config = settings.get('host_system', {})
    
    # 返回意图识别配置
    intent_config = settings.get('intent_classifier', {})
    if 'token' in intent_config:
        intent_config = intent_config.copy()
        intent_config['token'] = "***"
    
    return {
        "data_provider": dp_config,
        "host_system": host_config,
        "intent_classifier": intent_config
    }


@router.get("/api/project")
async def get_project_info():
    """获取项目信息"""
    settings = load_full_settings()
    host_config = settings.get('host_system', {})
    
    project_name = host_config.get('name', '未知项目')
    
    return {
        "name": project_name,
        "full_name": f"{project_name}-智能版"
    }


@router.get("/api/host-docs")
async def get_host_docs():
    """获取宿主项目的 README 和设计文档"""
    from minghua_evo.services.data_provider import DataProvider
    
    # 使用数据源配置获取宿主 API 地址
    config = DataProvider.get_config()
    http_config = config.get('http', {})
    base_url = f"http://{http_config.get('host', 'localhost')}:{http_config.get('port', 8081)}"
    
    result = {"readme": None, "design_doc": None}
    
    # 获取 README
    try:
        import urllib.request
        req = urllib.request.Request(f"{base_url}/api/readme")
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result["readme"] = data.get("content", "")
    except Exception as e:
        print(f"[API] 获取 README 失败: {e}")
    
    # 获取设计文档
    try:
        req = urllib.request.Request(f"{base_url}/api/design-doc")
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result["design_doc"] = data.get("content", "")
    except Exception as e:
        print(f"[API] 获取设计文档失败: {e}")
    
    return result


@router.get("/api/config/data-provider")
async def get_data_provider_config():
    """获取数据源配置"""
    from minghua_evo.services.data_provider import DataProvider
    
    config = DataProvider.get_config()
    return config


# ========================================
# 文档管理 API
# ========================================

class DocStatusRequest(BaseModel):
    filename: str
    status: str


@router.get("/api/docs/summary")
async def get_docs_summary():
    """获取文档摘要"""
    from minghua_evo.core.doc_manager import get_doc_manager
    
    manager = get_doc_manager()
    return manager.get_summary()


@router.post("/api/docs/status")
async def update_doc_status(request: DocStatusRequest):
    """更新文档状态"""
    from minghua_evo.core.doc_manager import get_doc_manager
    
    manager = get_doc_manager()
    success = manager.update_status(request.filename, request.status)
    
    if success:
        return {"status": "ok", "message": f"状态已更新为 {request.status}"}
    else:
        raise HTTPException(status_code=500, detail="更新失败")


@router.delete("/api/docs/{filename}")
async def delete_doc(filename: str):
    """删除文档"""
    from minghua_evo.core.doc_manager import get_doc_manager
    
    manager = get_doc_manager()
    
    # 找到文件路径
    import glob
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    design_dir = os.path.join(project_root, "design")
    
    filepath = os.path.join(design_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 删除文件
    try:
        os.remove(filepath)
        return {"status": "ok", "message": f"已删除 {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e}")


# ========================================
# 新需求管理 API
# ========================================

@router.get("/api/requirements")
async def get_requirements():
    """获取所有新功能需求"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    requirements = collector.get_requirements()
    
    # 获取摘要
    from minghua_evo.core.doc_manager import get_doc_manager
    doc_manager = get_doc_manager()
    summary = doc_manager.get_summary()
    
    return {
        "requirements": requirements,
        "total": len(requirements),
        "summary": summary
    }


@router.post("/api/requirements/{req_id}")
async def update_requirement(req_id: int, action: str = None):
    """处理需求（标记处理/删除）"""
    from minghua_evo.core.feedback_collector import get_collector
    
    collector = get_collector()
    requirements = collector.get_requirements()
    
    if req_id < 0 or req_id >= len(requirements):
        raise HTTPException(status_code=404, detail="需求不存在")
    
    if action == "delete":
        requirements.pop(req_id)
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "feedback", "requirements.json"), 'w') as f:
            json.dump(requirements, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "message": "已删除"}
    
    return {"status": "ok"}
