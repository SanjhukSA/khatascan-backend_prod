import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getReceipt } from '../api/receipts.js'
import { apiBase } from '../api/client.js'

const CATEGORY_STYLES = {
  Groceries: { bg: '#eef2ff', color: '#6366f1' },
  Restaurant: { bg: '#ffe4e6', color: '#e11d48' },
  Utilities: { bg: '#f3e8ff', color: '#9333ea' },
  Transport: { bg: '#e0f2fe', color: '#0284c7' },
  Others: { bg: '#f1f5f9', color: '#64748b' },
}

function formatINR(val) {
  if (val === undefined || val === null) return '₹ 0.00'
  return (
    '₹ ' +
    Number(val).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  )
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

export default function ReceiptDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [receipt, setReceipt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getReceipt(id)
      .then(setReceipt)
      .catch((err) => {
        console.error(err)
        setError('Unable to load receipt details.')
      })
      .finally(() => setLoading(false))
  }, [id])

  const catStyle = receipt ? (CATEGORY_STYLES[receipt.category] || CATEGORY_STYLES.Others) : CATEGORY_STYLES.Others

  return (
    <div className="page-inner" style={{ padding: '16px 20px 24px' }}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate(-1)}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0f172a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 style={styles.headerTitle}>Receipt Details</h2>
        <div style={{ width: '38px' }} />
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div style={styles.errorBox}>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate(-1)} style={{ marginTop: '12px' }}>
            Go Back
          </button>
        </div>
      ) : receipt ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Receipt Image if available */}
          {receipt.image_url && (
            <div style={styles.imageCard}>
              <img
                src={`${apiBase}${receipt.image_url}`}
                alt="Receipt"
                style={styles.fullImage}
              />
            </div>
          )}

          {/* Overview Card */}
          <div style={styles.card}>
            <div style={styles.topRow}>
              <div>
                <span style={styles.metaLabel}>MERCHANT</span>
                <h3 style={styles.merchantName}>{receipt.vendor_name || 'Unknown Vendor'}</h3>
              </div>
              <span style={{ ...styles.categoryBadge, backgroundColor: catStyle.bg, color: catStyle.color }}>
                {receipt.category || 'Others'}
              </span>
            </div>

            <div style={styles.divider} />

            <div style={styles.detailRow}>
              <span style={styles.rowLabel}>Date</span>
              <span style={styles.rowValue}>{formatDate(receipt.date || receipt.created_at)}</span>
            </div>

            <div style={styles.detailRow}>
              <span style={styles.rowLabel}>Total Amount</span>
              <span style={styles.totalAmount}>{formatINR(receipt.total)}</span>
            </div>
          </div>

          {/* Line Items */}
          {receipt.items && receipt.items.length > 0 && (
            <div style={styles.card}>
              <h4 style={styles.sectionHeading}>Line Items</h4>
              <div style={styles.itemsList}>
                {receipt.items.map((item, idx) => (
                  <div key={item.id || idx} style={styles.itemRow}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={styles.itemName}>{item.name}</span>
                      {item.quantity > 1 && (
                        <span style={styles.itemQty}>Qty: {item.quantity}</span>
                      )}
                    </div>
                    <span style={styles.itemPrice}>
                      {formatINR(item.total_price || item.unit_price)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw OCR Text */}
          {receipt.raw_ocr_text && (
            <div style={styles.card}>
              <h4 style={styles.sectionHeading}>Raw OCR Text</h4>
              <pre style={styles.rawText}>{receipt.raw_ocr_text}</pre>
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}

const styles = {
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '20px',
  },
  backButton: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '6px',
    borderRadius: '10px',
    display: 'flex',
  },
  headerTitle: {
    fontSize: '20px',
    fontWeight: '800',
    color: '#0f172a',
  },
  errorBox: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '30px 20px',
    textAlign: 'center',
    color: '#64748b',
  },
  imageCard: {
    backgroundColor: '#0f172a',
    borderRadius: '20px',
    overflow: 'hidden',
    maxHeight: '260px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullImage: {
    width: '100%',
    maxHeight: '260px',
    objectFit: 'contain',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '22px 20px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.03)',
  },
  topRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  metaLabel: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.06em',
  },
  merchantName: {
    fontSize: '20px',
    fontWeight: '800',
    color: '#0f172a',
    marginTop: '2px',
  },
  categoryBadge: {
    fontSize: '12px',
    fontWeight: '600',
    padding: '4px 12px',
    borderRadius: '9999px',
  },
  divider: {
    height: '1px',
    backgroundColor: '#f1f5f9',
    margin: '16px 0',
  },
  detailRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  rowLabel: {
    fontSize: '14px',
    color: '#64748b',
  },
  rowValue: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#0f172a',
  },
  totalAmount: {
    fontSize: '20px',
    fontWeight: '800',
    color: '#0f172a',
  },
  sectionHeading: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '14px',
  },
  itemsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  itemRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0',
    borderBottom: '1px solid #f1f5f9',
  },
  itemName: {
    fontSize: '14px',
    fontWeight: '500',
    color: '#1e293b',
  },
  itemQty: {
    fontSize: '12px',
    color: '#94a3b8',
    marginTop: '2px',
  },
  itemPrice: {
    fontSize: '14.5px',
    fontWeight: '700',
    color: '#0f172a',
  },
  rawText: {
    backgroundColor: '#f8fafc',
    borderRadius: '12px',
    padding: '12px',
    fontSize: '12px',
    color: '#475569',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    fontFamily: 'monospace',
    maxHeight: '200px',
    overflowY: 'auto',
  },
}
