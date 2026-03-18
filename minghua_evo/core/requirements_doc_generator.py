"""
需求设计文档生成器 - 从用户反馈自动生成完整的需求分析和软件设计文档

功能：
- 分析用户反馈
- 生成需求分析文档 (requirements_*.md)
- 生成软件设计文档 (design_*.md)
- 支持文档版本管理
"""
import os
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
import shutil


class RequirementsDocGenerator:
    """需求设计文档生成器"""
    
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
    
    def call_ai(self, prompt: str, timeout: int = 300) -> str:
        """调用 AI 生成内容"""
        # 使用默认 session-id
        result = subprocess.run(
            ["openclaw", "agent", "--session-id", "dfc59459-f9d5-4dd8-954f-fb9abd1093ea", "--message", prompt, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=self.project_root
        )

        if result.returncode != 0:
            raise Exception(f"AI 调用失败: {result.stderr}")

        # 解析 JSON 输出
        import json
        try:
            data = json.loads(result.stdout)
            return data.get("result", {}).get("payloads", [{}])[0].get("text", "")
        except:
            return result.stdout
    
    def generate_requirements_doc(self, feedbacks: List[Dict]) -> str:
        """生成需求分析文档"""
        # 构建反馈摘要
        error_feedbacks = [f for f in feedbacks if f.get('user_input')]
        
        if not error_feedbacks:
            return "暂无错误反馈需要处理"
        
        feedback_summary = "\n".join([
            f"- 用户原输入: `{f.get('message', '')}`"
            f"  AI错误识别: `{f.get('ai_intent', 'UNKNOWN')}`"
            f"  用户期望意图: `{f.get('user_input', '')}`"
            f"  用户备注: {f.get('comment', '无')}"
            for f in error_feedbacks
        ])
        
        prompt = f"""你是一个资深产品经理，为"茗花智能汇报系统"生成需求分析文档。

## 现有系统背景
- 水果进货数据管理系统 + 智能对话助手
- 支持周报/月报/跨周对比/水果查询/店铺查询
- 意图识别采用三级混合模式：闲聊过滤 → 正则匹配 → AI识别

## 用户反馈（需要分析的错误识别）
{feedback_summary}

请生成完整的**需求分析文档**，包含以下章节：

# 需求分析文档

## 1. 概述
- 产品背景
- 产品目标
- 目标用户

## 2. 问题分析
### 2.1 用户反馈问题
（列出所有反馈的问题）

### 2.2 根本原因
（分析为什么AI识别错误）

### 2.3 影响范围
（这些问题影响哪些功能）

## 3. 需求定义
### 3.1 功能需求
（针对每个问题，定义具体的功能需求）

### 3.2 非功能需求
（性能、可扩展性等）

### 3.3 用户交互需求
（界面、反馈机制等）

## 4. 改进方案
### 4.1 短期方案
（快速修复）

### 4.2 中期方案
（规则优化）

### 4.3 长期方案
（架构优化）

## 5. 优先级
（按优先级排序需求）

请用 Markdown 格式返回完整文档。"""
        
        return self.call_ai(prompt)
    
    def generate_design_doc(self, feedbacks: List[Dict], requirements: str) -> str:
        """生成软件设计文档"""
        error_feedbacks = [f for f in feedbacks if f.get('user_input')]
        
        if not error_feedbacks:
            return "暂无错误反馈需要处理"
        
        feedback_summary = "\n".join([
            f"- 用户输入: `{f.get('message', '')}` → 期望: `{f.get('user_input', '')}`"
            for f in error_feedbacks
        ])
        
        prompt = f"""你是一个资深架构师，为"茗花智能汇报系统"生成软件设计文档。

## 现有系统架构
- 两个独立软件：茗花（原版，数据API端口8081）+ 茗花进化插件（智能对话端口3001）
- 插件采用三层架构：通用层（意图识别/对话记录/进化引擎） + 适配层（代码执行器/API路由）
- 意图识别：三级混合模式（闲聊过滤 → 正则匹配 → AI识别）
- 进化机制：用户反馈 → AI分析 → 规则改进

## 本次需要设计的需求
{requirements}

## 用户反馈（需要解决的识别错误）
{feedback_summary}

请生成完整的**软件设计文档**，包含以下章节：

# 软件设计文档

## 1. 系统概述
- 设计目标
- 核心特性
- 设计原则

## 2. 系统架构
- 架构图
- 模块设计
- 耦合点分析

## 3. 模块详细设计
### 3.1 改进的意图识别模块
（针对用户反馈的设计改进）

### 3.2 新增/修改的功能模块
（如有）

### 3.3 数据流设计

## 4. 接口设计
- API 接口
- 内部模块接口

## 5. 数据库设计
（如有）

## 6. 配置设计
- 意图规则配置
- 进化配置

## 7. 测试计划
- 单元测试
- 集成测试

请用 Markdown 格式返回完整文档。"""
        
        return self.call_ai(prompt)
    
    def save_documents(self, requirements: str, design: str) -> Dict[str, str]:
        """保存文档到文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存需求分析文档
        req_filename = f"requirements_{timestamp}.md"
        req_filepath = os.path.join(self.design_dir, req_filename)
        
        req_content = f"""# 需求分析文档

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

{requirements}

---

*本文档由进化引擎自动生成*
"""
        
        with open(req_filepath, 'w', encoding='utf-8') as f:
            f.write(req_content)
        
        # 保存软件设计文档
        des_filename = f"design_{timestamp}.md"
        des_filepath = os.path.join(self.design_dir, des_filename)
        
        des_content = f"""# 软件设计文档

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

{design}

---

*本文档由进化引擎自动生成*
"""
        
        with open(des_filepath, 'w', encoding='utf-8') as f:
            f.write(des_content)
        
        return {
            "requirements_file": req_filepath,
            "design_file": des_filepath
        }
    
    def mark_processed(self, feedbacks: List[Dict]):
        """标记反馈为已处理"""
        all_feedbacks = self.load_feedbacks()
        
        processed_messages = [(f.get('message', ''), f.get('timestamp', '')) for f in feedbacks]
        
        for f in all_feedbacks:
            key = (f.get('message', ''), f.get('timestamp', ''))
            if key in processed_messages:
                f['processed'] = True
                f['processed_at'] = datetime.now().isoformat()
        
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(all_feedbacks, f, ensure_ascii=False, indent=2)
    
    def generate_full_docs(self) -> Dict:
        """生成完整的需求和设计文档"""
        # 1. 获取未处理的反馈
        feedbacks = self.get_unprocessed_feedbacks()
        
        # 也包含已处理但想重新分析的错误反馈
        all_error_feedbacks = [
            f for f in self.load_feedbacks() 
            if f.get('user_input')  # 用户提交了期望的输入
        ]
        
        if not all_error_feedbacks:
            return {
                "success": False,
                "message": "暂无需要处理的错误反馈"
            }
        
        print(f"📊 分析 {len(all_error_feedbacks)} 条错误反馈...")
        
        # 2. 生成需求分析文档
        print("📝 生成需求分析文档...")
        requirements = self.generate_requirements_doc(all_error_feedbacks)
        
        # 3. 生成软件设计文档
        print("📐 生成软件设计文档...")
        design = self.generate_design_doc(all_error_feedbacks, requirements)
        
        # 4. 保存文档
        print("💾 保存文档...")
        files = self.save_documents(requirements, design)
        
        # 5. 标记已处理
        self.mark_processed(feedbacks)
        
        return {
            "success": True,
            "feedback_count": len(all_error_feedbacks),
            "requirements_file": files["requirements_file"],
            "design_file": files["design_file"],
            "latest_requirements": files["latest_requirements"],
            "latest_design": files["latest_design"],
            "requirements": requirements,
            "design": design
        }

    def generate_from_requirements(self, requirements: List[Dict]) -> Dict:
        """从需求列表生成需求文档"""
        if not requirements:
            return {"success": False, "message": "暂无需求"}
        
        # 构建需求摘要
        req_summary = "\n".join([
            f"- 用户需求: `{r.get('requirement', '')}`"
            f"  原始输入: `{r.get('original_message', '')}`"
            f"  详细说明: {r.get('description', '无')}"
            for r in requirements
        ])
        
        prompt = f"""你是一个资深产品经理，为"茗花智能汇报系统"生成需求分析文档。

## 现有系统背景
- 水果进货数据管理系统 + 智能对话助手
- 支持周报/月报/跨周对比/水果查询/店铺查询
- 意图识别采用三级混合模式

## 用户提交的需求
{req_summary}

请生成完整的**需求分析文档**，包含：
1. 概述（背景、目标）
2. 需求分析（每个需求的详细描述）
3. 优先级（高/中/低）
4. 实现建议

用 Markdown 格式返回。"""
        
        requirements_content = self.call_ai(prompt)
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"requirements_{timestamp}.md"
        filepath = os.path.join(self.design_dir, filename)
        
        content = f"""# 需求分析文档

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**需求数量**: {len(requirements)}

---

{requirements_content}

---

*本文档由进化引擎自动生成*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "requirements": requirements_content,
            "requirements_file": filepath
        }

    def generate_design_from_requirements(self, requirements: List[Dict], requirements_content: str = "") -> Dict:
        """从需求生成设计文档"""
        if not requirements:
            return {"success": False, "message": "暂无需求"}
        
        req_summary = "\n".join([
            f"- 用户需求: `{r.get('requirement', '')}`"
            for r in requirements
        ])
        
        prompt = f"""你是一个资深架构师，为"茗花智能汇报系统"生成软件设计文档。

## 现有系统架构
- 茗花进化插件（三层架构：通用层 + 适配层 + API层）
- 意图识别：三级混合模式
- 进化机制：用户反馈 → AI分析 → 规则改进

## 需要设计的需求
{req_summary}

请生成完整的**软件设计文档**，包含：
1. 系统概述
2. 模块设计
3. 接口设计
4. 数据流设计

用 Markdown 格式返回。"""
        
        design_content = self.call_ai(prompt)
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"design_{timestamp}.md"
        filepath = os.path.join(self.design_dir, filename)
        
        content = f"""# 软件设计文档

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

{design_content}

---

*本文档由进化引擎自动生成*
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "design": design_content,
            "design_file": filepath
        }


def main():
    """命令行入口"""
    generator = RequirementsDocGenerator()
    result = generator.generate_full_docs()
    
    if result["success"]:
        print("\n" + "="*50)
        print("✅ 文档生成完成！")
        print("="*50)
        print(f"📊 处理反馈: {result['feedback_count']} 条")
        print(f"\n📄 需求分析文档:")
        print(f"   {result['requirements_file']}")
        print(f"\n📐 软件设计文档:")
        print(f"   {result['design_file']}")
        print(f"\n📂 最新文档:")
        print(f"   {result['latest_requirements']}")
        print(f"   {result['latest_design']}")
    else:
        print(f"❌ {result['message']}")


if __name__ == "__main__":
    main()
