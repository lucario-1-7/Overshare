import Section from './Section.jsx'

// Optional plain-English summary from the local LLM (PLAN §4.11). Purely additive —
// if the backend shipped a report without one, this section simply doesn't render.
export default function Explanation({ text }) {
  if (!text) return null
  return (
    <Section step="8" title="In plain English" hint="local LLM · optional">
      <p className="text-sm leading-relaxed text-fg/90">{text}</p>
    </Section>
  )
}
