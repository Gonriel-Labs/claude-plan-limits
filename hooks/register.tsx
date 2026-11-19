import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Limit } from '../types'

const limits = atom({ plugin: 'plan-limits', key: 'limits' } as const, [] as Limit[])
// Every token the session's turns reported, subagents and cache included.
const tokens = atom({ plugin: 'plan-limits', key: 'tokens' } as const, 0)
const usd = atom({ plugin: 'plan-limits', key: 'usd' } as const, null as number | null)
// The live context window's fill, and whether a compaction asked from the
// warning is pending (it hides the warning until the fill drops).
const context = atom({ plugin: 'plan-limits', key: 'context' } as const, null as number | null)
const isCompacting = atom({ plugin: 'plan-limits', key: 'isCompacting' } as const, false)

const COMPACT_AT = 300_000

const LABELS: Record<string, string> = {
  five_hour: '5h',
  seven_day: 'Semanal',
  spend_limit: 'Gasto',
}

const SEGMENTS = 5

// The concept palette: coral, amber past 70 %, red past 90 %, gray for what is left.
const EMPTY_COLOR = '#888780'
const WARNING_COLOR = '#EF9F27'
const DIVIDER_COLOR = '#3A3A38'

function colorFor(percent: number) {
  if (percent >= 90) return '#E24B4A'
  if (percent >= 70) return WARNING_COLOR
  return '#D85A30'
}

