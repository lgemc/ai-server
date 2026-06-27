import { useEffect, useState, useCallback } from 'react'
import { api, type Session, type Message, type Artifact } from './api/client'
import { Sidebar } from './components/Sidebar'
import { ChatPane } from './components/ChatPane'
import { ArtifactPanel } from './components/ArtifactPanel'

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [artifacts, setArtifacts] = useState<Artifact[]>([])

  const loadSessions = useCallback(async () => {
    const s = await api.listSessions()
    setSessions(s)
  }, [])

  const loadSession = useCallback(async (id: string) => {
    const s = await api.getSession(id)
    setMessages(s.messages)
    setActiveId(id)
    const a = await api.listArtifacts(id)
    setArtifacts(a)
  }, [])

  const refreshArtifacts = useCallback(async () => {
    if (!activeId) return
    const a = await api.listArtifacts(activeId)
    setArtifacts(a)
  }, [activeId])

  useEffect(() => {
    loadSessions()
  }, [])

  const handleCreate = async () => {
    const s = await api.createSession()
    await loadSessions()
    loadSession(s.id)
  }

  const handleSelect = (id: string) => {
    if (id === activeId) return
    setMessages([])
    setArtifacts([])
    loadSession(id)
  }

  const handleDelete = async (id: string) => {
    await api.deleteSession(id)
    if (activeId === id) {
      setActiveId(null)
      setMessages([])
      setArtifacts([])
    }
    await loadSessions()
  }

  const handleRename = async (id: string, title: string) => {
    await api.renameSession(id, title)
    await loadSessions()
  }

  const handleMessagesUpdate = useCallback((next: Message[] | ((prev: Message[]) => Message[])) => {
    if (typeof next === 'function') {
      setMessages(next)
    } else {
      setMessages(next)
    }
    loadSessions()
  }, [loadSessions])

  const handleStreamDone = useCallback(() => {
    if (activeId) loadSession(activeId)
  }, [activeId, loadSession])

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={handleSelect}
        onCreate={handleCreate}
        onDelete={handleDelete}
        onRename={handleRename}
      />
      <ChatPane
        sessionId={activeId}
        messages={messages}
        onMessagesUpdate={handleMessagesUpdate}
        onArtifactsChange={refreshArtifacts}
        onStreamDone={handleStreamDone}
      />
      {activeId && <ArtifactPanel sessionId={activeId} artifacts={artifacts} />}
    </div>
  )
}
