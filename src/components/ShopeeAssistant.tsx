import { useState, useRef, useEffect } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, Sparkles, ShoppingBag, Plus, MessageSquare, Trash2, Menu } from "lucide-react";
import { cn } from "./ui/utils";

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    isStreaming?: boolean;
}

interface Session {
    id: string;
    title: string;
    createdAt: number;
    messages: Message[];
}

const WELCOME_MESSAGE: Message = {
    id: 'welcome',
    role: 'assistant',
    content: `👋 您好！我是您的 **Shopee 智能助手**，基于多智能体（Multi-Agent）架构构建。

我可以为您提供以下能力支持：

🚀 **全网选品采集**
目前支持 **拼多多** 商品数据的深度采集，包括主图、价格、详细参数及卖点分析。

🏗️ **店铺智能运营 (即将上线)**
• **智能刊登**：一键将采集商品优化并同步至 Shopee 店铺
• **活动中心**：AI 辅助策划促销方案，提高转化率
• **市场雷达**：实时监控竞品动态与行业趋势

您可以试着对我说：*"帮我搜一下拼多多上的智能充电宝，要大容量的"*`
};

export function ShopeeAssistant() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [isTyping, setIsTyping] = useState(false);
    const [query, setQuery] = useState("");
    const [showSidebar, setShowSidebar] = useState(true);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Initialize sessions from localStorage
    useEffect(() => {
        const savedSessions = localStorage.getItem('shopee_agent_sessions');
        if (savedSessions) {
            try {
                const parsed = JSON.parse(savedSessions);
                setSessions(parsed);
                if (parsed.length > 0) {
                    setCurrentSessionId(parsed[0].id);
                } else {
                    createNewSession();
                }
            } catch (e) {
                console.error("Failed to parse sessions", e);
                createNewSession();
            }
        } else {
            createNewSession();
        }
    }, []);

    // Save sessions to localStorage whenever they change
    useEffect(() => {
        if (sessions.length > 0) {
            localStorage.setItem('shopee_agent_sessions', JSON.stringify(sessions));
        }
    }, [sessions]);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [currentSessionId, sessions]);

    // Focus input when session changes
    useEffect(() => {
        inputRef.current?.focus();
    }, [currentSessionId]);

    const createNewSession = () => {
        const newSessionId = Date.now().toString();
        const newSession: Session = {
            id: newSessionId,
            title: "新对话",
            createdAt: Date.now(),
            messages: [WELCOME_MESSAGE]
        };
        setSessions(prev => [newSession, ...prev]);
        setCurrentSessionId(newSessionId);
        if (window.innerWidth < 768) setShowSidebar(false);
    };

    const deleteSession = (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        const newSessions = sessions.filter(s => s.id !== sessionId);
        setSessions(newSessions);
        if (sessionId === currentSessionId) {
            if (newSessions.length > 0) {
                setCurrentSessionId(newSessions[0].id);
            } else {
                createNewSession(); // If all deleted, create new
            }
        }
    };

    const getCurrentMessages = () => {
        const session = sessions.find(s => s.id === currentSessionId);
        return session ? session.messages : [];
    };

    const updateCurrentSessionMessages = (newMessages: Message[]) => {
        setSessions(prev => prev.map(s => {
            if (s.id === currentSessionId) {
                // Update title if it's the first user message
                let title = s.title;
                if (s.messages.length <= 1 && newMessages.length > 1) {
                    const firstUserMsg = newMessages.find(m => m.role === 'user');
                    if (firstUserMsg) {
                        title = firstUserMsg.content.slice(0, 15) + (firstUserMsg.content.length > 15 ? '...' : '');
                    }
                }
                return { ...s, messages: newMessages, title };
            }
            return s;
        }));
    };

    const handleSend = async () => {
        if (!query.trim() || isTyping || !currentSessionId) return;

        const userMsgId = Date.now().toString();
        const userMsg: Message = { id: userMsgId, role: 'user', content: query };

        const currentMsgs = getCurrentMessages();
        const newMsgs = [...currentMsgs, userMsg];

        updateCurrentSessionMessages(newMsgs);
        setQuery("");
        setIsTyping(true);

        try {
            // Placeholder for assistant
            const assistantMsgId = (Date.now() + 1).toString();
            const assistantMsg: Message = {
                id: assistantMsgId,
                role: 'assistant',
                content: "",
                isStreaming: true
            };

            updateCurrentSessionMessages([...newMsgs, assistantMsg]);

            // Connect to SSE stream
            const eventSource = new EventSource(`http://localhost:9000/api/agent/stream?query=${encodeURIComponent(userMsg.content)}&session_id=${currentSessionId}`);

            let fullContent = "";

            eventSource.onmessage = (event) => {
                if (event.data === "[DONE]") {
                    eventSource.close();
                    setIsTyping(false);
                    setSessions(prev => prev.map(s => {
                        if (s.id === currentSessionId) {
                            return {
                                ...s,
                                messages: s.messages.map(msg =>
                                    msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg
                                )
                            };
                        }
                        return s;
                    }));
                    return;
                }

                const textChunk = event.data.replace(/<br>/g, '\n');
                fullContent += textChunk;

                setSessions(prev => prev.map(s => {
                    if (s.id === currentSessionId) {
                        return {
                            ...s,
                            messages: s.messages.map(msg =>
                                msg.id === assistantMsgId ? { ...msg, content: fullContent } : msg
                            )
                        };
                    }
                    return s;
                }));
            };

            eventSource.onerror = (err) => {
                console.error("EventSource failed:", err);
                eventSource.close();
                setIsTyping(false);
                setSessions(prev => prev.map(s => {
                    if (s.id === currentSessionId) {
                        return {
                            ...s,
                            messages: s.messages.map(msg =>
                                msg.id === assistantMsgId ? { ...msg, isStreaming: false, content: fullContent + "\n\n[连接中断，请重试]" } : msg
                            )
                        };
                    }
                    return s;
                }));
            };

        } catch (error) {
            console.error("Error sending message:", error);
            setIsTyping(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex h-full bg-white relative overflow-hidden">
            {/* Sidebar Overlay for Mobile */}
            {showSidebar && (
                <div
                    className="fixed inset-0 bg-black/20 z-20 md:hidden"
                    onClick={() => setShowSidebar(false)}
                />
            )}

            {/* Sidebar */}
            <div className={cn(
                "flex flex-col w-64 border-r border-gray-100 bg-gray-50/50 absolute md:relative z-30 h-full transition-transform duration-300 ease-in-out",
                showSidebar ? "translate-x-0" : "-translate-x-full md:translate-x-0 md:w-0 md:border-none md:overflow-hidden"
            )}>
                <div className="p-4">
                    <button
                        onClick={createNewSession}
                        className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-xl transition-all shadow-sm shadow-blue-200 font-medium"
                    >
                        <Plus className="w-5 h-5" />
                        新对话
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto px-2 space-y-1">
                    {sessions.map(session => (
                        <div
                            key={session.id}
                            onClick={() => {
                                setCurrentSessionId(session.id);
                                if (window.innerWidth < 768) setShowSidebar(false);
                            }}
                            className={cn(
                                "group flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer transition-all border border-transparent",
                                currentSessionId === session.id
                                    ? "bg-white border-gray-200 shadow-sm text-gray-900"
                                    : "hover:bg-gray-100 text-gray-500 hover:text-gray-900"
                            )}
                        >
                            <MessageSquare className={cn(
                                "w-4 h-4 shrink-0",
                                currentSessionId === session.id ? "text-blue-600" : "text-gray-400 group-hover:text-gray-600"
                            )} />
                            <span className="truncate text-sm font-medium flex-1">{session.title}</span>
                            <button
                                onClick={(e) => deleteSession(e, session.id)}
                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 hover:text-red-500 rounded transition-all"
                            >
                                <Trash2 className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col h-full relative w-full">
                {/* Mobile Header */}
                <div className="md:hidden flex items-center p-4 border-b border-gray-100 bg-white">
                    <button onClick={() => setShowSidebar(true)} className="p-2 -ml-2 hover:bg-gray-50 rounded-lg">
                        <Menu className="w-6 h-6 text-gray-600" />
                    </button>
                    <span className="ml-2 font-semibold text-gray-800">Shopee 助手</span>
                </div>

                {/* Sidebar Toggle for Desktop (Optional, kept hidden for simplicity or can be added) */}
                <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-[#f8f9fa]">
                    {/* Toggle Sidebar Button Desktop */}
                    <button
                        onClick={() => setShowSidebar(!showSidebar)}
                        className="hidden md:flex absolute left-4 top-4 z-10 p-2 bg-white/80 backdrop-blur border border-gray-200 rounded-lg shadow-sm hover:bg-white text-gray-500 hover:text-gray-700 transition-all"
                        title={showSidebar ? "收起侧边栏" : "展开侧边栏"}
                    >
                        <Menu className="w-5 h-5" />
                    </button>

                    {getCurrentMessages().map((msg) => (
                        <div
                            key={msg.id}
                            className={cn(
                                "flex gap-8 max-w-7xl mx-auto w-full",
                                msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                            )}
                        >
                            <div className={cn(
                                "w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-sm text-white",
                                msg.role === 'assistant'
                                    ? "bg-gradient-to-tr from-blue-600 to-indigo-600"
                                    : "bg-gray-400"
                            )}>
                                {msg.role === 'assistant' ? <Bot className="w-6 h-6" /> : <User className="w-6 h-6" />}
                            </div>

                            <div className={cn(
                                "flex flex-col flex-1 min-w-0",
                                msg.role === 'user' ? "items-end" : "items-start"
                            )}>
                                <span className="text-xs text-gray-400 mb-1 px-1">
                                    {msg.role === 'assistant' ? 'Shopee 智能助理' : '我'}
                                </span>

                                <div className={cn(
                                    "px-8 py-6 rounded-3xl text-[17px] leading-normal shadow-sm whitespace-pre-wrap tracking-normal text-gray-800",
                                    msg.role === 'assistant'
                                        ? "bg-white border border-t-0 border-gray-100 rounded-tl-none"
                                        : "bg-blue-600 text-white rounded-tr-none shadow-blue-600/20 max-w-[85%]"
                                )}>
                                    {msg.role === 'assistant' ? (
                                        <div className="markdown-body">
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                components={{
                                                    ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2 space-y-0.5 text-gray-700" {...props} />,
                                                    ol: ({ node, ...props }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5 text-gray-700" {...props} />,
                                                    li: ({ node, ...props }) => <li className="pl-0.5" {...props} />,
                                                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0 text-gray-700 block min-h-[1.2em]" {...props} />,
                                                    h1: ({ node, ...props }) => <h1 className="text-lg font-bold mb-2 mt-3 text-gray-900 first:mt-0" {...props} />,
                                                    h2: ({ node, ...props }) => <h2 className="text-base font-bold mb-1.5 mt-2.5 text-gray-900 first:mt-0" {...props} />,
                                                    h3: ({ node, ...props }) => <h3 className="text-base font-bold mb-1 mt-2 text-gray-900 first:mt-0" {...props} />,
                                                    strong: ({ node, ...props }) => <strong className="font-semibold text-gray-900" {...props} />,
                                                    table: ({ node, ...props }) => (
                                                        <div className="overflow-x-auto my-4 rounded-xl border border-gray-100 shadow-sm transition-all hover:shadow-md">
                                                            <table className="min-w-full divide-y divide-gray-100 bg-white" {...props} />
                                                        </div>
                                                    ),
                                                    thead: ({ node, ...props }) => <thead className="bg-gray-50/50" {...props} />,
                                                    th: ({ node, ...props }) => <th className="px-4 py-3 text-left text-xs font-bold text-gray-900 uppercase tracking-wider" {...props} />,
                                                    td: ({ node, ...props }) => <td className="px-4 py-3 text-sm text-gray-700 border-t border-gray-50" {...props} />,
                                                    img: ({ node, ...props }) => (
                                                        <img
                                                            className="max-w-[120px] h-auto rounded-lg shadow-sm border border-gray-50 bg-gray-50 transition-transform hover:scale-105"
                                                            {...props}
                                                            loading="lazy"
                                                        />
                                                    ),
                                                    a: ({ node, ...props }) => <a className="text-blue-600 hover:text-blue-800 font-medium underline-offset-4 hover:underline transition-colors" target="_blank" rel="noopener noreferrer" {...props} />,
                                                    code: ({ node, ...props }) => {
                                                        // @ts-ignore
                                                        const { inline, className, children } = props;
                                                        return inline ? (
                                                            <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono text-pink-600" {...props} />
                                                        ) : (
                                                            <code className="block bg-gray-50 p-4 rounded-xl text-sm font-mono overflow-x-auto my-4 text-gray-800 border border-gray-100" {...props} />
                                                        );
                                                    }
                                                }}
                                            >
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        msg.content
                                    )}
                                    {msg.isStreaming && (
                                        <span className="inline-block w-2 h-4 ml-1 align-middle bg-blue-400 animate-pulse"></span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>

                <div className="p-8 sm:p-10 bg-white border-t border-gray-100 z-20">
                    <div className="max-w-7xl mx-auto relative">
                        <input
                            ref={inputRef}
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="输入您的问题或指令..."
                            disabled={isTyping}
                            className="w-full pl-5 pr-14 py-4 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm text-base disabled:bg-gray-50 disabled:text-gray-400"
                        />
                        <button
                            onClick={handleSend}
                            disabled={!query.trim() || isTyping}
                            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-lg transition-all shadow-sm"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
