"""
设计文档管理器 - 管理需求设计文档的确认状态

功能：
- 列出所有设计文档
- 确认/驳回文档
- 执行已确认的变更
"""
import os
import json
import shutil
from datetime import datetime
from typing import List, Dict, Optional


class DesignDocumentManager:
    """设计文档管理器"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.project_root = os.path.dirname(current_dir)
        else:
            self.project_root = project_root
        
        self.design_dir = os.path.join(self.project_root, "design")
        os.makedirs(self.design_dir, exist_ok=True)
        
        # 状态文件
        self.status_file = os.path.join(self.design_dir, "_status.json")
    
    def _load_status(self) -> Dict:
        """加载状态"""
        if os.path.exists(self.status_file):
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"documents": {}}
    
    def _save_status(self, status: Dict):
        """保存状态"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    
    def list_documents(self) -> List[Dict]:
        """列出所有设计文档"""
        status = self._load_status()
        
        documents = []
        for filename in os.listdir(self.design_dir):
            if filename.startswith('_'):
                continue
            
            filepath = os.path.join(self.design_dir, filename)
            if not os.path.isfile(filepath):
                continue
            
            doc_status = status.get("documents", {}).get(filename, {})
            
            documents.append({
                "filename": filename,
                "path": filepath,
                "status": doc_status.get("status", "pending"),  # pending, confirmed, rejected
                "confirmed_at": doc_status.get("confirmed_at"),
                "confirmed_by": doc_status.get("confirmed_by"),
                "rejected_at": doc_status.get("rejected_at"),
                "rejected_reason": doc_status.get("rejected_reason"),
                "modified_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })
        
        return sorted(documents, key=lambda x: x.get("modified_at", ""), reverse=True)
    
    def confirm_document(self, filename: str, confirmed_by: str = "engineer") -> bool:
        """确认设计文档"""
        filepath = os.path.join(self.design_dir, filename)
        if not os.path.exists(filepath):
            return False
        
        status = self._load_status()
        
        if "documents" not in status:
            status["documents"] = {}
        
        status["documents"][filename] = {
            "status": "confirmed",
            "confirmed_at": datetime.now().isoformat(),
            "confirmed_by": confirmed_by,
            "executed": False
        }
        
        self._save_status(status)
        return True
    
    def reject_document(self, filename: str, reason: str) -> bool:
        """驳回设计文档"""
        filepath = os.path.join(self.design_dir, filename)
        if not os.path.exists(filepath):
            return False
        
        status = self._load_status()
        
        if "documents" not in status:
            status["documents"] = {}
        
        status["documents"][filename] = {
            "status": "rejected",
            "rejected_at": datetime.now().isoformat(),
            "rejected_reason": reason
        }
        
        self._save_status(status)
        return True
    
    def get_confirmed_documents(self) -> List[str]:
        """获取已确认但未执行的文档"""
        status = self._load_status()
        confirmed = []
        
        for filename, info in status.get("documents", {}).items():
            if info.get("status") == "confirmed" and not info.get("executed", False):
                confirmed.append(filename)
        
        return confirmed
    
    def mark_executed(self, filename: str):
        """标记为已执行"""
        status = self._load_status()
        
        if filename in status.get("documents", {}):
            status["documents"][filename]["executed"] = True
            status["documents"][filename]["executed_at"] = datetime.now().isoformat()
            self._save_status(status)


def main():
    """命令行入口"""
    import sys
    
    manager = DesignDocumentManager()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  list                    - 列出所有文档")
        print("  confirm <file>         - 确认文档")
        print("  reject <file> <reason> - 驳回文档")
        print("  execute                 - 执行已确认的变更")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        for doc in manager.list_documents():
            print(f"{doc['filename']}: {doc['status']}")
    
    elif cmd == "confirm":
        if len(sys.argv) < 3:
            print("用法: confirm <filename>")
            return
        filename = sys.argv[2]
        if manager.confirm_document(filename):
            print(f"✅ 已确认: {filename}")
        else:
            print(f"❌ 文件不存在: {filename}")
    
    elif cmd == "reject":
        if len(sys.argv) < 4:
            print("用法: reject <filename> <reason>")
            return
        filename = sys.argv[2]
        reason = sys.argv[3]
        if manager.reject_document(filename, reason):
            print(f"✅ 已驳回: {filename}")
        else:
            print(f"❌ 文件不存在: {filename}")
    
    elif cmd == "execute":
        # 简化版本：仅标记已确认文档为已执行
        confirmed = manager.get_confirmed_documents()
        for filename in confirmed:
            manager.mark_executed(filename)
            print(f"✅ 已执行: {filename}")
        if not confirmed:
            print("没有待执行的文档")


if __name__ == "__main__":
    main()
