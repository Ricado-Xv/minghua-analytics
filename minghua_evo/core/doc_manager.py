"""
文档管理器 - 负责文档的版本管理、状态跟踪
"""
import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Optional


class DocStatus:
    """文档状态"""
    DRAFT = "draft"           # 草稿
    PENDING = "pending"       # 待审核
    CONFIRMED = "confirmed"   # 已确认
    EXECUTED = "executed"     # 已执行


class DocManager:
    """文档管理器"""
    
    def __init__(self, design_dir: str = None):
        if design_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            design_dir = os.path.join(os.path.dirname(current_dir), "design")
        
        self.design_dir = design_dir
        self.status_file = os.path.join(design_dir, "_status.json")
        os.makedirs(design_dir, exist_ok=True)
        
        # 初始化状态文件
        if not os.path.exists(self.status_file):
            self._save_status({})
    
    def _load_status(self) -> Dict:
        """加载状态"""
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_status(self, status: Dict):
        """保存状态"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    
    def get_docs(self, doc_type: str = None) -> List[Dict]:
        """获取文档列表"""
        status = self._load_status()
        
        all_docs = []
        
        # 需求文档
        for f in glob.glob(os.path.join(self.design_dir, "requirements_*.md")):
            basename = os.path.basename(f)
            if basename == "requirements_latest.md":
                continue
            version = basename.replace("requirements_", "").replace(".md", "")
            all_docs.append({
                "filename": basename,
                "type": "requirements",
                "version": version,
                "status": status.get(basename, {}).get("status", DocStatus.PENDING),
                "modified": os.path.getmtime(f)
            })
        
        # 设计文档
        for f in glob.glob(os.path.join(self.design_dir, "design_*.md")):
            basename = os.path.basename(f)
            if basename == "design_latest.md":
                continue
            version = basename.replace("design_", "").replace(".md", "")
            all_docs.append({
                "filename": basename,
                "type": "design",
                "version": version,
                "status": status.get(basename, {}).get("status", DocStatus.PENDING),
                "modified": os.path.getmtime(f)
            })
        
        # 筛选类型
        if doc_type:
            all_docs = [d for d in all_docs if d["type"] == doc_type]
        
        # 按修改时间排序
        return sorted(all_docs, key=lambda x: x["modified"], reverse=True)
    
    def update_status(self, filename: str, status: str) -> bool:
        """更新文档状态"""
        try:
            data = self._load_status()
            data[filename] = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            self._save_status(data)
            return True
        except Exception as e:
            print(f"[DocManager] 更新状态失败: {e}")
            return False
    
    def get_status(self, filename: str) -> str:
        """获取文档状态"""
        data = self._load_status()
        return data.get(filename, {}).get("status", DocStatus.PENDING)
    
    def get_summary(self) -> Dict:
        """获取文档摘要"""
        status = self._load_status()
        
        requirements = self.get_docs("requirements")
        design = self.get_docs("design")
        
        # 统计各状态数量
        req_status = {}
        des_status = {}
        
        for d in requirements:
            s = d["status"]
            req_status[s] = req_status.get(s, 0) + 1
        
        for d in design:
            s = d["status"]
            des_status[s] = des_status.get(s, 0) + 1
        
        return {
            "requirements": {
                "total": len(requirements),
                "by_status": req_status
            },
            "design": {
                "total": len(design),
                "by_status": des_status
            },
            "latest_version": {
                "requirements": requirements[0]["version"] if requirements else None,
                "design": design[0]["version"] if design else None
            }
        }


# 单例
_doc_manager = None


def get_doc_manager() -> DocManager:
    global _doc_manager
    if _doc_manager is None:
        _doc_manager = DocManager()
    return _doc_manager
