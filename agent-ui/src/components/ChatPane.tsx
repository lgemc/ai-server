import { useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message, Artifact, SSEEvent } from '../api/client'
import { api } from '../api/client'

interface ToolActivity {
  name: string
  status: 'running' | 'done'
  result?: unknown
}

interface ContentPart {
  type: 'think' | 'text'
  content: string
  partial?: boolean
}

function parseContent(text: string): ContentPart[] {
  const parts: ContentPart[] = []
  const regex = /<think>([\s\S]*?)<\/think>/g
  let last = 0
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push({ type: 'text', content: text.slice(last, match.index) })
    parts.push({ type: 'think', content: match[1] })
    last = match.index + match[0].length
  }
  const remaining = text.slice(last)
  const thinkStart = remaining.indexOf('<think>')
  if (thinkStart !== -1) {
    if (thinkStart > 0) parts.push({ type: 'text', content: remaining.slice(0, thinkStart) })
    parts.push({ type: 'think', content: remaining.slice(thinkStart + 7), partial: true })
  } else if (remaining) {
    parts.push({ type: 'text', content: remaining })
  }
  return parts
}

function MarkdownContent({ text, streaming }: { text: string; streaming?: boolean }) {
  const parts = parseContent(text)
  // Reorder: text first, thinking last
  const textParts = parts.filter(p => p.type === 'text')
  const thinkParts = parts.filter(p => p.type === 'think')
  const orderedParts = [...textParts, ...thinkParts]
  
  return (
    <>
      {orderedParts.map((p, i) =>
        p.type === 'think' ? (
          <details key={i} style={thinkDetails} open={p.partial}>
            <summary style={thinkSummary}>
              {p.partial ? '💭 Thinking…' : '💭 Thinking'}
            </summary>
            <div style={thinkBody}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{p.content}</ReactMarkdown>
            </div>
          </details>
        ) : (
          <div key={i} className="md-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{p.content}</ReactMarkdown>
            {streaming && i === orderedParts.length - 1 && (
              <span style={{ display: 'inline-block', width: 8, height: 14, background: 'var(--accent)', borderRadius: 1, marginLeft: 2, animation: 'blink 1s step-end infinite', verticalAlign: 'text-bottom' }} />
            )}
          </div>
        )
      )}
    </>
  )
}

interface Props {
  sessionId: string | null
  messages: Message[]
  onMessagesUpdate: (next: Message[] | ((prev: Message[]) => Message[])) => void
  onArtifactsChange: () => void
  onStreamDone?: () => void
}

