const API = 'http://localhost:8000'

export interface ImportResult {
  imported: number
  skipped: number
  errors: string[]
}

export interface PlayerStats {
  player: string
  hands: number
  vpip: number
  pfr: number
  bb_per_100: number
  bb_per_100_adjusted: number
}

export interface HandSummary {
  hand_id: string
  played_at: string
  table_name: string
  game_type: string
  small_blind: number
  big_blind: number
  hero_name: string | null
}

export interface HandsResponse {
  player: string
  total: number
  page: number
  page_size: number
  hands: HandSummary[]
}

export async function importFiles(files: File[]): Promise<ImportResult> {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  const resp = await fetch(`${API}/import`, { method: 'POST', body: form })
  return resp.json()
}

export async function fetchStats(player: string): Promise<PlayerStats> {
  const resp = await fetch(`${API}/${player}/stats`)
  return resp.json()
}

export async function fetchHands(player: string, page: number, pageSize: number): Promise<HandsResponse> {
  const resp = await fetch(`${API}/${player}/hands?page=${page}&page_size=${pageSize}`)
  return resp.json()
}
