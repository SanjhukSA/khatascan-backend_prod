import React from 'react'

const CATEGORY_CONFIG = {
  Groceries: { color: '#4f46e5', label: 'Groceries' },
  Restaurant: { color: '#f43f5e', label: 'Restaurant' },
  Utilities: { color: '#a855f7', label: 'Utilities' },
  Transport: { color: '#06b6d4', label: 'Transport' },
  Others: { color: '#64748b', label: 'Others' },
  Other: { color: '#64748b', label: 'Others' },
}

const DEFAULT_CATEGORIES = [
  { category: 'Groceries', total: 4320, percentage: 35 },
  { category: 'Restaurant', total: 2240, percentage: 18 },
  { category: 'Utilities', total: 1870, percentage: 15 },
  { category: 'Transport', total: 1490, percentage: 12 },
  { category: 'Others', total: 2530, percentage: 20 },
]

function formatINR(val) {
  if (val === null || val === undefined) return '₹0'
  return '₹' + Math.round(val).toLocaleString('en-IN')
}

/* Precision SVG Doughnut Chart */
function DoughnutChart({ data, total }) {
  const size = 120
  const strokeWidth = 18
  const radius = (size - strokeWidth) / 2
  const center = size / 2
  const circumference = 2 * Math.PI * radius

  let accumulatedPct = 0

  return (
    <div style={styles.chartContainer}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        {data.map((item, index) => {
          const pct = (item.percentage || 0) / 100
          const strokeDash = pct * circumference
          const color = (CATEGORY_CONFIG[item.category] || CATEGORY_CONFIG.Others).color
          const offset = - accumulatedPct * circumference
          accumulatedPct += pct

          return (
            <circle
              key={item.category || index}
              cx={center}
              cy={center}
              r={radius}
              fill="transparent"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${strokeDash} ${circumference - strokeDash}`}
              strokeDashoffset={offset}
              strokeLinecap="butt"
            />
          )
        })}
      </svg>

      {/* Centered Total Label */}
      <div style={styles.centerBadge}>
        <span style={styles.centerSub}>TOTAL</span>
        <span style={styles.centerTotal}>{formatINR(total)}</span>
      </div>
    </div>
  )
}

export default function MoneyGoesCard({ data, loading = false }) {
  const categories = (data && data.length > 0) ? data : DEFAULT_CATEGORIES
  const totalSpend = categories.reduce((sum, item) => sum + (item.total || 0), 0)

  return (
    <div style={styles.card}>
      {/* Title & Badge Header */}
      <div style={styles.headerRow}>
        <div>
          <h3 style={styles.title}>Where Your Money Goes</h3>
          <p style={styles.subtitle}>Category spending distribution</p>
        </div>
        <span style={styles.badge}>This Month</span>
      </div>

      {loading ? (
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', padding: '12px 0' }}>
          <div className="skeleton" style={{ width: '120px', height: '120px', borderRadius: '50%' }} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton" style={{ width: '100%', height: '14px' }} />
            ))}
          </div>
        </div>
      ) : (
        /* Side-by-side: Donut Chart on Left, Legend List on Right */
        <div style={styles.contentRow}>
          {/* Doughnut Chart */}
          <div style={styles.chartCol}>
            <DoughnutChart data={categories} total={totalSpend} />
          </div>

          {/* Category List */}
          <div style={styles.legendCol}>
            {categories.map((item) => {
              const cfg = CATEGORY_CONFIG[item.category] || CATEGORY_CONFIG.Others
              return (
                <div key={item.category} style={styles.legendRow}>
                  {/* Category dot and name */}
                  <div style={styles.catLeft}>
                    <div style={{ ...styles.colorDot, backgroundColor: cfg.color }} />
                    <span style={styles.catName}>{cfg.label}</span>
                  </div>

                  {/* Category amount and percentage */}
                  <div style={styles.catRight}>
                    <span style={styles.catAmount}>{formatINR(item.total)}</span>
                    <span style={styles.catPercent}>{Math.round(item.percentage)}%</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

const styles = {
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '20px',
    padding: '18px 16px',
    marginBottom: '14px',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.02)',
    boxSizing: 'border-box',
    width: '100%',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '16px',
  },
  title: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#0f172a',
    letterSpacing: '-0.3px',
    marginBottom: '2px',
  },
  subtitle: {
    fontSize: '12.5px',
    color: '#64748b',
  },
  badge: {
    backgroundColor: '#eef2ff',
    color: '#6366f1',
    fontSize: '12px',
    fontWeight: '600',
    padding: '5px 12px',
    borderRadius: '9999px',
    whiteSpace: 'nowrap',
  },
  contentRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
  },
  chartCol: {
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  chartContainer: {
    position: 'relative',
    width: '120px',
    height: '120px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  centerBadge: {
    position: 'absolute',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    pointerEvents: 'none',
  },
  centerSub: {
    fontSize: '10px',
    fontWeight: '600',
    letterSpacing: '0.06em',
    color: '#94a3b8',
    marginBottom: '1px',
  },
  centerTotal: {
    fontSize: '15.5px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.3px',
  },
  legendCol: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '9px',
    minWidth: 0,
  },
  legendRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  catLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  colorDot: {
    width: '9px',
    height: '9px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  catName: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#1e293b',
  },
  catRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  catAmount: {
    fontSize: '13.5px',
    fontWeight: '700',
    color: '#0f172a',
  },
  catPercent: {
    fontSize: '11.5px',
    fontWeight: '500',
    color: '#94a3b8',
    minWidth: '26px',
    textAlign: 'right',
  },
}
