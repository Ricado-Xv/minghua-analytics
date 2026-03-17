"""
FastAPI 路由
"""
import os
import sys
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
