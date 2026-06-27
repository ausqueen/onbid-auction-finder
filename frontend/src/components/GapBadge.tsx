interface GapBadgeProps {
  gapPct: number | null
  size?: 'sm' | 'md' | 'lg'
  hasDeposit?: boolean
}

export default function GapBadge({ gapPct, size = 'md', hasDeposit = false }: GapBadgeProps) {
  if (gapPct == null) return null

  const sizeClass = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
    lg: 'text-base px-3 py-1.5 font-bold',
  }[size]

  let colorClass = 'bg-gray-100 text-gray-600'
  if (gapPct >= 40) colorClass = 'bg-red-100 text-red-700'
  else if (gapPct >= 25) colorClass = 'bg-orange-100 text-orange-700'
  else if (gapPct >= 15) colorClass = 'bg-yellow-100 text-yellow-700'
  else if (gapPct > 0) colorClass = 'bg-green-100 text-green-700'

  return (
    <span className={`inline-flex items-center rounded-full font-semibold ${sizeClass} ${colorClass}`}>
      {hasDeposit && <span className="mr-1 text-[0.85em] opacity-90">인수포함</span>}
      ↓{gapPct.toFixed(1)}%
    </span>
  )
}
