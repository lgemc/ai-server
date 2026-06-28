// Simulates ChatPane.tsx message rendering to show the think/text separation bug

// --- Step 1: Simulate what arrives from the stream ---
const thinkingBuffer = `The user wants to know the capital of France. Let me think...
France is a country in Western Europe. Its capital city is Paris,
which has been the capital since the medieval period.`

const textBuffer = `The capital of France is **Paris**. It has been the capital city for centuries and is known for landmarks like the Eiffel Tower and the Louvre.`

// --- Step 2: How ChatPane.tsx combines them at stream end (lines 135-148) ---
function combineContent(thinking, text) {
  let combined = text
  if (thinking.trim()) {
    const wrapped = thinking.trim().startsWith('<think>')
      ? thinking.trim()
      : `<think>${thinking.trim()}</think>`
    combined = `${wrapped}\n\n${text}`
  }
  return combined
}

const combinedContent = combineContent(thinkingBuffer, textBuffer)

console.log('='.repeat(60))
console.log('COMBINED CONTENT (stored as msg.content):')
console.log('='.repeat(60))
console.log(combinedContent)
console.log()

// --- Step 3: The BROKEN regex from line 22 of ChatPane.tsx ---
// File has: /<think>([\s\S]*?)</think>/g
// In a JS regex literal, the `/` in `</think>` ENDS the pattern.
// The actual compiled regex is: /<think>([\s\S]*?)</
// (pattern ends at the second `/`, everything after is syntax noise)

console.log('='.repeat(60))
console.log('REGEX ANALYSIS:')
console.log('='.repeat(60))

const brokenRegex  = /<think>([\s\S]*?)</g      // what the file actually produces
const correctRegex = /<think>([\s\S]*?)<\/think>/g  // what was intended

console.log('Broken regex pattern :', brokenRegex.source)
console.log('Correct regex pattern:', correctRegex.source)
console.log()

// --- Step 4: Run parseContent() with the BROKEN regex ---
function parseContentBroken(text) {
  const parts = []
  const regex = /<think>([\s\S]*?)</g   // <-- the bug: stops at `<`, not `</think>`
  let last = 0
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push({ type: 'text', content: text.slice(last, match.index) })
    parts.push({ type: 'think', content: match[1] })
    last = match.index + match[0].length
    // prevent infinite loop on zero-width matches
    if (match.index === regex.lastIndex) regex.lastIndex++
  }
  const remaining = text.slice(last)
  const thinkStart = remaining.indexOf('<think>')
  if (thinkStart !== -1) {
    if (thinkStart > 0) parts.push({ type: 'text', content: remaining.slice(0, thinkStart) })
    parts.push({ type: 'think', content: remaining.slice(thinkStart + 7), partial: true })
  } else if (remaining) {
    parts.push({ type: 'text', content: remaining })
  }
  return parts
}

// --- Step 5: Run parseContent() with the CORRECT regex ---
function parseContentCorrect(text) {
  const parts = []
  const regex = /<think>([\s\S]*?)<\/think>/g   // <-- correct
  let last = 0
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push({ type: 'text', content: text.slice(last, match.index) })
    parts.push({ type: 'think', content: match[1] })
    last = match.index + match[0].length
  }
  const remaining = text.slice(last)
  const thinkStart = remaining.indexOf('<think>')
  if (thinkStart !== -1) {
    if (thinkStart > 0) parts.push({ type: 'text', content: remaining.slice(0, thinkStart) })
    parts.push({ type: 'think', content: remaining.slice(thinkStart + 7), partial: true })
  } else if (remaining) {
    parts.push({ type: 'text', content: remaining })
  }
  return parts
}

console.log('='.repeat(60))
console.log('parseContent() WITH BROKEN REGEX:')
console.log('='.repeat(60))
const brokenParts = parseContentBroken(combinedContent)
brokenParts.forEach((p, i) => {
  console.log(`  part[${i}] type=${p.type} partial=${!!p.partial}`)
  console.log(`           content="${p.content.slice(0, 80).replace(/\n/g, '\\n')}..."`)
})
console.log()

console.log('='.repeat(60))
console.log('parseContent() WITH CORRECT REGEX:')
console.log('='.repeat(60))
const correctParts = parseContentCorrect(combinedContent)
correctParts.forEach((p, i) => {
  console.log(`  part[${i}] type=${p.type} partial=${!!p.partial}`)
  console.log(`           content="${p.content.slice(0, 80).replace(/\n/g, '\\n')}..."`)
})
console.log()

// --- Step 6: Simulate what MarkdownContent renders ---
// After reorder: text parts first, then think parts
function simulateRender(parts, label) {
  const textParts = parts.filter(p => p.type === 'text')
  const thinkParts = parts.filter(p => p.type === 'think')
  const ordered = [...textParts, ...thinkParts]

  console.log(`=`.repeat(60))
  console.log(`RENDERED OUTPUT (${label}):`)
  console.log(`=`.repeat(60))
  ordered.forEach((p, i) => {
    if (p.type === 'think') {
      console.log(`  [<details> collapsible "💭 Thinking"]`)
      console.log(`    ${p.content.slice(0, 60).replace(/\n/g, '\\n')}...`)
      console.log(`  [</details>]`)
    } else {
      console.log(`  [<div class="md-content"> rendered as markdown]`)
      console.log(`    ${p.content.slice(0, 60).replace(/\n/g, '\\n')}...`)
      console.log(`  [</div>]`)
    }
  })
  console.log()
}

// --- Step 7: Simulate what ReactMarkdown does with unparsed <think> tags ---
// (the broken case: one big text part containing raw <think>...</think>)
function simulateReactMarkdown(text) {
  // ReactMarkdown with remarkGfm strips unknown HTML tags by default (no rehype-raw)
  // <think> and </think> are stripped, content remains as paragraphs
  const stripped = text
    .replace(/<think>/g, '')
    .replace(/<\/think>/g, '')
    .trim()
  return stripped
}

console.log('='.repeat(60))
console.log('WHAT USER ACTUALLY SEES (broken regex path):')
console.log('='.repeat(60))
if (brokenParts.length === 1 && brokenParts[0].type === 'text') {
  console.log('  >> parseContent returned a SINGLE text part (no separation!)')
  console.log('  >> ReactMarkdown strips <think> and </think> tags')
  console.log('  >> Result is thinking + text as plain paragraphs:')
  console.log()
  const rendered = simulateReactMarkdown(brokenParts[0].content)
  console.log(rendered)
  console.log()
  console.log('  So the user sees:')
  console.log('  [ thinking content as plain text ]')
  console.log('  <p />')
  console.log('  [ actual response ]')
  console.log()
  console.log('  NO collapsible <details> — just one block of text separated by a <p>')
} else {
  console.log('  >> Broken regex still produced multiple parts — investigate further')
  simulateRender(brokenParts, 'BROKEN')
}

simulateRender(correctParts, 'CORRECT (after fix)')

console.log('='.repeat(60))
console.log('THE FIX:')
console.log('='.repeat(60))
console.log('  In ChatPane.tsx line 22, change:')
console.log('    const regex = /<think>([\\s\\S]*?)</think>/g')
console.log('  to:')
console.log('    const regex = /<think>([\\s\\S]*?)<\\/think>/g')
console.log()
console.log('  The unescaped `/` in `</think>` terminates the regex literal early.')
console.log('  Pattern compiled was: /<think>([\\s\\S]*?)<!/ instead of the full closing tag.')
