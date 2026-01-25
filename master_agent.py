import os
from typing import Annotated, Literal, TypedDict, Union
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pdd_agent_tools import crawl_pinduoduo

# 设置 DeepSeek API Key
os.environ["DEEPSEEK_API_KEY"] = "sk-edebb99b4b1045f19f3dd9c2621b8776"
BASE_URL = "https://api.deepseek.com"

from pdd_agent_tools import crawl_pinduoduo, crawl_pinduoduo_data
from shopee_agent_tools import publish_to_shopee_global
import contextvars

# 定义上下文变量，用于在工具中获取当前的 thread_id
current_thread_id = contextvars.ContextVar("thread_id", default=None)

# --- 1. 定义工具 (Tools) ---

@tool
def search_pdd_tool(keyword: str, quantity: int = 2, need_download: bool = False, session_id: str = None) -> str:
    """
    搜索拼多多(PDD)上的商品，并返回商品详情，包括价格和评论。
    
    Args:
        keyword: 商品的搜索关键词。
        quantity: 需要采集的商品数量 (默认为 2)。
        need_download: 是否需要下载商品详情和图片 (默认为 False)。
        session_id: 会话 ID，用于控制中断（由系统自动注入，无需 LLM 生成）。
    """
    try:
        return crawl_pinduoduo(keyword, limit=quantity, enable_download=need_download, session_id=session_id)
    except Exception as e:
        return f"Error crawling Pinduoduo: {str(e)}"

@tool
def crawl_and_publish_tool(keyword: str, quantity: int = 1, session_id: str = None) -> str:
    """
    采集拼多多商品并直接发布到 Shopee 全球商品。
    适用于用户明确要求“发布”、“上架”或“采集并发布”的场景。
    
    Args:
        keyword: 商品的搜索关键词。
        quantity: 需要采集并发布的商品数量 (默认为 1)。
        session_id: 会话 ID (由系统自动注入)。
    """
    results = []
    try:
        # 使用流式采集+发布
        for item in crawl_pinduoduo_data(keyword, limit=quantity, enable_download=True, session_id=session_id):
            global_id = publish_to_shopee_global(item)
            if global_id:
                results.append(f"✅ 成功发布: {item.get('title', '未知')} (Global ID: {global_id})")
            else:
                results.append(f"❌ 发布失败: {item.get('title', '未知')}")
        
        if not results:
            return "未找到相关商品或采集失败。"
        return "\n".join(results)
    except Exception as e:
        return f"Error in crawl_and_publish: {str(e)}"

# 工具列表
all_tools = [search_pdd_tool, crawl_and_publish_tool]

# --- 2. 定义状态 (State) ---

class AgentState(TypedDict):
    # messages 存储对话历史
    messages: Annotated[list, add_messages]
    # intent 记录意图判断结果: "crawl" 或 "chat"
    intent: str
    # task_instruction 记录分发给后端的具体指令
    task_instruction: str
    # keywords 记录提取出来的关键词
    keywords: str

# --- 3. 初始化 LLM ---

llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.environ["DEEPSEEK_API_KEY"],
    openai_api_base=BASE_URL,
    temperature=0
)

# --- 4. 定义 Agent 节点逻辑 ---

