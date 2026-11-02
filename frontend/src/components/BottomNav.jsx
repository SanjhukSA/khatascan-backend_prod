import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// Figma design tokens from https://www.figma.com/community/file/1209593649566951455/bottom-navigation-bar
const ACTIVE_COLOR = '#0f172a'
const INACTIVE_COLOR = '#6b7f96'

function HomeIcon({ active }) {
  const color = active ? ACTIVE_COLOR : INACTIVE_COLOR
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path
        d="M3 10.5L12 3l9 7.5V20a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-9.5z"
        stroke={color}
        strokeWidth="1.85"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 22v-6a3 3 0 0 1 6 0v6"
        stroke={color}
        strokeWidth="1.85"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ReceiptsIcon({ active }) {
  const color = active ? ACTIVE_COLOR : INACTIVE_COLOR
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path
        d="M6 3.5h12v17l-2.2-1.5-1.8 1.5-2-1.5-2 1.5-1.8-1.5L6 20.5v-17z"
        stroke={color}
        strokeWidth="1.85"
        strokeLinejoin="round"
      />
      <path d="M9 8h6M9 12h6M9 16h3" stroke={color} strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  )
}

function CameraIcon({ active }) {
  const color = active ? ACTIVE_COLOR : INACTIVE_COLOR
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M4 7.5h3l1.5-2h7l1.5 2h3A1.5 1.5 0 0 1 21.5 9v9a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 18V9A1.5 1.5 0 0 1 4 7.5z" stroke={color} strokeWidth="1.85" strokeLinejoin="round" />
      <circle cx="12" cy="13" r="3.2" stroke={color} strokeWidth="1.85" />
    </svg>
  )
}

function AnalyticsIcon({ active }) {
  const color = active ? ACTIVE_COLOR : INACTIVE_COLOR
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M4 20V4M4 20h17" stroke={color} strokeWidth="1.85" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M7.5 16v-4M12 16V8M16.5 16v-6" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

function ProfileIcon({ active }) {
  const color = active ? ACTIVE_COLOR : INACTIVE_COLOR
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8.2" r="4.2" stroke={color} strokeWidth="1.85" />
      <path
        d="M4.5 20.2a7.5 7.5 0 0 1 15 0"
        stroke={color}
        strokeWidth="1.85"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default function BottomNav() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const tabs = [
    {
      id: 'home',
      label: 'Home',
      path: '/',
      isActive: pathname === '/',
      Icon: HomeIcon,
    },
    {
      id: 'feed',
      label: 'Receipts',
      path: '/receipts',
      isActive: pathname.startsWith('/receipts'),
      Icon: ReceiptsIcon,
    },
    {
      id: 'explore',
      label: '',
      ariaLabel: 'Scan receipt',
      path: '/scan',
      isActive: pathname === '/scan',
      Icon: CameraIcon,
    },
    {
      id: 'highlights',
      label: 'Analytics',
      path: '/analytics',
      isActive: pathname === '/analytics',
      Icon: AnalyticsIcon,
    },
    {
      id: 'profile',
      label: 'Profile',
      path: '/settings',
      isActive: pathname === '/settings',
      Icon: ProfileIcon,
    },
  ]

  return (
    <div style={styles.navContainer}>
      <nav style={styles.navBar}>
        {tabs.map((tab) => {
          const { Icon, isActive, label, ariaLabel, path, id } = tab
          return (
            <button
              key={id}
              style={styles.navButton}
              onClick={() => navigate(path)}
              aria-label={ariaLabel || label}
            >
              <div style={styles.iconWrapper}>
                <Icon active={isActive} />
              </div>
              <span
                aria-hidden={label ? undefined : 'true'}
                style={{
                  ...styles.navLabel,
                  color: isActive ? ACTIVE_COLOR : INACTIVE_COLOR,
                  fontWeight: isActive ? '600' : '400',
                  visibility: label ? 'visible' : 'hidden',
                }}
              >
                {label}
              </span>
            </button>
          )
        })}
      </nav>

      {/* iPhone Home Indicator */}
      <div style={styles.homeIndicatorWrapper}>
        <div style={styles.homeIndicator} />
      </div>
    </div>
  )
}

const styles = {
  navContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    width: '100%',
    backgroundColor: '#ffffff',
    borderTop: '1px solid #eef2f6',
    zIndex: 100,
    paddingBottom: 'env(safe-area-inset-bottom, 0px)',
    boxSizing: 'border-box',
    boxShadow: '0 -2px 10px rgba(15, 23, 42, 0.03)',
  },
  navBar: {
    height: '60px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-around',
    padding: '0 8px',
    boxSizing: 'border-box',
    width: '100%',
  },
  navButton: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '6px 0',
    minWidth: '0',
    transition: 'opacity 0.15s ease, transform 0.1s ease',
  },
  iconWrapper: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '26px',
    height: '26px',
  },
  navLabel: {
    fontSize: '12px',
    letterSpacing: '-0.1px',
    lineHeight: '1.2',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  },
  homeIndicatorWrapper: {
    height: '18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  homeIndicator: {
    width: '134px',
    height: '4.5px',
    backgroundColor: '#0f172a',
    borderRadius: '100px',
    opacity: 0.9,
  },
}
