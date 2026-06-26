const BASE = '/api'

export interface Session {
  id: string
  title: string
  last_update_time: number
  message_count: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface SessionDetail extends Session {
  messages: Message[]
}

export interface Artifact {
  filename: string
  mime_type: string | null
  version: number
  create_time: number | null
}

export type SSEEvent =
  | { type: 'text'; content: string; author: string }
  | { type: 'tool_call'; name: string; args: Record<string, unknown> }
  | { type: 'tool_result'; name: string; result: unknown }
  | { type: 'artifact_saved'; keys: string[] }
  | { type: 'thinking'; content: string }
  | { type: 'done' }
  | { type: 'error'; message: string }

export const api = {
  async createSession(title?: string): Promise<Session> {
    const r = await fetch(`${BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
    return r.json()
  },

  async listSessions(): Promise<Session[]> {
    const r = await fetch(`${BASE}/sessions`)
    return r.json()
  },

  async getSession(id: string): Promise<SessionDetail> {
    const r = await fetch(`${BASE}/sessions/${id}`)
    return r.json()
  },

  async renameSession(id: string, title: string): Promise<void> {
    await fetch(`${BASE}/sessions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    })
  },

  async deleteSession(id: string): Promise<void> {
    await fetch(`${BASE}/sessions/${id}`, { method: 'DELETE' })
  },

  async listArtifacts(sessionId: string): Promise<Artifact[]> {
    const r = await fetch(`${BASE}/artifacts?session_id=${encodeURIComponent(sessionId)}`)
    return r.json()
  },

  artifactDownloadUrl(sessionId: string, filename: string): string {
    return `${BASE}/artifacts/download?session_id=${encodeURIComponent(sessionId)}&filename=${encodeURIComponent(filename)}`
  },

  streamChat(
    sessionId: string,
    message: string,
    onEvent: (e: SSEEvent) => void,
    onDone: () => void,
  ): () => void {
    const controller = new AbortController()

    fetch(`${BASE}/sessions/${sessionId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    }).then(async (res) => {
      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })

        const blocks = buf.split('\n\n')
        buf = blocks.pop() ?? ''

        for (const block of blocks) {
          const eventLine = block.match(/^event: (.+)$/m)?.[1]
          const dataLine = block.match(/^data: (.+)$/m)?.[1]
          if (!eventLine || !dataLine) continue
          try {
            const payload = JSON.parse(dataLine)
            const e = { type: eventLine, ...payload } as SSEEvent
            onEvent(e)
            if (eventLine === 'done' || eventLine === 'error') onDone()
          } catch {}
        }
      }
    }).catch(() => {})

    return () => controller.abort()
  },
}
