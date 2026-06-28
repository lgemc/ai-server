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
    <aside className={`sidebar${isOpen ? ' open' : ''} w-[240px] min-w-[240px] bg-[var(--bg2)] border-r border-[var(--border)] flex flex-col h-full`}>
      <div className="p-[16px_12px_12px] border-b border-[var(--border)]">
        <div className="text-[13px] font-semibold text-[var(--accent2)] mb-[10px] tracking-wider">
          AI AGENT
        </div>
        <button onClick={onCreate} className="w-full px-3 py-2 bg-[var(--accent)] text-white border-none rounded-md cursor-pointer text-[13px] font-medium">+ New chat</button>
      </div>

      <div className="overflow-y-auto flex-1 p-[8px_6px]">
        {sorted.length === 0 && (
          <div className="text-[var(--text2)] text-[13px] text-center mt-6">
            No sessions yet
          </div>
        )}
        {sorted.map(s => (
          <div
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`flex items-center gap-1.5 p-2 rounded-md cursor-pointer mb-[2px] border-transparent transition-colors duration-150 ${
              activeId === s.id ? 'bg-[var(--bg3)] border-[var(--accent)]' : 'bg-transparent border-transparent'
            }`}
          >
            {editing === s.id ? (
              <input
                autoFocus
                value={editValue}
                onChange={e => setEditValue(e.target.value)}
                onBlur={() => commitEdit(s.id)}
                onKeyDown={e => { if (e.key === 'Enter') commitEdit(s.id); if (e.key === 'Escape') setEditing(null) }}
                onClick={e => e.stopPropagation()}
                className="flex-1 min-w-0 text-[13px] overflow-hidden text-ellipsis whitespace-nowrap"
              />
            ) : (
              <>
                <span className="flex-1 text-[13px] overflow-hidden text-ellipsis whitespace-nowrap">
                  {s.title}
                </span>
                <span className="text-[var(--text2)] text-[11px]">{s.message_count}msg</span>
                <button onClick={e => startEdit(s, e)} className="bg-none border-none cursor-pointer text-[var(--text2)] text-[13px] p-[2px_4px] rounded-sm flex-shrink-0" title="Rename">✎</button>
                <button onClick={e => { e.stopPropagation(); onDelete(s.id) }} className="bg-none border-none cursor-pointer text-[var(--danger)] text-[13px] p-[2px_4px] rounded-sm flex-shrink-0" title="Delete">✕</button>
              </>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}


