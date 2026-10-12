export default function Wordmark({ size = 24, tone = 'ink' }: { size?: number; tone?: 'ink' | 'paper' }) {
  const slope = tone === 'paper' ? 'text-paper' : 'text-ink';
  const sense = tone === 'paper' ? 'text-saffron' : 'text-saffron-deep';
  return (
    <span
      className="inline-flex items-baseline font-serif leading-none"
      style={{ fontSize: size, letterSpacing: '-0.03em' }}
      aria-label="SlopeSense"
    >
      <span className={`font-semibold ${slope}`} aria-hidden="true">Slope</span>
      <span className={`font-normal italic ${sense}`} aria-hidden="true">Sense</span>
    </span>
  );
}
