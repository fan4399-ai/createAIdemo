import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export interface Profile {
  name: string
  career: string
  expected_salary: string
  interest: string
  location: string
  raw: string
}

export type StreamEventType = 'connected' | 'stage' | 'log' | 'done' | 'error'

export interface StreamEvent {
  type: StreamEventType
  stage?: string
  status?: 'running' | 'done' | 'pending'
  message?: string
  markdown?: string
  session?: string
}

/** 获取用户画像（来自 knowledge/user_preference.txt） */
export async function getProfile(): Promise<Profile> {
  const { data } = await http.get<Profile>('/profile')
  return data
}

/** 启动一次报告生成，返回 session_id；topic/user_preference 为空时由后端回退默认 */
export async function startGeneration(
  topic?: string,
  userPreference?: string,
): Promise<string> {
  const { data } = await http.post<{ session_id: string }>('/generate', {
    topic: topic ?? null,
    user_preference: userPreference ?? null,
  })
  return data.session_id
}

/** 请求取消某个正在进行的生成 */
export async function cancelGeneration(session: string): Promise<void> {
  await http.post('/generate/cancel', null, { params: { session } })
}

/** 建立 SSE 连接，消费实时进度流 */
export function connectStream(
  session: string,
  onEvent: (e: StreamEvent) => void,
  onError: (err: Event) => void,
): EventSource {
  const es = new EventSource(`/api/generate/stream?session=${session}`)
  es.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data) as StreamEvent)
    } catch {
      /* 忽略无法解析的心跳/空帧 */
    }
  }
  es.onerror = (err) => {
    onError(err)
    es.close()
  }
  return es
}

/** 导出 Word（复用后端 export_utils） */
export async function exportWord(markdown: string, title = '报告'): Promise<void> {
  const { data } = await http.post('/export/word', { markdown, title }, { responseType: 'blob' })
  downloadBlob(data, `${title}.docx`)
}

/** 导出 Markdown（按 session 取最终报告） */
export async function exportMarkdown(session: string, title = 'report'): Promise<void> {
  const { data } = await http.get('/export/markdown', {
    params: { session },
    responseType: 'blob',
  })
  downloadBlob(data, `${title}.md`)
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
