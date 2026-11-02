import React from 'react'

function formatINR(val) {
  if (val === null || val === undefined) return '₹ 0'
  return '₹ ' + Math.round(val).toLocaleString('en-IN')
}

export default function TotalExpensesCard({ total = 12450, loading = false }) {
  const effectiveTotal = total || 0

  if (loading) {
    return (
      <div style={styles.card}>
        <div style={styles.amountBlock}>
          <div className="skeleton" style={{ width: '90px', height: '12px', marginBottom: '8px' }} />
          <div className="skeleton" style={{ width: '130px', height: '30px' }} />
        </div>
      </div>
    )
  }

  return (
    <div style={styles.card}>
      <div style={styles.amountBlock}>
        <span style={styles.label}>TOTAL EXPENSES</span>
        <div style={styles.amount}>{formatINR(effectiveTotal)}</div>
      </div>
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
  amountBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
  },
  label: {
    fontSize: '11.5px',
    fontWeight: '600',
    color: '#64748b',
    letterSpacing: '0.06em',
  },
  amount: {
    fontSize: '28px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.7px',
    lineHeight: '1.1',
  },
}