export function ChatPane({ sessionId, messages, onMessagesUpdate, onArtifactsChange, onStreamDone }: Props) {
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [agentState, setAgentState] = useState<string | null>(null)
  const [streamBuffer, setStreamBuffer] = useState('')
  const [thinkBuffer, setThinkBuffer] = useState('')
  const [toolActivity, setToolActivity] = useState<ToolActivity | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamBuffer, toolActivity])

  const send = () => {
    if (!sessionId || !input.trim() || streaming) return
    const text = input.trim()
    setInput('')

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: Date.now() / 1000,
    }
    onMessagesUpdate([...messages, userMsg])
    setStreaming(true)
    setAgentState(null)
    setStreamBuffer('')
    setThinkBuffer('')
    setToolActivity(null)

    let buffer = ''
    let thinking = ''
    const abort = api.streamChat(sessionId, text, (e: SSEEvent) => {
      if (e.type === 'status') {
        setAgentState(e.state ?? null)
      } else if (e.type === 'text') {
        setAgentState(null)
        buffer += e.content
        flushSync(() => setStreamBuffer(buffer))
      } else if (e.type === 'thinking') {
        setAgentState(null)
        thinking += e.content
        flushSync(() => setThinkBuffer(thinking))
      } else if (e.type === 'tool_call') {
        setToolActivity({ name: e.name, status: 'running' })
      } else if (e.type === 'tool_result') {
        setToolActivity({ name: e.name, status: 'done', result: e.result })
      } else if (e.type === 'artifact_saved') {
        onArtifactsChange()
      }
    }, () => {
      if (buffer.trim() || thinking.trim()) {
        // Combine thinking and text into the final message
        let combinedContent = buffer
        if (thinking.trim()) {
          const wrappedThinking = thinking.trim().startsWith('<think>') ? thinking.trim() : `<think>${thinking.trim()}</think>`
          combinedContent = `${wrappedThinking}\n\n${buffer}`
        }
        const assistantMsg: Message = {
          id: Date.now().toString() + '-a',
          role: 'assistant',
          content: combinedContent,
          timestamp: Date.now() / 1000,
        }
        onMessagesUpdate((prev: Message[]) => [...prev, assistantMsg])
      }
      setStreamBuffer('')
      setThinkBuffer('')
      setToolActivity(null)
      setAgentState(null)
      setStreaming(false)
      onStreamDone?.()
    })
    abortRef.current = abort
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  if (!sessionId) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text2)' }}>
        Select or create a session to start chatting
      </div>
    )
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 0' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 24px' }}>
          {messages.length === 0 && !streaming && (
            <div style={{ textAlign: 'center', color: 'var(--text2)', marginTop: 60 }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🤖</div>
              <div style={{ fontSize: 15 }}>What can I help you with?</div>
              <div style={{ fontSize: 13, marginTop: 6, color: 'var(--text2)' }}>
                Try: "Transcribe this YouTube video: ..." or "What files do we have?"
              </div>
            </div>
          )}

          {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}

          {toolActivity && (
            <div style={toolBox}>
              <span style={{ color: toolActivity.status === 'running' ? 'var(--accent2)' : '#6acc6a' }}>
                {toolActivity.status === 'running' ? '⚙ ' : '✓ '}
              </span>
              <span style={{ fontSize: 12, color: 'var(--text2)' }}>
                {toolActivity.status === 'running' ? 'Calling ' : 'Done: '}
                <code style={{ color: 'var(--accent2)' }}>{toolActivity.name}</code>
                {toolActivity.status === 'running' && <span style={{ marginLeft: 6 }}>⋯</span>}
              </span>
            </div>
          )}

          {agentState === 'thinking' && !thinkBuffer && !streamBuffer && (
            <div style={assistantBubble}>
              <div style={bubbleLabel}>Assistant</div>
              <div style={{ color: 'var(--text2)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="thinking-spinner" />
                <span>Thinking…</span>
              </div>
            </div>
          )}

          {streamBuffer && (
            <div style={assistantBubble}>
              <div style={bubbleLabel}>Assistant</div>
              <MarkdownContent text={streamBuffer} streaming />
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)', padding: '16px 24px', background: 'var(--bg)' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', gap: 10 }}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Message the agent… (Enter to send, Shift+Enter for newline)"
            disabled={streaming}
            rows={1}
            style={inputStyle}
            onInput={e => {
              const t = e.currentTarget
              t.style.height = 'auto'
              t.style.height = Math.min(t.scrollHeight, 160) + 'px'
            }}
          />
          <button onClick={send} disabled={!input.trim() || streaming} style={sendBtn}>
            {streaming ? '…' : '↑'}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        .md-content p { margin: 0 0 8px; line-height: 1.65; }
        .md-content p:last-child { margin-bottom: 0; }
        .md-content h1,.md-content h2,.md-content h3 { margin: 12px 0 6px; font-weight: 600; line-height: 1.3; }
        .md-content h1 { font-size: 1.25em; }
        .md-content h2 { font-size: 1.1em; }
        .md-content h3 { font-size: 1em; }
        .md-content ul,.md-content ol { margin: 4px 0 8px; padding-left: 20px; }
        .md-content li { margin-bottom: 4px; line-height: 1.55; }
        .md-content code { background: var(--bg); border: 1px solid var(--border); border-radius: 4px; padding: 1px 5px; font-size: 0.85em; font-family: 'JetBrains Mono','Fira Code',monospace; }
        .md-content pre { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; overflow-x: auto; margin: 8px 0; }
        .md-content pre code { background: none; border: none; padding: 0; font-size: 0.82em; }
        .md-content blockquote { border-left: 3px solid var(--accent); margin: 8px 0; padding: 4px 12px; color: var(--text2); }
        .md-content a { color: var(--accent); text-decoration: underline; }
        .md-content table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 0.9em; }
        .md-content th,.md-content td { border: 1px solid var(--border); padding: 6px 10px; }
        .md-content th { background: var(--bg3); font-weight: 600; }
        .md-content hr { border: none; border-top: 1px solid var(--border); margin: 12px 0; }
        .thinking-spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{ ...messageRow, justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <div style={isUser ? userBubble : assistantBubble}>
        <div style={bubbleLabel}>{isUser ? 'You' : 'Assistant'}</div>
        {isUser
          ? <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{msg.content}</div>
          : <MarkdownContent text={msg.content} />
        }
      </div>
    </div>
  )
}

const messageRow: React.CSSProperties = { display: 'flex', marginBottom: 16 }
const bubbleBase: React.CSSProperties = { maxWidth: '82%', padding: '12px 16px', borderRadius: 12, fontSize: 14 }
const userBubble: React.CSSProperties = { ...bubbleBase, background: 'var(--user-bubble)', borderBottomRightRadius: 4, border: '1px solid var(--accent)' }
const assistantBubble: React.CSSProperties = { ...bubbleBase, background: 'var(--bg3)', borderBottomLeftRadius: 4, border: '1px solid var(--border)', marginBottom: 16 }
const bubbleLabel: React.CSSProperties = { fontSize: 11, fontWeight: 600, color: 'var(--text2)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }
const toolBox: React.CSSProperties = { display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', background: 'var(--tool-bg)', border: '1px solid var(--tool-border)', borderRadius: 8, marginBottom: 12, fontSize: 12 }
const inputStyle: React.CSSProperties = { flex: 1, background: 'var(--bg3)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)', fontSize: 14, padding: '12px 14px', resize: 'none', outline: 'none', lineHeight: 1.5, fontFamily: 'inherit' }
const sendBtn: React.CSSProperties = { width: 42, height: 42, alignSelf: 'flex-end', background: 'var(--accent)', border: 'none', borderRadius: 10, color: '#fff', fontSize: 18, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }
const thinkDetails: React.CSSProperties = { marginBottom: 10, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg)', overflow: 'hidden' }
const thinkSummary: React.CSSProperties = { padding: '6px 12px', cursor: 'pointer', fontSize: 12, color: 'var(--text2)', fontStyle: 'italic', userSelect: 'none' }
const thinkBody: React.CSSProperties = { padding: '8px 12px', borderTop: '1px solid var(--border)', fontSize: 12.5, color: 'var(--text2)', lineHeight: 1.6 }
