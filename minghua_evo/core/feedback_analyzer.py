"""
反馈进化器 - 将用户反馈转化为需求设计文档

功能：
- 读取意图识别反馈
- 使用 AI 分析错误模式
- 生成需求设计文档
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import subprocess


class FeedbackAnalyzer:
    """反馈分析器"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.project_root = os.path.dirname(current_dir)  # minghua_evo/
        else:
            self.project_root = project_root
        
        self.feedback_file = os.path.join(
            self.project_root, "data", "feedback", "intent_feedback.json"
        )
        self.design_dir = os.path.join(self.project_root, "design")
        
        # 确保目录存在
        os.makedirs(self.design_dir, exist_ok=True)
    
    def load_feedbacks(self) -> List[Dict]:
        """加载所有反馈"""
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def get_unprocessed_feedbacks(self) -> List[Dict]:
        """获取未处理的反馈"""
        feedbacks = self.load_feedbacks()
        return [f for f in feedbacks if not f.get("processed", False)]
    
    def analyze_with_ai(self, feedbacks: List[Dict]) -> str:
        """使用 AI 分析反馈，生成改进建议"""
        if not feedbacks:
            return "暂无反馈数据"
        
        # 构建反馈摘要
        feedback_summary = "\n".join([
            f"- 用户输入: {f.get('message', '')}"
            f"  AI识别: {f.get('ai_intent', 'CUSTOM')}"
            f"  用户期望: {f.get('user_input', f.get('message', ''))}"
            f"  备注: {f.get('comment', '无')}"
            for f in feedbacks
        ])
        
        prompt = f"""你是一个产品经理，分析以下意图识别的用户反馈，生成改进建议。

用户反馈：
{feedback_summary}

请分析：
1. 这些反馈有什么共同点？
2. 应该如何改进 intent_rules.yaml 规则？
3. 生成具体的需求设计文档

请返回 Markdown 格式的需求设计文档，包含：
- 问题分析
- 改进方案（具体的规则修改）
- 预期效果"""
        
        # 调用 AI
        result = subprocess.run(
            [
                "openclaw", "agent",
                "--agent", "test-agent",
                "-m", prompt
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return f"AI 分析失败: {result.stderr}"
        
        return result.stdout
    
    def generate_design_document(self, analysis: str) -> str:
        """生成需求设计文档"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intent_improvement_{timestamp}.md"
        filepath = os.path.join(self.design_dir, filename)
        
        content = f"""# 意图识别改进需求设计

生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 用户反馈分析

{analysis}

---
*本文档由进化引擎自动生成*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def mark_processed(self, feedbacks: List[Dict]):
        """标记反馈为已处理"""
        all_feedbacks = self.load_feedbacks()
        
        # 标记已处理的反馈
        processed_messages = [f.get('message', '') for f in feedbacks]
        for f in all_feedbacks:
            if f.get('message', '') in processed_messages:
                f['processed'] = True
                f['processed_at'] = datetime.now().isoformat()
        
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(all_feedbacks, f, ensure_ascii=False, indent=2)
    
    def evolve(self) -> Dict:
        """执行进化流程"""
        # 1. 获取未处理的反馈
        feedbacks = self.get_unprocessed_feedbacks()
        
        if not feedbacks:
            return {
                "success": False,
                "message": "暂无未处理的反馈"
            }
        
        # 2. AI 分析
        analysis = self.analyze_with_ai(feedbacks)
        
        # 3. 生成设计文档
        filepath = self.generate_design_document(analysis)
        
        # 4. 标记已处理
        self.mark_processed(feedbacks)
        
        return {
            "success": True,
            "feedback_count": len(feedbacks),
            "design_file": filepath,
            "analysis": analysis
        }


def main():
    """命令行入口"""
    analyzer = FeedbackAnalyzer()
    result = analyzer.evolve()
    
    if result["success"]:
        print(f"✅ 进化完成！")
        print(f"   处理反馈: {result['feedback_count']} 条")
        print(f"   生成文档: {result['design_file']}")
    else:
        print(f"❌ {result['message']}")


if __name__ == "__main__":
    main()