function resetText(resetsAt: string | undefined, now: number) {
  if (!resetsAt) return ''
  const ms = Date.parse(resetsAt) - now
  if (!Number.isFinite(ms) || ms <= 0) return ''
  const minutes = Math.round(ms / 60000)
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

function tokenText(count: number) {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}k`
  return `${count}`
}

// Rate limits are the account's, not the session's: the last ones seen are
// kept across sessions so the band shows them before this session's first call.
// A chat reopened reports the reading it last saw, which may be older than one
// another chat saved since, so readings are merged per window, newest kept.
function newer(a: Limit, b: Limit) {
  const resetA = a.resetsAt ? Date.parse(a.resetsAt) : 0
  const resetB = b.resetsAt ? Date.parse(b.resetsAt) : 0
  // A later reset is a later window; in the same window usage only grows.
  if (resetA !== resetB) return resetA > resetB ? a : b
  return a.percentUsed >= b.percentUsed ? a : b
}

function merge(...readings: Limit[][]) {
  const byKind = new Map<string, Limit>()
  for (const reading of readings) {
    for (const limit of reading) {
      const seen = byKind.get(limit.kind)
      byKind.set(limit.kind, seen ? newer(seen, limit) : limit)
    }
  }
  const order = ['five_hour', 'seven_day']
  return [...byKind.values()].sort(
    (a, b) => (order.indexOf(a.kind) + 1 || 99) - (order.indexOf(b.kind) + 1 || 99),
  )
}

async function setLimits($: EngineInterface, reported: Limit[]) {
  const kept = await $.store.get('limits')
  const merged = merge(Array.isArray(kept) ? (kept as Limit[]) : [], await read($, limits), reported)
  if (merged.length === 0) return
  await update($, limits, () => merged)
  if (JSON.stringify(merged) !== JSON.stringify(kept)) await $.store.set('limits', merged)
}

async function setContext($: EngineInterface, fill: number | undefined) {
  if (fill === undefined) return
  await update($, context, () => fill)
  if (fill < COMPACT_AT) await update($, isCompacting, () => false)
}

// The transcript is the one record of the whole session, from before this
// module loaded too: recount it whenever a prompt starts or an answer ends.
async function recount($: EngineInterface, transcript: string) {
  if (!transcript) return
  const script = `${$.plugin.root}/scripts/count-tokens.cjs`
  const { exitCode, stdout } = await $.process.run(['node', script, transcript])
  const counted = Number(stdout.trim())
  if (exitCode === 0 && Number.isFinite(counted)) {
    await update($, tokens, () => counted)
  }
  const usage = await $.session.usage()
  await update($, usd, () => usage.cost?.usd ?? null)
  await setContext($, usage.context.tokens)
}

// Runs /compact itself, as if typed: queued while an answer is running and
// run once the session is idle, instead of refused as a direct compaction is.
async function compact($: EngineInterface) {
  await update($, isCompacting, () => true)
  try {
    await $.command.run({ command: 'compact' })
    const usage = await $.session.usage()
    await setContext($, usage.context.tokens)
  } catch (error) {
    await update($, isCompacting, () => false)
    const reason = error instanceof Error ? error.message : String(error)
    $.ui.log(`compact failed: ${reason}`, { to: 'debug' })
    $.ui.toast(`No se pudo compactar: ${reason}`)
  }
}

// The band reads the clock only when it is drawn, and nothing redraws it while
// the chat sits idle: every minute, take in what other chats saved and redraw,
// so the countdown runs, a reset window drops to 0 % and every chat agrees.
const REDRAW_MS = 60_000
let redraw: { cancel: () => void } | undefined

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const result = await next(e)
    redraw?.cancel()
    redraw = $.clock.every(REDRAW_MS, () => {
      void setLimits($, [])
        .catch(() => undefined)
        .then(() => $.ui.invalidate('ui.render'))
    })
    const usage = await $.session.usage()
    await setLimits($, usage.rateLimits)
    await update($, usd, () => usage.cost?.usd ?? null)
    await setContext($, usage.context.tokens)
    // Opening an existing chat: count its transcript now, not at the next prompt.
    void $.session
      .id()
      .then(id => recount($, id))
      .catch(() => undefined)
    return result
  })

  on('session.measure', async ($, e, next) => {
    await setLimits($, e.rateLimits)
    await update($, usd, () => e.cost?.usd ?? null)
    await setContext($, e.context.tokens)
    return next(e)
  })

  on('classic.UserPromptSubmit', async ($, e, next) => {
    const result = await next(e)
    void recount($, e.transcript_path).catch(() => undefined)
    return result
  })

  on('classic.Stop', async ($, e, next) => {
    const result = await next(e)
    void recount($, e.transcript_path).catch(() => undefined)
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const current = await read($, limits)
    const total = await read($, tokens)
    const dollars = await read($, usd)
    if (e.props.hasSurvey || (current.length === 0 && total === 0 && dollars === null)) {
      return next(e)
    }

    const { Box, Button, Text } = $.ui.resolve(e)
    const now = await $.clock.now()
    const fill = await read($, context)
    const showWarning = fill !== null && fill >= COMPACT_AT && !(await read($, isCompacting))

    const usageRow = (
      <Box flexDirection="row">
        <Box flexDirection="row" flexGrow={1}>
          {current.map((limit, i) => {
            // A window whose reset time has passed starts over at zero: the
            // saved reading may predate it, so trust the reset over the figure.
            const isReset = limit.resetsAt !== undefined && Date.parse(limit.resetsAt) <= now
            const used = isReset ? 0 : limit.percentUsed
            const percent = Math.max(0, Math.min(100, used))
            const filled = Math.round((percent / 100) * SEGMENTS)
            const color = colorFor(used)
            const reset = resetText(limit.resetsAt, now)
            return (
              <Text key={limit.kind}>
                {i > 0 ? <Text color={EMPTY_COLOR}>{'   │   '}</Text> : ''}
                <Text dimColor>{LABELS[limit.kind] ?? limit.kind}  </Text>
                <Text color={color}>{'■'.repeat(filled)}</Text>
                <Text color={EMPTY_COLOR}>{'□'.repeat(SEGMENTS - filled)}  </Text>
                <Text color={color} bold>{`${Math.round(used)}%`}</Text>
                {reset ? <Text dimColor>{`  ↻ ${reset}`}</Text> : ''}
              </Text>
            )
          })}
        </Box>
        <Text>
          <Text dimColor>{`${tokenText(total)} tokens`}</Text>
          {dollars !== null ? (
            <Text>
              <Text color={EMPTY_COLOR}>{'  ·  '}</Text>
              <Text bold>{`$${dollars.toFixed(2)}`}</Text>
            </Text>
          ) : (
            ''
          )}
        </Text>
      </Box>
    )

    if (!showWarning) {
      return usageRow
    }

    return (
      <Box flexDirection="column">
        {usageRow}
        {/* A rule of box-drawing dashes in the smallest type, clipped to one
            line so it spans the band without wrapping or an ellipsis. */}
        <Box height={1} overflow="hidden">
          <Text size="caption" color={DIVIDER_COLOR} wrap="wrap">
            {'─'.repeat(400)}
          </Text>
        </Box>
        <Box flexDirection="row" alignItems="center" gap={2}>
          <Box flexGrow={1} flexShrink={1}>
            <Text wrap="truncate-end">
              <Text color={WARNING_COLOR}>▲  </Text>
              <Text dimColor>
                {`El contexto va en ${tokenText(fill)}. Compactar lo resume y abarata las respuestas.`}
              </Text>
            </Text>
          </Box>
          {/* The app's own button alone: its slightly rounded rectangle is the
              shape and size its hover highlight draws, with no frame around it. */}
          <Box flexShrink={0}>
            <Button key="compact" dimColor onPress={() => void compact($)}>
              <Text size="footnote">Compactar</Text>
            </Button>
          </Box>
        </Box>
      </Box>
    )
  })
}
