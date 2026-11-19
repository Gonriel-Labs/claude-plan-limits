export type Limit = { kind: string; percentUsed: number; resetsAt?: string }

declare module 'claude-code' {
  interface PluginState {
    'plan-limits': {
      limits: Limit[]
      tokens: number
      usd: number | null
      context: number | null
      isCompacting: boolean
      showClock: boolean
    }
  }
}
