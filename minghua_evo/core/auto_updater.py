"""
自动更新器 - 根据确认的设计文档自动更新配置

功能：
- 读取已确认的设计文档
- 提取规则修改
- 自动更新 intent_rules.yaml
- 记录变更日志
"""
import os
import re
import yaml
import shutil
from datetime import datetime
from typing import Dict, List, Optional


class AutoUpdater:
    """自动更新器"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.project_root = os.path.dirname(current_dir)
        else:
            self.project_root = project_root
        
        self.config_file = os.path.join(self.project_root, "config", "intent_rules.yaml")
        self.backup_dir = os.path.join(self.project_root, "config", "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 变更日志
        self.changelog_file = os.path.join(self.project_root, "design", "changelog.md")
    
    def backup_config(self) -> str:
        """备份当前配置"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"intent_rules_{timestamp}.yaml")
        shutil.copy2(self.config_file, backup_file)
        return backup_file
    
    def load_config(self) -> Dict:
        """加载配置"""
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def save_config(self, config: Dict):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    def extract_rules_from_document(self, content: str) -> Dict[str, Dict]:
        """从设计文档提取规则修改"""
        # 解析 YAML 代码块
        yaml_blocks = re.findall(r'```yaml\n(.*?)```', content, re.DOTALL)
        
        rules = {}
        
        for block in yaml_blocks:
            # 尝试解析 YAML
            try:
                data = yaml.safe_load(block)
                if data and 'rules' in data:
                    rules.update(data['rules'])
            except:
                continue
        
        return rules
    
    def update_rules(self, new_rules: Dict) -> List[str]:
        """更新规则，返回变更列表"""
        config = self.load_config()
        
        if 'rules' not in config:
            config['rules'] = {}
        
        changes = []
        
        for intent_type, rule_config in new_rules.items():
            if intent_type not in config['rules']:
                config['rules'][intent_type] = {}
            
            old_config = config['rules'].get(intent_type, {})
            
            # 更新 keywords
            if 'keywords' in rule_config:
                old_keywords = set(config['rules'][intent_type].get('keywords', []))
                new_keywords = set(rule_config['keywords'])
                added = new_keywords - old_keywords
                if added:
                    config['rules'][intent_type]['keywords'] = list(old_keywords | new_keywords)
                    changes.append(f"{intent_type}: 新增关键词 {added}")
            
            # 更新 patterns
            if 'patterns' in rule_config:
                old_patterns = set(config['rules'][intent_type].get('patterns', []))
                new_patterns = set(rule_config['patterns'])
                added = new_patterns - old_patterns
                if added:
                    config['rules'][intent_type]['patterns'] = list(old_patterns | new_patterns)
                    changes.append(f"{intent_type}: 新增模式 {added}")
            
            # 更新 priority
            if 'priority' in rule_config:
                old_priority = config['rules'][intent_type].get('priority', 0)
                new_priority = rule_config['priority']
                if new_priority != old_priority:
                    config['rules'][intent_type]['priority'] = new_priority
                    changes.append(f"{intent_type}: 优先级 {old_priority} -> {new_priority}")
        
        if changes:
            self.save_config(config)
        
        return changes
    
    def execute_design(self, filename: str) -> Dict:
        """执行设计文档"""
        filepath = os.path.join(self.project_root, "design", filename)
        
        if not os.path.exists(filepath):
            return {"success": False, "error": "文件不存在"}
        
        # 1. 备份
        backup_file = self.backup_config()
        
        # 2. 读取文档
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 3. 提取规则
        new_rules = self.extract_rules_from_document(content)
        
        if not new_rules:
            return {"success": False, "error": "未找到规则修改"}
        
        # 4. 更新规则
        changes = self.update_rules(new_rules)
        
        # 5. 记录日志
        self.log_change(filename, changes)
        
        # 6. 重新加载意图识别器
        self.reload_intent_classifier()
        
        return {
            "success": True,
            "backup": backup_file,
            "changes": changes,
            "rules_updated": list(new_rules.keys())
        }
    
    def log_change(self, filename: str, changes: List[str]):
        """记录变更日志"""
        log_entry = f"""
## {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

### 执行文档: {filename}

**变更:**
"""
        for change in changes:
            log_entry += f"- {change}\n"
        
        # 追加到日志
        if os.path.exists(self.changelog_file):
            with open(self.changelog_file, 'r', encoding='utf-8') as f:
                old_content = f.read()
        else:
            old_content = "# 变更日志\n"
        
        with open(self.changelog_file, 'w', encoding='utf-8') as f:
            f.write(log_entry + "\n" + old_content)
    
    def reload_intent_classifier(self):
        """重新加载意图识别器"""
        try:
            from minghua_evo.core.intent_classifier import IntentClassifier
            IntentClassifier.reload_rules()
            print("[AutoUpdater] 意图识别器已重新加载")
        except Exception as e:
            print(f"[AutoUpdater] 重新加载失败: {e}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python -m auto_updater <design_file>")
        return
    
    filename = sys.argv[1]
    updater = AutoUpdater()
    result = updater.execute_design(filename)
    
    if result["success"]:
        print(f"✅ 执行成功！")
        print(f"   备份: {result['backup']}")
        print(f"   变更:")
        for change in result["changes"]:
            print(f"     - {change}")
    else:
        print(f"❌ 执行失败: {result['error']}")


if __name__ == "__main__":
    main()
