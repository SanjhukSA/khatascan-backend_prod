import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { listReceipts } from '../api/receipts.js'
import ReceiptRow from '../components/ReceiptRow.jsx'

export default function ReceiptsPage() {
  const navigate = useNavigate()
  const [receipts, setReceipts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetchReceipts = useCallback(async (p) => {
    setLoading(true)
    setError(null)
    try {
      const data = await listReceipts({ page: p, per_page: 10, sort_by: 'created_at', order: 'desc' })
      setReceipts(data.items || [])
      setTotalPages(data.pages || 1)
    } catch (err) {
      console.error(err)
      setError('Could not load receipts. Make sure the backend server is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReceipts(page)
  }, [page, fetchReceipts])

  return (
    <div className="page-inner" style={{ padding: '16px 20px 24px' }}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>All Receipts</h2>
          <p style={styles.subtitle}>View and manage all scanned expenses</p>
        </div>
        <button style={styles.scanBtn} onClick={() => navigate('/scan')}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>Scan</span>
        </button>
      </div>

      {error ? (
        <div style={styles.errorBox}>
          <p style={{ color: '#ef4444', fontSize: '14px', marginBottom: '12px' }}>{error}</p>
          <button className="btn btn-primary" onClick={() => fetchReceipts(page)}>
            Retry
          </button>
        </div>
      ) : loading ? (
        <div style={styles.list}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '14px', padding: '14px 0', borderBottom: '1px solid #f1f5f9' }}>
              <div className="skeleton" style={{ width: '54px', height: '66px', borderRadius: '12px' }} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="skeleton" style={{ width: '60%', height: '16px' }} />
                <div className="skeleton" style={{ width: '40%', height: '12px' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                <div className="skeleton" style={{ width: '60px', height: '16px' }} />
                <div className="skeleton" style={{ width: '64px', height: '20px', borderRadius: '9999px' }} />
              </div>
            </div>
          ))}
        </div>
      ) : receipts.length === 0 ? (
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>🧾</div>
          <h3 style={styles.emptyTitle}>No Receipts Found</h3>
          <p style={styles.emptySub}>
            Start scanning your receipts to build your expense history.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/scan')} style={{ marginTop: '16px' }}>
            Scan Your First Receipt
          </button>
        </div>
      ) : (
        <div style={styles.list}>
          {receipts.map((r) => (
            <ReceiptRow
              key={r.id}
              receipt={r}
              onClick={() => navigate(`/receipts/${r.id}`)}
            />
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={styles.paginationRow}>
              <button
                style={styles.pageBtn}
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span style={styles.pageIndicator}>
                Page {page} of {totalPages}
              </span>
              <button
                style={styles.pageBtn}
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const styles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    paddingTop: '6px',
  },
  title: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: '13px',
    color: '#94a3b8',
    marginTop: '2px',
  },
  scanBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#6366f1',
    color: '#ffffff',
    border: 'none',
    borderRadius: '12px',
    padding: '9px 16px',
    fontSize: '13.5px',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '10px 20px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.03)',
  },
  errorBox: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '32px 20px',
    textAlign: 'center',
  },
  emptyState: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '48px 24px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  emptyIcon: {
    fontSize: '44px',
    marginBottom: '12px',
  },
  emptyTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '6px',
  },
  emptySub: {
    fontSize: '13.5px',
    color: '#64748b',
    maxWidth: '240px',
    lineHeight: '1.5',
  },
  paginationRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 0 8px',
  },
  pageBtn: {
    backgroundColor: '#f1f5f9',
    color: '#0f172a',
    border: 'none',
    borderRadius: '10px',
    padding: '8px 14px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  pageIndicator: {
    fontSize: '13px',
    color: '#64748b',
    fontWeight: '500',
  },
}
