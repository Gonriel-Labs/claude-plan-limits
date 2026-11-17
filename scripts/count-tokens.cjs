// Sums the tokens a session's transcript records, its subagents' included.
// Usage: node count-tokens.cjs <transcript.jsonl>  →  prints the total.
const fs = require('fs')
const path = require('path')

const transcript = process.argv[2]
const files = [transcript]
const subagents = path.join(transcript.replace(/\.jsonl$/, ''), 'subagents')
if (fs.existsSync(subagents)) {
  for (const name of fs.readdirSync(subagents)) {
    if (name.endsWith('.jsonl')) files.push(path.join(subagents, name))
  }
}

// A response is written as one line per content block, each repeating its
// usage, so each message id is counted once.
const seen = new Map()
for (const file of files) {
  if (!fs.existsSync(file)) continue
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    if (!line.includes('"usage"')) continue
    let row
    try {
      row = JSON.parse(line)
    } catch {
      continue
    }
    const message = row && row.message
    const usage = message && message.usage
    if (!usage) continue
    const total =
      (usage.input_tokens || 0) +
      (usage.output_tokens || 0) +
      (usage.cache_read_input_tokens || 0) +
      (usage.cache_creation_input_tokens || 0)
    seen.set(`${file}:${message.id || row.uuid}`, total)
  }
}

let sum = 0
for (const total of seen.values()) sum += total
process.stdout.write(String(sum))
