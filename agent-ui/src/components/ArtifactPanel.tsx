import type { Artifact } from '../api/client'
import { api } from '../api/client'

interface Props {
  sessionId: string
  artifacts: Artifact[]
}

const ICONS: Record<string, string> = {
  'text/plain': '📄',
  'audio/mpeg': '🎵',
  'audio/mp3': '🎵',
  'video/mp4': '🎬',
  'image/png': '🖼',
  'image/jpeg': '🖼',
}

function icon(mime: string | null) {
  if (!mime) return '📎'
  return ICONS[mime] ?? (mime.startsWith('audio') ? '🎵' : mime.startsWith('video') ? '🎬' : mime.startsWith('image') ? '🖼' : '📄')
}

function formatTime(ts: number | null) {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export function ArtifactPanel({ sessionId, artifacts }: Props) {
  if (artifacts.length === 0) return null

  return (
    <aside style={{
      width: 220, minWidth: 220, background: 'var(--bg2)', borderLeft: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{ padding: '14px 12px 10px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text2)', letterSpacing: '0.06em' }}>
          ARTIFACTS ({artifacts.length})
        </div>
      </div>
      <div style={{ overflowY: 'auto', flex: 1, padding: '8px 8px' }}>
        {artifacts.map(a => (
          <a
            key={a.filename}
            href={api.artifactDownloadUrl(sessionId, a.filename)}
            download={a.filename}
            style={artifactItem}
            title={a.filename}
          >
            <span style={{ fontSize: 18, flexShrink: 0 }}>{icon(a.mime_type)}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {a.filename}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 2 }}>
                {a.mime_type?.split('/')[1] ?? 'file'} · v{a.version} · {formatTime(a.create_time)}
              </div>
            </div>
            <span style={{ fontSize: 12, color: 'var(--text2)', flexShrink: 0 }}>↓</span>
          </a>
        ))}
      </div>
    </aside>
  )
}

const artifactItem: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 8px',
  borderRadius: 6, marginBottom: 4, textDecoration: 'none', color: 'var(--text)',
  border: '1px solid var(--border)', background: 'var(--bg3)', transition: 'border-color 0.15s',
}
