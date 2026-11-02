import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadReceipt, processReceipt, saveReceipt } from '../api/receipts.js'

const CATEGORIES = ['Groceries', 'Restaurant', 'Utilities', 'Transport', 'Others']

export default function ScanPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)

  const [step, setStep] = useState('idle') // 'idle' | 'uploading' | 'processing' | 'review' | 'saving' | 'done'
  const [uploadProgress, setUploadProgress] = useState(0)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [uploadId, setUploadId] = useState(null)
  const [error, setError] = useState(null)

  // Review form state
  const [vendorName, setVendorName] = useState('')
  const [receiptDate, setReceiptDate] = useState('')
  const [totalAmount, setTotalAmount] = useState('')
  const [category, setCategory] = useState('Groceries')
  const [items, setItems] = useState([])
  const [rawOcrText, setRawOcrText] = useState('')

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setPreviewUrl(URL.createObjectURL(file))
    startUploadAndOcr(file)
  }

  const startUploadAndOcr = async (file) => {
    setError(null)
    setStep('uploading')
    setUploadProgress(0)

    try {
      // Step 1: Upload
      const uploadRes = await uploadReceipt(file, (pct) => setUploadProgress(pct))
      const uid = uploadRes.upload_id
      setUploadId(uid)

      // Step 2: OCR Extraction
      setStep('processing')
      const ocrRes = await processReceipt(uid)

      if (ocrRes.is_receipt === false) {
        setError(ocrRes.rejection_reason || 'The image does not appear to be a receipt.')
        setStep('idle')
        return
      }

      setVendorName(ocrRes.vendor_name || 'Super Mart')
      setReceiptDate(ocrRes.date || new Date().toISOString().split('T')[0])
      setTotalAmount(ocrRes.total != null ? String(ocrRes.total) : '0')
      setCategory(ocrRes.category || 'Groceries')
      setItems(ocrRes.items || [])
      setRawOcrText(ocrRes.raw_ocr_text || '')

      setStep('review')
    } catch (err) {
      console.error(err)
      setError(err?.response?.data?.detail || 'Failed to process receipt image. Please try another photo.')
      setStep('idle')
    }
  }

  const handleSave = async () => {
    setStep('saving')
    setError(null)

    try {
      await saveReceipt({
        upload_id: uploadId,
        vendor_name: vendorName.trim() || 'Unknown Vendor',
        date: receiptDate || null,
        total: parseFloat(totalAmount) || 0.0,
        category: category,
        confidence: 'high',
        total_auto_corrected: false,
        items: items.map((it) => ({
          name: it.name || 'Item',
          quantity: parseFloat(it.quantity) || 1.0,
          unit_price: parseFloat(it.unit_price) || 0.0,
          total_price: parseFloat(it.total_price) || 0.0,
        })),
        raw_ocr_text: rawOcrText,
      })

      setStep('done')
    } catch (err) {
      console.error(err)
      setError(err?.response?.data?.detail || 'Failed to save receipt. Please try again.')
      setStep('review')
    }
  }

  if (step === 'done') {
    return (
      <div className="page-inner" style={{ padding: '30px 20px', textAlign: 'center' }}>
        <div style={styles.successIconWrap}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        </div>
        <h2 style={{ fontSize: '22px', fontWeight: '800', color: '#0f172a', marginBottom: '8px' }}>
          Receipt Saved!
        </h2>
        <p style={{ color: '#64748b', fontSize: '14px', marginBottom: '24px' }}>
          Your expense has been digitized and added to Khatascan.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button className="btn btn-primary" onClick={() => navigate('/')} style={{ justifyContent: 'center' }}>
            Back to Dashboard
          </button>
          <button
            className="btn"
            style={{ justifyContent: 'center', backgroundColor: '#f1f5f9', color: '#0f172a' }}
            onClick={() => {
              setStep('idle')
              setPreviewUrl(null)
            }}
          >
            Scan Another Receipt
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page-inner" style={{ padding: '16px 20px 24px' }}>
      {/* Top Header */}
      <div style={styles.header}>
        <button style={styles.backButton} onClick={() => navigate(-1)}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0f172a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <h2 style={styles.headerTitle}>Scan Receipt</h2>
        <div style={{ width: '38px' }} />
      </div>

      {error && (
        <div style={styles.errorBox}>
          <span style={{ fontSize: '13.5px', color: '#ef4444' }}>{error}</span>
        </div>
      )}

      {/* Step 1: Upload Prompt */}
      {step === 'idle' && (
        <div>
          <div style={styles.dropZone} onClick={() => fileInputRef.current?.click()}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />
            <div style={styles.cameraIconCircle}>
              <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
            </div>
            <h3 style={styles.dropTitle}>Take Photo or Upload Receipt</h3>
            <p style={styles.dropSub}>JPG, PNG, or HEIC &bull; Max 10 MB</p>
          </div>
        </div>
      )}

      {/* Step 2: Uploading Progress */}
      {step === 'uploading' && (
        <div style={styles.loadingCard}>
          {previewUrl && <img src={previewUrl} alt="Receipt preview" style={styles.previewImage} />}
          <h3 style={styles.loadingTitle}>Uploading Receipt...</h3>
          <div style={styles.progressBar}>
            <div style={{ ...styles.progressFill, width: `${uploadProgress}%` }} />
          </div>
          <span style={styles.progressPct}>{uploadProgress}%</span>
        </div>
      )}

      {/* Step 3: OCR Processing */}
      {step === 'processing' && (
        <div style={styles.loadingCard}>
          {previewUrl && <img src={previewUrl} alt="Receipt preview" style={styles.previewImage} />}
          <div className="spinner" style={{ margin: '16px 0 12px' }} />
          <h3 style={styles.loadingTitle}>Extracting Data with AI...</h3>
          <p style={styles.loadingSub}>Recognizing vendor, date, line items, and total</p>
        </div>
      )}

      {/* Step 4: Review and Confirm */}
      {(step === 'review' || step === 'saving') && (
        <div>
          {previewUrl && <img src={previewUrl} alt="Receipt" style={styles.reviewImage} />}

          <div style={styles.formCard}>
            <h3 style={styles.formTitle}>Review Extracted Details</h3>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Merchant Name</label>
              <input
                type="text"
                style={styles.fieldInput}
                value={vendorName}
                onChange={(e) => setVendorName(e.target.value)}
                placeholder="e.g. Super Mart"
              />
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Date</label>
              <input
                type="date"
                style={styles.fieldInput}
                value={receiptDate}
                onChange={(e) => setReceiptDate(e.target.value)}
              />
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Total Amount (₹)</label>
              <input
                type="number"
                step="0.01"
                style={styles.fieldInput}
                value={totalAmount}
                onChange={(e) => setTotalAmount(e.target.value)}
                placeholder="0.00"
              />
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.fieldLabel}>Category</label>
              <select
                style={styles.fieldInput}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            {/* Extracted Line Items */}
            {items.length > 0 && (
              <div style={styles.itemsBlock}>
                <label style={styles.fieldLabel}>Extracted Items ({items.length})</label>
                <div style={styles.itemsList}>
                  {items.map((it, idx) => (
                    <div key={idx} style={styles.itemRow}>
                      <span style={styles.itemTitle}>{it.name}</span>
                      <span style={styles.itemPrice}>₹{it.total_price || it.unit_price || 0}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: '16px', padding: '14px' }}
              onClick={handleSave}
              disabled={step === 'saving'}
            >
              {step === 'saving' ? 'Saving Receipt...' : 'Confirm & Save Receipt'}
            </button>
          </div>
        </div>
      )}
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
    backgroundColor: '#fef2f2',
    border: '1px solid #fee2e2',
    borderRadius: '14px',
    padding: '12px 16px',
    marginBottom: '16px',
  },
  dropZone: {
    backgroundColor: '#ffffff',
    border: '2px dashed #c7d2fe',
    borderRadius: '24px',
    padding: '48px 24px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    cursor: 'pointer',
  },
  cameraIconCircle: {
    width: '74px',
    height: '74px',
    borderRadius: '50%',
    backgroundColor: '#6366f1',
    backgroundImage: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 8px 20px rgba(99, 102, 241, 0.35)',
    marginBottom: '16px',
  },
  dropTitle: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '6px',
  },
  dropSub: {
    fontSize: '13px',
    color: '#94a3b8',
  },
  loadingCard: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '24px 20px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  previewImage: {
    width: '100%',
    maxHeight: '220px',
    objectFit: 'contain',
    borderRadius: '16px',
    marginBottom: '16px',
  },
  loadingTitle: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '6px',
  },
  loadingSub: {
    fontSize: '13px',
    color: '#94a3b8',
  },
  progressBar: {
    width: '100%',
    height: '8px',
    backgroundColor: '#f1f5f9',
    borderRadius: '9999px',
    overflow: 'hidden',
    marginTop: '16px',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#6366f1',
    borderRadius: '9999px',
    transition: 'width 0.2s',
  },
  progressPct: {
    fontSize: '12px',
    color: '#64748b',
    marginTop: '6px',
    fontWeight: '600',
  },
  reviewImage: {
    width: '100%',
    maxHeight: '180px',
    objectFit: 'contain',
    borderRadius: '16px',
    marginBottom: '14px',
    backgroundColor: '#0f172a',
  },
  formCard: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '20px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.03)',
  },
  formTitle: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '16px',
  },
  fieldGroup: {
    marginBottom: '14px',
  },
  fieldLabel: {
    display: 'block',
    fontSize: '12.5px',
    fontWeight: '600',
    color: '#64748b',
    marginBottom: '6px',
  },
  fieldInput: {
    width: '100%',
    padding: '11px 14px',
    borderRadius: '12px',
    border: '1.5px solid #e2e8f0',
    fontSize: '14.5px',
    color: '#0f172a',
    backgroundColor: '#f8fafc',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
    outline: 'none',
  },
  itemsBlock: {
    marginTop: '12px',
    marginBottom: '12px',
  },
  itemsList: {
    backgroundColor: '#f8fafc',
    borderRadius: '12px',
    padding: '8px 12px',
  },
  itemRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    borderBottom: '1px solid #e2e8f0',
    fontSize: '13px',
  },
  itemTitle: {
    color: '#334155',
    fontWeight: '500',
  },
  itemPrice: {
    color: '#0f172a',
    fontWeight: '700',
  },
  successIconWrap: {
    width: '72px',
    height: '72px',
    borderRadius: '50%',
    backgroundColor: '#dcfce7',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '16px',
  },
}