# 4.1 意图识别节点 (Intent Node)
def intent_node(state: AgentState):
    messages = state["messages"]
    
    system_prompt = SystemMessage(content="""你是 Shopee 智能助手的意图识别专家。
你的任务是分析用户的最新请求，判断其意图。
意图分类：
1. crawl: 用户想要寻找商品、查询价格、采集商品信息（目前仅支持拼多多）。
2. publish: 用户想要采集商品并发布/上架到 Shopee。
3. chat: 用户只是在打招呼、闲聊、询问不需要实时爬取的问题。

请以 JSON 格式回复：
{
  "intent": "crawl" 或 "publish" 或 "chat",
  "reason": "简短说明理由",
  "keywords": "提取出来的搜索关键词。注意：如果用户明确指定了搜索词（如：'搜索词为：XX'、'关键词：YY'），必须原文保留该搜索词",
  "instruction": "如果是 crawl，请汇总出具体的执行要求（如：数量、下载偏好等）；如果是 chat，请保持为空"
}
""")
    
    # 获取判断
    response = llm.invoke([system_prompt] + messages)
    
    # 简单解析 JSON (实际生产建议使用结构化输出工具)
    try:
        import json
        import re
        content = response.content
        # 兼容一些带 markdown code block 的回复
        json_str = re.search(r'\{.*\}', content, re.DOTALL).group()
        data = json.loads(json_str)
        intent = data.get("intent", "chat")
        instruction = data.get("instruction", "")
        keywords = data.get("keywords", "")
    except:
        intent = "chat"
        instruction = ""
        keywords = ""

    return {
        "intent": intent, 
        "task_instruction": instruction,
        "keywords": keywords,
        "messages": [AIMessage(content=f"判定意图：{intent} | 关键词：{keywords}")]
    }

# 4.2 意图路由
def intent_router(state: AgentState) -> Literal["crawler_tool_node", "response_node"]:
    if state["intent"] in ["crawl", "publish"]:
        return "crawler_tool_node"
    return "response_node"

# 4.3 爬虫工具节点 (Crawler Tool Node)
# 这个节点负责调用工具。我们让它绑定工具并思考如何调用。
crawler_llm = llm.bind_tools(all_tools)

from langchain_core.runnables import RunnableConfig

def crawler_tool_node(state: AgentState, config: RunnableConfig):
    messages = state["messages"]
    instruction = state["task_instruction"]
    keywords = state["keywords"]
    
    # 从 config 中获取 thread_id (即 session_id)
    thread_id = config.get("configurable", {}).get("thread_id")
    
    # 清理旧的停止文件，防止误判
    if thread_id:
        stop_file = f"/tmp/agent_stops/{thread_id}"
        if os.path.exists(stop_file):
            try:
                os.remove(stop_file)
                print(f"🧹 [Agent] 已清理旧的停止文件: {stop_file}")
            except Exception as e:
                print(f"⚠️ [Agent] 清理停止文件失败: {e}")
    
    system_prompt = SystemMessage(content=f"你是爬虫专家。用户想找：{keywords}。请根据以下详细要求调用工具获取数据：{instruction}")
    
    # 将 state 中的消息和指令结合
    response = crawler_llm.invoke([system_prompt] + messages)
    
    # 强制注入 session_id 到工具调用中
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call['name'] in ['search_pdd_tool', 'crawl_and_publish_tool']:
                tool_call['args']['session_id'] = thread_id
                print(f"🔧 [Agent] 已注入 session_id: {thread_id} 到工具调用")
                
    return {"messages": [response]}

# 4.4 爬虫路由 (判断是否需要执行工具)
def crawler_router(state: AgentState) -> Literal["tools", "response_node"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "response_node"

# 4.5 回复节点 (Response Node)
def response_node(state: AgentState):
    messages = state["messages"]
    keywords = state["keywords"]
    
    system_prompt = SystemMessage(content=f"""你是 Shopee 智能助手的首席客服。
你的任务是根据之前的对话历史和爬虫采集到的原始数据，整理出一份精美的回复给用户。

要求：
1. **展示搜索词**：在回复的开头明确告知用户你使用了搜索词：**{keywords}**。
2. **Markdown 表格展示**：必须使用 Markdown 表格形式对比展示所有采集到的商品。表格列应包括：
   - **主图**：使用 `![商品图](图片链接)` 语法展示预览图。如果链接为空则留白。
   - **商品名称**：包含标题，并将其设为指向“链接”的超链接。
   - **Global ID**：如果商品已发布，务必展示 Global Item ID；未发布则显示“-”。
   - **价格**：展示商品价格。
   - **核心卖点/详情**：简要概括详情中的重要参数（如材质、空间、是否有隔层等）。
3. **对比分析**：在表格下方根据用户提出的需求（如“空间要大”、“耐用”等）做简短的推荐建议。
4. **语气友好**：始终保持专业、友好的语气。
""")
    
    response = llm.invoke([system_prompt] + messages)
    return {"messages": [response]}


# --- 5. 构建图 (Graph) ---

builder = StateGraph(AgentState)

# 添加节点
builder.add_node("intent_node", intent_node)
builder.add_node("crawler_tool_node", crawler_tool_node)
builder.add_node("tools", ToolNode(all_tools))
builder.add_node("response_node", response_node)

# 定义边
builder.add_edge(START, "intent_node")

# 意图路由
builder.add_conditional_edges(
    "intent_node",
    intent_router,
    {
        "crawler_tool_node": "crawler_tool_node",
        "response_node": "response_node"
    }
)

# 爬虫逻辑边
builder.add_conditional_edges(
    "crawler_tool_node",
    crawler_router,
    {
        "tools": "tools",
        "response_node": "response_node"
    }
)

# 工具执行完回到爬虫节点继续思考
builder.add_edge("tools", "crawler_tool_node")

# 回复节点结束后结束
builder.add_edge("response_node", END)

# 初始化持久化内存 (MySQL)
from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
import pymysql

# 获取 MySQL 配置
mysql_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "shopee_orders"),
    "autocommit": True,
    "charset": 'utf8mb4'
}

