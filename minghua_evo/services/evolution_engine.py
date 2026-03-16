"""
进化引擎
"""
import os
import yaml
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class PermissionLevel:
    FORBIDDEN = "forbidden"
    CONFIRM_REQUIRED = "confirm"
    AUTO = "auto"


@dataclass
class DesignDoc:
    title: str
    description: str
    requirements: List[str]
    implementation: str
    affected_files: List[str]


@dataclass
class ApplyResult:
    success: bool
    message: str
    modified_files: List[str]
    pending_files: List[str]


@dataclass
class VersionInfo:
    version: str
    created_at: str
    title: str
    status: str


class PermissionManager:
    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.permissions: Dict[str, str] = {}
        if config_file and os.path.exists(config_file):
            self._load()

    def _load(self):
        with open(self.config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            self.permissions = data.get('permissions', {})

    def get_permission(self, file_path: str) -> str:
        for pattern, level in self.permissions.items():
            if file_path.startswith(pattern):
                return level
        return PermissionLevel.FORBIDDEN

    def get_all_permissions(self) -> Dict[str, str]:
        return self.permissions


class EvolutionEngine:
    def __init__(self, project_root: str = None, openclaw_endpoint: str = "http://localhost:8080", permissions_config: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.openclaw_endpoint = openclaw_endpoint

        if permissions_config:
            self.permissions = PermissionManager(permissions_config)
        else:
            default_config = os.path.join(self.project_root, "minghua_evo", "config", "permissions.yaml")
            if os.path.exists(default_config):
                self.permissions = PermissionManager(default_config)
            else:
                self.permissions = PermissionManager()

        self.history_dir = os.path.join(self.project_root, "minghua_evo", "evolution_history")
        Path(self.history_dir).mkdir(parents=True, exist_ok=True)

        self.schedule_config = {"enabled": False, "cron": "0 9 * * *"}
        self.is_running = False
        self.last_run = None
        self.current_version = "v0.1"

    def trigger_manual(self, conversation_logger=None) -> dict:
        if self.is_running:
            return {"status": "running", "message": "进化任务正在执行中"}

        self.is_running = True
        try:
            if conversation_logger:
                conversations = conversation_logger.get_recent_conversations(hours=24)
            else:
                conversations = []

            requirements = self._analyze_conversations(conversations)
            if not requirements:
                return {"status": "completed", "message": "近期没有新的需求，跳过进化", "new_version": self.current_version}

            design = self._generate_design(requirements)
            result = self._apply_design(design)
            new_version = self._save_version(design, result)
            self.last_run = datetime.now().isoformat()

            return {
                "status": "completed",
                "message": "进化完成",
                "new_version": new_version,
                "modified": result.modified_files,
                "pending": result.pending_files
            }
        finally:
            self.is_running = False

    def set_schedule(self, cron_expr: str = None, enabled: bool = True) -> bool:
        if cron_expr:
            self.schedule_config["cron"] = cron_expr
        self.schedule_config["enabled"] = enabled
        return True

    def get_schedule_status(self) -> dict:
        return {
            "enabled": self.schedule_config["enabled"],
            "cron": self.schedule_config["cron"],
            "last_run": self.last_run,
            "next_run": None
        }

    def _analyze_conversations(self, conversations: List[Dict]) -> List[str]:
        if not conversations:
            return []
        requirements = []
        seen = set()
        for conv in conversations:
            msg = conv.get('user_message', '')
            intent = conv.get('intent', '')
            if intent == 'CUSTOM' and msg and msg not in seen:
                requirements.append(msg)
                seen.add(msg)
        return requirements

    def _generate_design(self, requirements: List[str]) -> DesignDoc:
        return DesignDoc(
            title="新功能设计",
            description="\n".join([f"- {r}" for r in requirements]),
            requirements=requirements,
            implementation="# TODO: 实现方案",
            affected_files=["src/features/"]
        )

    def _apply_design(self, design: DesignDoc) -> ApplyResult:
        modified_files = []
        pending_files = []
        for file_path in design.affected_files:
            permission = self.permissions.get_permission(file_path)
            if permission == PermissionLevel.FORBIDDEN:
                continue
            elif permission == PermissionLevel.CONFIRM_REQUIRED:
                pending_files.append(file_path)
            elif permission == PermissionLevel.AUTO:
                modified_files.append(file_path)

        return ApplyResult(success=True, message=f"已处理 {len(modified_files)} 个文件", modified_files=modified_files, pending_files=pending_files)

    def _save_version(self, design: DesignDoc, result: ApplyResult) -> str:
        version_num = len([d for d in os.listdir(self.history_dir) if d.startswith('v')])
        version = f"v{version_num + 1}.0"
        self.current_version = version

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        version_dir = os.path.join(self.history_dir, f"{version}_{timestamp}")
        Path(version_dir).mkdir(parents=True, exist_ok=True)

        design_file = os.path.join(version_dir, "design.md")
        with open(design_file, 'w', encoding='utf-8') as f:
            f.write(f"# {design.title}\n\n## 需求描述\n{design.description}\n\n## 实现方案\n{design.implementation}\n")

        changelog_file = os.path.join(version_dir, "changelog.md")
        with open(changelog_file, 'w', encoding='utf-8') as f:
            f.write(f"# 变更日志 - {version}\n")
            f.write(f"## 修改: {', '.join(result.modified_files)}\n")
            f.write(f"## 待确认: {', '.join(result.pending_files)}\n")

        readme_file = os.path.join(version_dir, "README.md")
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(f"# {version} - {design.title}\n\n**创建时间**: {timestamp}\n\n## 概述\n{design.description}\n")

        return version

    def get_version_history(self) -> List[VersionInfo]:
        versions = []
        for dirname in os.listdir(self.history_dir):
            dir_path = os.path.join(self.history_dir, dirname)
            if not os.path.isdir(dir_path):
                continue
            parts = dirname.split('_')
            version = parts[0] if parts else "v1.0"
            created_at = '_'.join(parts[1:]) if len(parts) > 1 else dirname
            versions.append(VersionInfo(version=version, created_at=created_at, title="新功能", status="applied"))
        versions.sort(key=lambda x: x.version, reverse=True)
        return versions

    def get_version_detail(self, version: str) -> Optional[dict]:
        for dirname in os.listdir(self.history_dir):
            if not dirname.startswith(version):
                continue
            dir_path = os.path.join(self.history_dir, dirname)
            result = {"version": version, "created_at": dirname, "design": "", "changelog": "", "readme": ""}
            for fname in ["design.md", "changelog.md", "README.md"]:
                fpath = os.path.join(dir_path, fname)
                if os.path.exists(fpath):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        result[fname.replace(".md", "")] = f.read()
            return result
        return None
