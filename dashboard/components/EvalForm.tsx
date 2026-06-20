"use client";

import { useState } from "react";
import { evaluate, EvalResult } from "@/lib/api";

interface EvalFormProps {
  onResult: (result: EvalResult) => void;
  onError: (error: string) => void;
  onLoadingChange: (loading: boolean) => void;
}

const LLM_OPTIONS = [
  { value: "openai/gpt-4o", label: "OpenAI GPT-4o" },
  { value: "anthropic/claude-3-5-sonnet", label: "Anthropic Claude 3.5 Sonnet" },
  { value: "ollama/llama3", label: "Ollama Llama 3" },
  { value: "litellm/gpt-4", label: "LiteLLM GPT-4" },
];

export default function EvalForm({ onResult, onError, onLoadingChange }: EvalFormProps) {
  const [question, setQuestion] = useState("");
  const [contextChunks, setContextChunks] = useState<string[]>([""]);
  const [answer, setAnswer] = useState("");
  const [llm, setLlm] = useState("openai/gpt-4o");

  const handleAddChunk = () => setContextChunks([...contextChunks, ""]);
  const handleRemoveChunk = (i: number) => {
    if (contextChunks.length > 1) {
      setContextChunks(contextChunks.filter((_, idx) => idx !== i));
    }
  };
  const handleChunkChange = (i: number, value: string) => {
    const chunks = [...contextChunks];
    chunks[i] = value;
    setContextChunks(chunks);
  };

  const handleSubmit = async () => {
    if (!question.trim() || !answer.trim()) return;
    onLoadingChange(true);
    onError("");

    try {
      const result = await evaluate({
        question,
        context: contextChunks.filter((c) => c.trim()),
        answer,
        llm,
      });
      onResult(result);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      onLoadingChange(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">Question</label>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="input"
          placeholder="What is the capital of France?"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-sm font-medium">Context Chunks</label>
          <button type="button" onClick={handleAddChunk} className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
            + Add chunk
          </button>
        </div>
        {contextChunks.map((chunk, i) => (
          <div key={i} className="flex gap-2 mb-2">
            <textarea
              value={chunk}
              onChange={(e) => handleChunkChange(i, e.target.value)}
              className="input text-sm min-h-[60px]"
              placeholder={`Chunk ${i + 1}...`}
            />
            {contextChunks.length > 1 && (
              <button
                type="button"
                onClick={() => handleRemoveChunk(i)}
                className="text-red-500 hover:text-red-700 self-start pt-2 text-lg"
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Answer</label>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          className="input min-h-[80px]"
          placeholder="The capital of France is Paris."
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">LLM</label>
        <select value={llm} onChange={(e) => setLlm(e.target.value)} className="input">
          {LLM_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!question.trim() || !answer.trim()}
        className="btn-primary w-full justify-center"
      >
        Run Evaluation
      </button>
    </div>
  );
}
