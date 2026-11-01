import React from 'react'
import { useNavigate } from 'react-router-dom'
import ReceiptRow from './ReceiptRow.jsx'

const MOCK_RECEIPTS = [
  {
    id: 'mock-1',
    vendor_name: 'Super Mart',
    date: '12 Sep 2026',
    total: 320.0,
    category: 'Groceries',
    items: [
      { name: 'Rice', total_price: 160.0 },
      { name: 'Oil', total_price: 120.0 },
      { name: 'Biscuits', total_price: 40.0 },
    ],
  },
  {
    id: 'mock-2',
    vendor_name: 'Spice Hub Restaurant',
    date: '11 Sep 2026',
    total: 450.0,
    category: 'Restaurant',
    items: [
      { name: 'Chicken Biryani', total_price: 320.0 },
      { name: 'Cold Drink', total_price: 130.0 },
    ],
  },
  {
    id: 'mock-3',
    vendor_name: 'HP Petrol Pump',
    date: '10 Sep 2026',
    total: 2000.0,
    category: 'Transport',
    items: [
      { name: 'Petrol Unleaded', total_price: 2000.0 },
    ],
  },
]

export default function RecentReceipts({ receipts = [], loading = false }) {
  const navigate = useNavigate()

  const displayReceipts = receipts && receipts.length > 0 ? receipts : MOCK_RECEIPTS

  return (
    <div style={styles.card}>
      {/* Header Row */}
      <div style={styles.headerRow}>
        <div>
          <h3 style={styles.title}>Recent Receipts</h3>
          <p style={styles.subtitle}>Tap to inspect full breakdown</p>
        </div>
        <button style={styles.seeAllBtn} onClick={() => navigate('/receipts')}>
          See all
        </button>
      </div>

      {/* Receipts List */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', padding: '8px 0' }}>
          {[1, 2, 3].map((i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div className="skeleton" style={{ width: '48px', height: '60px', borderRadius: '10px' }} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div className="skeleton" style={{ width: '60%', height: '14px' }} />
                <div className="skeleton" style={{ width: '35%', height: '11px' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                <div className="skeleton" style={{ width: '55px', height: '14px' }} />
                <div className="skeleton" style={{ width: '60px', height: '18px', borderRadius: '9999px' }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={styles.list}>
          {displayReceipts.slice(0, 5).map((r) => (
            <ReceiptRow
              key={r.id}
              receipt={r}
              onClick={() => {
                if (r.id.startsWith('mock')) {
                  navigate('/receipts')
                } else {
                  navigate(`/receipts/${r.id}`)
                }
              }}
            />
          ))}
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
    marginBottom: '6px',
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
  seeAllBtn: {
    background: 'none',
    border: 'none',
    color: '#6366f1',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    padding: '2px 0',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
  },
}
