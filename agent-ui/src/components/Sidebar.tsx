import { useState } from 'react'
import type { Session } from '../api/client'

interface Props {
  sessions: Session[]
  activeId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
  onRename: (id: string, title: string) => void
  isOpen?: boolean
}

export function Sidebar({ sessions, activeId, onSelect, onCreate, onDelete, onRename, isOpen }: Props) {
  const [editing, setEditing] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const startEdit = (s: Session, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditing(s.id)
    setEditValue(s.title)
  }

  const commitEdit = (id: string) => {
    if (editValue.trim()) onRename(id, editValue.trim())
    setEditing(null)
  }

  const sorted = [...sessions].sort((a, b) => b.last_update_time - a.last_update_time)

  return (
    <aside className={`sidebar${isOpen ? ' open' : ''}`} style={{
      width: 240, minWidth: 240, background: 'var(--bg2)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', height: '100%',
    }}>
      <div style={{ padding: '16px 12px 12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent2)', marginBottom: 10, letterSpacing: '0.05em' }}>
          AI AGENT
        </div>
        <button onClick={onCreate} style={newChatBtn}>+ New chat</button>
      </div>

      <div style={{ overflowY: 'auto', flex: 1, padding: '8px 6px' }}>
        {sorted.length === 0 && (
          <div style={{ color: 'var(--text2)', fontSize: 13, textAlign: 'center', marginTop: 24 }}>
            No sessions yet
          </div>
        )}
        {sorted.map(s => (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            style={{
              ...sessionItem,
              background: activeId === s.id ? 'var(--bg3)' : 'transparent',
              borderColor: activeId === s.id ? 'var(--accent)' : 'transparent',
            }}
          >
            {editing === s.id ? (
              <input
                autoFocus
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                onBlur={() => commitEdit(s.id)}
                onKeyDown={e => { if (e.key === 'Enter') commitEdit(s.id); if (e.key === 'Escape') setEditing(null) }}
                onClick={e => e.stopPropagation()}
                style={editInput}
              />
            ) : (
              <>
                <span style={{ flex: 1, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {s.title}
                </span>
                <span style={{ color: 'var(--text2)', fontSize: 11 }}>{s.message_count}msg</span>
                <button onClick={e => startEdit(s, e)} style={iconBtn} title="Rename">✎</button>
                <button onClick={e => { e.stopPropagation(); onDelete(s.id) }} style={{ ...iconBtn, color: 'var(--danger)' }} title="Delete">✕</button>
              </>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}

const newChatBtn: React.CSSProperties = {
  width: '100%', padding: '8px 12px', background: 'var(--accent)', color: '#fff',
  border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 500,
}

const sessionItem: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6, padding: '8px 8px',
  borderRadius: 6, cursor: 'pointer', marginBottom: 2,
  border: '1px solid transparent', transition: 'background 0.15s',
}

const iconBtn: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text2)',
  fontSize: 13, padding: '2px 4px', borderRadius: 4, flexShrink: 0,
}

const editInput: React.CSSProperties = {
  flex: 1, background: 'var(--bg3)', border: '1px solid var(--accent)',
  borderRadius: 4, color: 'var(--text)', fontSize: 13, padding: '2px 6px', outline: 'none',
}
