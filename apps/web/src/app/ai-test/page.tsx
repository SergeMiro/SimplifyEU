"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Send, Sparkles, Loader2, History, Trash2, ExternalLink } from "lucide-react";

export default function AITestPage() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<{prompt: string, response: string, date: string}[]>([]);

  // Load history on mount
  useEffect(() => {
    const saved = localStorage.getItem("ai_test_history");
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load history", e);
      }
    }
  }, []);

  const saveToHistory = (p: string, r: string) => {
    const newEntry = { prompt: p, response: r, date: new Date().toISOString() };
    const newHistory = [newEntry, ...history].slice(0, 10); // Keep last 10
    setHistory(newHistory);
    localStorage.setItem("ai_test_history", JSON.stringify(newHistory));
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem("ai_test_history");
  };

  const handleTest = async () => {
    if (!prompt.trim()) return;

    setLoading(true);
    setError("");
    setResponse("");

    try {
      const res = await fetch("/api/ai-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.error || "Unknown error");
        setLoading(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      
      if (!reader) {
        setError("Response body is null");
        setLoading(false);
        return;
      }

      let accumulatedResponse = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr === "[DONE]") continue;
            
            try {
              const data = JSON.parse(dataStr);
              const content = data.choices?.[0]?.delta?.content || "";
              accumulatedResponse += content;
              setResponse(accumulatedResponse);
            } catch (e) {
              // Ignore partial JSON
            }
          }
        }
      }
      
      saveToHistory(prompt, accumulatedResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  };

  const examplePrompts = [
    "Explain what SimplifyEU does in one paragraph",
    "List 5 benefits of AI in fintech",
    "What is a subscription leak detector?",
  ];

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-purple-100 via-background to-background dark:from-purple-950/20">
      {/* Header */}
      <header className="border-b bg-background/50 backdrop-blur-md sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/">
              <Button variant="ghost" size="sm" className="hover:bg-purple-100 dark:hover:bg-purple-900/40 transition-colors">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Home
              </Button>
            </Link>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-pink-500 rounded-lg flex items-center justify-center shadow-lg shadow-purple-500/20">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-pink-500">
                AI Lab
              </span>
            </div>
          </div>
          <div className="hidden md:flex items-center space-x-4">
            <Link href="/dashboard/services/subscription-detector">
              <Button variant="outline" size="sm" className="border-purple-200 hover:border-purple-500 text-purple-600 dark:text-purple-400">
                <ExternalLink className="mr-2 h-4 w-4" />
                Subscription Detector
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 lg:py-16 max-w-6xl">
        <div className="grid lg:grid-cols-[1fr_300px] gap-8">
          
          <div className="space-y-8">
            <div className="text-left">
              <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight mb-4">
                Test the <span className="text-purple-600">Future</span> of Finance
              </h1>
              <p className="text-md text-muted-foreground">
                Interact with Mistral-Small-3.1 via Chutes AI API.
              </p>
            </div>

            {/* Chat Interface */}
            <div className="rounded-3xl border border-purple-100 dark:border-purple-900/50 bg-card/80 backdrop-blur-sm shadow-2xl shadow-purple-500/5 overflow-hidden transition-all hover:shadow-purple-500/10">
              {/* Input Area */}
              <div className="p-8 border-b border-purple-50/50 dark:border-purple-900/20 bg-gradient-to-b from-purple-50/30 to-transparent dark:from-purple-900/10">
                <div className="flex gap-3">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Ask me anything about your finances or business..."
                    className="flex-1 min-h-[140px] p-5 rounded-2xl border border-purple-100 dark:border-purple-900/50 bg-background resize-none focus:outline-none focus:ring-4 focus:ring-purple-500/10 focus:border-purple-500 transition-all text-md"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && e.ctrlKey) {
                        handleTest();
                      }
                    }}
                  />
                </div>
                <div className="flex flex-col sm:flex-row items-center justify-between mt-6 gap-4">
                  <div className="flex flex-wrap gap-2">
                    {examplePrompts.map((example, i) => (
                      <button
                        key={i}
                        onClick={() => setPrompt(example)}
                        className="px-4 py-2 text-xs font-medium rounded-xl border border-purple-100 dark:border-purple-900/50 bg-background hover:bg-purple-50 dark:hover:bg-purple-900/30 hover:border-purple-300 transition-all"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                  <Button
                    onClick={handleTest}
                    disabled={loading || !prompt.trim()}
                    size="lg"
                    className="w-full sm:w-auto px-8 bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 text-white shadow-xl shadow-purple-500/20 rounded-xl"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-5 w-5" />
                        Send Stream
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Response Area */}
              <div className="p-8 min-h-[300px] bg-background/40">
                {error && (
                  <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-600 animate-in fade-in slide-in-from-top-2">
                    <p className="font-bold flex items-center"><Trash2 className="mr-2 h-4 w-4" /> Error</p>
                    <p className="text-sm mt-1 opacity-90">{error}</p>
                  </div>
                )}

                {response && (
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/[0.03] to-pink-500/[0.03] border border-purple-100/50 dark:border-purple-900/30">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-inner">
                        <Sparkles className="h-4 w-4 text-white" />
                      </div>
                      <span className="font-bold text-sm tracking-uppercase text-purple-700 dark:text-purple-300">AI ASSISTANT</span>
                    </div>
                    <div className="prose prose-purple dark:prose-invert max-w-none">
                      <p className="whitespace-pre-wrap leading-relaxed text-md">{response}</p>
                    </div>
                  </div>
                )}

                {!response && !error && !loading && (
                  <div className="text-center py-20 text-muted-foreground">
                    <div className="w-16 h-16 bg-purple-50 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-6">
                      <Sparkles className="h-8 w-8 text-purple-300 animate-pulse" />
                    </div>
                    <p className="text-md font-medium">Ready for your prompt</p>
                    <p className="text-sm opacity-70">Experience real-time AI generation</p>
                  </div>
                )}

                {loading && !response && (
                  <div className="text-center py-20">
                    <Loader2 className="h-16 w-16 mx-auto mb-6 animate-spin text-purple-500 opacity-50" />
                    <p className="text-md font-medium text-purple-600">Connecting to Chutes AI...</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Sidebar / History */}
          <aside className="space-y-6">
            <div className="p-6 rounded-3xl border border-purple-100 dark:border-purple-900/50 bg-card/50 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-bold flex items-center gap-2">
                  <History className="h-4 w-4 text-purple-500" />
                  Recent Lab Tests
                </h3>
                {history.length > 0 && (
                  <button onClick={clearHistory} className="text-muted-foreground hover:text-red-500 transition-colors">
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
              
              <div className="space-y-4">
                {history.map((item, i) => (
                  <div 
                    key={i} 
                    className="group p-4 rounded-2xl border border-transparent hover:border-purple-100 dark:hover:border-purple-900/50 hover:bg-background transition-all cursor-pointer"
                    onClick={() => { setPrompt(item.prompt); setResponse(item.response); }}
                  >
                    <p className="text-sm font-medium line-clamp-1 group-hover:text-purple-600 transition-colors">{item.prompt}</p>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      {new Date(item.date).toLocaleTimeString()}
                    </p>
                  </div>
                ))}
                
                {history.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <p className="text-xs italic">No history yet</p>
                  </div>
                )}
              </div>
            </div>

            <div className="p-6 rounded-3xl bg-gradient-to-br from-purple-600 to-pink-500 text-white shadow-xl shadow-purple-500/20">
              <h4 className="font-bold mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                Analyze Real Files
              </h4>
              <p className="text-xs opacity-90 mb-4">
                Use this AI model to scan your actual bank statements for hidden subscription leaks.
              </p>
              <Link href="/dashboard/services/subscription-detector">
                <Button variant="secondary" size="sm" className="w-full bg-white/20 hover:bg-white/30 border-0 text-white">
                  Try Subscription Detector
                </Button>
              </Link>
            </div>
          </aside>

        </div>
      </main>
    </div>
  );
}
