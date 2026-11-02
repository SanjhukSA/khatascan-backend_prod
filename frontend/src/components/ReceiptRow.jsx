import React from 'react'
import { apiBase } from '../api/client.js'

const CATEGORY_STYLES = {
  Groceries: { bg: '#eef2ff', color: '#6366f1' },
  Restaurant: { bg: '#ffe4e6', color: '#e11d48' },
  Utilities: { bg: '#f3e8ff', color: '#9333ea' },
  Transport: { bg: '#e0f2fe', color: '#0284c7' },
  Others: { bg: '#f1f5f9', color: '#64748b' },
  Other: { bg: '#f1f5f9', color: '#64748b' },
}

function formatAmount(amount) {
  if (amount === undefined || amount === null) return '₹ 0.00'
  return (
    '₹ ' +
    Number(amount).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  )
}

function formatDate(dateStr) {
  if (!dateStr) return '12 Sep 2026'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

/* Styled miniature receipt thumbnail */
function ReceiptThumbnail({ vendor, total, category, imgUrl }) {
  if (imgUrl) {
    return (
      <div style={styles.thumbnailWrapper}>
        <img
          src={`${apiBase}${imgUrl}`}
          alt={vendor}
          style={styles.thumbnailImg}
          onError={(e) => {
            e.target.style.display = 'none'
          }}
        />
      </div>
    )
  }

  const isRestaurant = category === 'Restaurant' || vendor?.toLowerCase().includes('spice')
  const isTransport = category === 'Transport' || vendor?.toLowerCase().includes('petrol')
  
  const bg = isTransport ? '#f0f9ff' : isRestaurant ? '#fff7ed' : '#fefce8'
  const border = isTransport ? '#e0f2fe' : isRestaurant ? '#ffedd5' : '#fef08a'

  const shortName = vendor ? vendor.split(' ').slice(0, 2).join('\n').toUpperCase() : 'RECEIPT'

  return (
    <div style={{ ...styles.thumbnailBox, backgroundColor: bg, borderColor: border }}>
      <div style={styles.miniHeader}>{shortName}</div>
      <div style={styles.miniLines}>
        <div style={styles.miniLine} />
        <div style={{ ...styles.miniLine, width: '65%' }} />
      </div>
      <div style={styles.miniTotal}>₹{Math.round(total || 0)}</div>
    </div>
  )
}

export default function ReceiptRow({ receipt, onClick }) {
  const catStyle = CATEGORY_STYLES[receipt.category] || CATEGORY_STYLES.Others

  return (
    <div style={styles.row} onClick={onClick}>
      {/* Left Column: Mini Receipt Paper Graphic / Thumbnail */}
      <ReceiptThumbnail
        vendor={receipt.vendor_name}
        total={receipt.total}
        category={receipt.category}
        imgUrl={receipt.thumbnail_url}
      />

      {/* Middle Column: Vendor Name & Date */}
      <div style={styles.middleCol}>
        <h4 style={styles.vendorName}>{receipt.vendor_name || 'Receipt'}</h4>
        <span style={styles.dateText}>{formatDate(receipt.date || receipt.created_at)}</span>
      </div>

      {/* Right Column: Amount (top) & Category Pill (bottom) */}
      <div style={styles.rightCol}>
        <span style={styles.amountText}>{formatAmount(receipt.total)}</span>
        {receipt.category && (
          <span style={{ ...styles.categoryPill, backgroundColor: catStyle.bg, color: catStyle.color }}>
            {receipt.category}
          </span>
        )}
      </div>
    </div>
  )
}

const styles = {
  row: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 0',
    borderBottom: '1px solid #f1f5f9',
    cursor: 'pointer',
    userSelect: 'none',
  },
  thumbnailWrapper: {
    width: '48px',
    height: '60px',
    borderRadius: '10px',
    overflow: 'hidden',
    flexShrink: 0,
    marginRight: '12px',
    boxShadow: '0 2px 6px rgba(0,0,0,0.04)',
  },
  thumbnailImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  thumbnailBox: {
    width: '48px',
    height: '60px',
    borderRadius: '10px',
    border: '1.2px solid',
    padding: '6px 4px',
    boxSizing: 'border-box',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexShrink: 0,
    marginRight: '12px',
    boxShadow: '0 2px 6px rgba(0, 0, 0, 0.03)',
  },
  miniHeader: {
    fontSize: '6px',
    fontWeight: '800',
    color: '#0f172a',
    textAlign: 'center',
    lineHeight: '1.1',
    letterSpacing: '0.04em',
    whiteSpace: 'pre-line',
  },
  miniLines: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    alignItems: 'center',
  },
  miniLine: {
    width: '90%',
    height: '1.5px',
    backgroundColor: '#cbd5e1',
    borderRadius: '1px',
    opacity: 0.8,
  },
  miniTotal: {
    fontSize: '7px',
    fontWeight: '800',
    color: '#0f172a',
  },
  middleCol: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
  },
  vendorName: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#0f172a',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    letterSpacing: '-0.2px',
  },
  dateText: {
    fontSize: '12px',
    fontWeight: '400',
    color: '#94a3b8',
  },
  rightCol: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '4px',
    flexShrink: 0,
  },
  amountText: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#0f172a',
    letterSpacing: '-0.2px',
  },
  categoryPill: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '2.5px 10px',
    borderRadius: '9999px',
    display: 'inline-block',
  },
}
