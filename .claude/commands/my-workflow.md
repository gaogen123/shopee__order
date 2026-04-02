---
description: my-workflow
---
```mermaid
flowchart TD
    start_node_default([开始])
    fetch_comments[fetch-comments]
    analyze_sentiment[analyze-sentiment]
    export_json[export-json]
    end_node_default([结束])

    start_node_default --> fetch_comments
    fetch_comments --> analyze_sentiment
    analyze_sentiment --> export_json
    export_json --> end_node_default
```

## 工作流执行指南

按照上方的Mermaid流程图执行工作流。每种节点类型的执行方法如下所述。

### 各节点类型的执行方法

- **矩形节点**：使用Task工具执行子代理
- **菱形节点（AskUserQuestion:...）**：使用AskUserQuestion工具提示用户并根据其响应进行分支
- **菱形节点（Branch/Switch:...）**：根据先前处理的结果自动分支（参见详细信息部分）
- **矩形节点（Prompt节点）**：执行下面详细信息部分中描述的提示
