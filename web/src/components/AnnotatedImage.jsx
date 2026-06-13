import Section from './Section.jsx'

// The "proof the AI is real" hero (PLAN §4.6): the server-annotated image with
// labelled detection boxes. Falls back to the original upload when the backend
// returned no boxes (e.g. EXIF-only, or the sample report which ships none).
export default function AnnotatedImage({ annotatedImage, fallbackUrl }) {
  const src = annotatedImage || fallbackUrl
  if (!src) return null
  return (
    <Section
      step="2"
      title="Annotated image"
      hint={annotatedImage ? 'boxes drawn server-side' : 'original (no detections to box)'}
    >
      <div className="overflow-hidden rounded-lg border border-line bg-black/40">
        <img src={src} alt="annotated" className="mx-auto max-h-[460px] w-auto" />
      </div>
    </Section>
  )
}