# 连接到 MySQL 用于保存检查点
mysql_conn = pymysql.connect(**mysql_config)
memory = PyMySQLSaver(mysql_conn)
# 确保表结构已初始化
memory.setup()

graph = builder.compile(checkpointer=memory)

# --- 6. 辅助函数 ---

def run_agent_generator(query: str, thread_id: str = None):
    # 如果没有提供 thread_id，则生成一个新的
    if not thread_id:
        thread_id = f"shopee-{os.urandom(4).hex()}"
    
    print(f"🔄 [Agent] 使用会话 ID: {thread_id}")
    
    # 设置上下文变量
    token = current_thread_id.set(thread_id)
    
    # 每次运行传入用户消息
    initial_state = {"messages": [("user", query)]}
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        for event in graph.stream(initial_state, config=config):
            for node_name, value in event.items():
                if "messages" in value:
                    msg = value['messages'][-1]
                    content = msg.content
                    
                    # 格式化输出前缀和任务内容
                    tool_name_map = {
                        "search_pdd_tool": "拼多多商品采集器",
                        "crawl_and_publish_tool": "拼多多采集+Shopee发布助手",
                        "search_shopee_tool": "Shopee 商品采集器"
                    }
                    
                    display_msg = ""
                    if node_name == "intent_node":
                        display_msg = "\n\n🔍 **[意图分析]**：正在深度分析您的需求与关键词..."
                    elif node_name == "crawler_tool_node":
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            raw_tool_name = msg.tool_calls[0].get('name')
                            friendly_name = tool_name_map.get(raw_tool_name, raw_tool_name)
                            display_msg = f"\n\n🕸️ **[采集启动]**：已为你匹配到最好的采集方案，正在唤起【{friendly_name}】..."
                        else:
                            display_msg = "\n\n🔎 **[任务规划]**：正在为您梳理采集路径与策略..."
                    elif node_name == "tools":
                        display_msg = "\n\n⚙️ **[正在执行]**：正在为您精准抓取商品数据，这可能需要一点时间..."
                    elif node_name == "response_node":
                        display_msg = content
                    
                    if display_msg:
                        # 处理多行文本，确保符合 SSE 格式
                        # SSE 要求每一行数据都以 "data: " 开头
                        formatted_lines = []
                        for line in display_msg.split('\n'):
                            formatted_lines.append(f"data: {line}")
                        
                        # 合并成一个完整的 SSE 消息块，以双换行结束
                        sse_message = "\n".join(formatted_lines) + "\n\n"
                        yield sse_message

    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"
    
    yield "data: [DONE]\n\n"

if __name__ == "__main__":
    import sys
    print("🤖 启动 Shopee 智能助手 (Multi-Agent)...")
    
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "帮我在拼多多找一下'猫粮'的价格"
        
    print(f"👤 用户: {query}")
    for chunk in run_agent_generator(query):
        print(chunk.strip())
