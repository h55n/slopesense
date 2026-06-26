export default function Loading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center bg-slope-bg">
      <div className="text-center">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-white/80" />
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/40">Loading</p>
      </div>
    </div>
  );
}
