import React from 'react'
import { useNavigate } from 'react-router-dom'

/* Receipt illustration with scanning corner brackets */
function ReceiptIllustration() {
  return (
    <div style={styles.illustrationWrapper}>
      {/* 4 Corner Bracket Markers */}
      <div style={{ ...styles.bracket, top: 0, left: 0, borderRight: 'none', borderBottom: 'none' }} />
      <div style={{ ...styles.bracket, top: 0, right: 0, borderLeft: 'none', borderBottom: 'none' }} />
      <div style={{ ...styles.bracket, bottom: 0, left: 0, borderRight: 'none', borderTop: 'none' }} />
      <div style={{ ...styles.bracket, bottom: 0, right: 0, borderLeft: 'none', borderTop: 'none' }} />

      {/* Receipt preview */}
      <div style={styles.receiptPaper}>
        <div style={styles.receiptHeader}>
          <div style={styles.storeName}>CORNER MARKET</div>
          <div style={styles.receiptDate}>01 NOV 2026 · 10:42</div>
        </div>

        <div className="receipt-scan-beam" aria-hidden="true">
          <div className="receipt-scan-line" />
        </div>

        <div style={styles.receiptItems}>
          <div style={styles.receiptRow}>
            <span>Rice · 1 kg</span>
            <span>160.00</span>
          </div>
          <div style={styles.receiptRow}>
            <span>Cooking oil</span>
            <span>120.00</span>
          </div>
          <div style={styles.receiptRow}>
            <span>Biscuits</span>
            <span>40.00</span>
          </div>
        </div>

        <div style={styles.receiptDivider} />
        <div style={styles.receiptTotal}>
          <span>PAID</span>
          <span>₹320.00</span>
        </div>
      </div>
    </div>
  )
}

export default function ScanReceiptCard({ onScan }) {
  const navigate = useNavigate()

  const handleScanClick = () => {
    if (onScan) {
      onScan()
    } else {
      navigate('/scan')
    }
  }

  return (
    <div style={styles.card}>
      {/* Ambient background glow */}
      <div style={styles.ambientGlow} />

      {/* Left Column Content */}
      <div style={styles.leftContent}>
        <h2 style={styles.title}>Scan Receipt</h2>
        <p style={styles.description}>
          Keep every item, tax, and total organized.
        </p>
        <button style={styles.scanButton} onClick={handleScanClick}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
            <circle cx="12" cy="13" r="4" />
          </svg>
          <span>Scan Receipt Now</span>
        </button>
      </div>

      {/* Right Column Illustration */}
      <div style={styles.rightContent}>
        <ReceiptIllustration />
      </div>
    </div>
  )
}

const styles = {
  card: {
    backgroundColor: '#12142d',
    backgroundImage: 'radial-gradient(circle at 85% 50%, rgba(99, 102, 241, 0.25) 0%, rgba(18, 20, 45, 0) 70%)',
    borderRadius: '20px',
    padding: '18px 16px',
    marginBottom: '14px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    position: 'relative',
    overflow: 'hidden',
    boxShadow: '0 6px 20px rgba(18, 20, 45, 0.12)',
    boxSizing: 'border-box',
    width: '100%',
  },
  ambientGlow: {
    position: 'absolute',
    right: '30px',
    top: '30%',
    width: '120px',
    height: '120px',
    borderRadius: '50%',
    background: 'radial-gradient(circle, rgba(99, 102, 241, 0.28) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  leftContent: {
    flex: 1,
    paddingRight: '8px',
    zIndex: 2,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    minWidth: 0,
  },
  title: {
    color: '#ffffff',
    fontSize: '20px',
    fontWeight: '700',
    letterSpacing: '-0.3px',
    marginBottom: '6px',
  },
  description: {
    color: '#94a3b8',
    fontSize: '12px',
    lineHeight: '1.45',
    marginBottom: '14px',
    maxWidth: '175px',
  },
  scanButton: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#4f46e5',
    backgroundImage: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
    color: '#ffffff',
    border: 'none',
    borderRadius: '12px',
    padding: '9px 13px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(79, 70, 229, 0.45)',
    whiteSpace: 'nowrap',
  },
  rightContent: {
    flexShrink: 0,
    zIndex: 2,
  },
  illustrationWrapper: {
    position: 'relative',
    padding: '8px',
    width: '110px',
    boxSizing: 'border-box',
  },
  bracket: {
    position: 'absolute',
    width: '14px',
    height: '14px',
    borderColor: '#6366f1',
    borderStyle: 'solid',
    borderWidth: '2.5px',
    borderRadius: '2.5px',
  },
  receiptPaper: {
    backgroundColor: '#fffefa',
    borderRadius: '8px',
    padding: '9px 8px 8px',
    width: '94px',
    boxSizing: 'border-box',
    boxShadow: '0 7px 16px rgba(0, 0, 0, 0.24)',
    position: 'relative',
    overflow: 'hidden',
  },
  receiptHeader: {
    textAlign: 'center',
    marginBottom: '5px',
  },
  storeName: {
    fontSize: '8px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '0.04em',
  },
  receiptDate: {
    fontSize: '6.5px',
    color: '#94a3b8',
    marginTop: '1px',
  },
  receiptItems: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2.5px',
    marginBottom: '5px',
  },
  receiptRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '3px',
    fontSize: '6.4px',
    fontWeight: '400',
    color: '#475569',
    fontFamily: 'monospace, -apple-system, sans-serif',
    whiteSpace: 'nowrap',
  },
  receiptDivider: {
    height: '1px',
    backgroundColor: '#0f172a',
    marginBottom: '3px',
    opacity: 0.75,
  },
  receiptTotal: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '7px',
    fontWeight: '700',
    color: '#0f172a',
    letterSpacing: '0.02em',
  },
}
