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
    result = executor.execute(intent.type.value, intent.params)

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
