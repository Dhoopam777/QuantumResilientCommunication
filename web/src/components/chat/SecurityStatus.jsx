import { useState } from 'react'
import { ShieldCheckIcon, ChevronDownIcon, ChevronUpIcon, AlertIcon } from '../icons'

const TECHNOLOGY = [
  { name: 'AES-256-GCM', role: 'Encrypts message content', stateKey: 'encryption' },
  { name: 'HKDF-SHA256', role: 'Derives the encryption/session key material', stateKey: 'session' },
  { name: 'ML-KEM-768', role: 'Post-quantum key establishment', stateKey: 'session' },
  { name: 'ML-DSA-65', role: 'Post-quantum digital signature / authenticity', stateKey: 'signature' },
  { name: 'SHA-256', role: 'Integrity verification', stateKey: 'integrity' },
]

function TechRow({ name, role, ok }) {
  const dot = ok ? 'bg-success' : (ok === 'active' ? 'bg-success' : 'bg-warning')
  const label = ok ? 'Active' : 'Standby'
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors">
      <div className="min-w-0">
        <div className="text-sm font-semibold text-text-primary">
          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${dot}`} />
          {name}
        </div>
        <div className="text-xs text-text-muted truncate">{role}</div>
      </div>
      <span className={`sec-chip ${ok ? 'good' : 'warn'}`}>{label}</span>
    </div>
  )
}

function toStatus(value) {
  // value: string | boolean — normalize to "active" / "standby"
  if (value === 'verified' || value === true) return 'active'
  return 'standby'
}

export default function SecurityStatus({ user, authenticated, sessionReady, messages }) {
  const [expanded, setExpanded] = useState(false)

  const latest = [...messages].reverse().find((message) => !message.is_deleted)
  const signatureVerified = latest?.signature_status === 'verified'
  const integrityVerified = latest?.integrity_status === 'verified'
  const encryptionActive = Boolean(latest?.encryption_version === 'AES-256-GCM' || latest?.attachments?.length)

  const allActive = authenticated && sessionReady && signatureVerified && integrityVerified && encryptionActive

  return (
    <section className="border-b border-border bg-surface/60 backdrop-blur-md px-4 py-2" aria-label="Security and encryption status">
      {/* Header row — the always-visible "trust line" */}
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setExpanded((exp) => !exp)}
          className="flex items-center gap-2 text-left group"
          aria-expanded={expanded}
          aria-label="Toggle security details"
        >
          <span className={`flex items-center justify-center w-7 h-7 rounded-full ${
            allActive ? 'bg-success/15 text-success' : 'bg-warning/15 text-warning'
          }`}>
            {allActive ? <ShieldCheckIcon className="w-4 h-4" /> : <AlertIcon className="w-4 h-4" />}
          </span>
          <span className="flex flex-col">
            <span className="text-sm font-semibold text-text-primary">End-to-End Encrypted</span>
            <span className="text-[11px] text-text-muted">
              {allActive
                ? 'Message content, identity and integrity are protected.'
                : 'Session establishing — protections activate when a secure session is ready.'}
            </span>
          </span>
        </button>
        <button
          type="button"
          onClick={() => setExpanded((exp) => !exp)}
          className="icon-btn !w-8 !h-8"
          aria-label={expanded ? 'Hide security details' : 'Show security details'}
          title={expanded ? 'Hide security details' : 'Show security details'}
        >
          {expanded ? <ChevronUpIcon className="w-4 h-4" /> : <ChevronDownIcon className="w-4 h-4" />}
        </button>
      </div>

      {/* Expandable panel */}
      {expanded && (
        <div className="mt-3 grid gap-1 panel-enter">
          <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-surface-hover">
            <span className="text-sm font-medium text-text-primary">Session</span>
            <span className={`sec-chip ${sessionReady ? 'good' : 'warn'}`}>
              {sessionReady ? 'Established' : 'Pending'}
            </span>
          </div>
          <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-surface-hover">
            <span className="text-sm font-medium text-text-primary">Signature</span>
            <span className={`sec-chip ${signatureVerified ? 'good' : 'warn'}`}>
              {signatureVerified ? 'Verified on latest message' : 'Awaiting verified message'}
            </span>
          </div>
          <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-surface-hover">
            <span className="text-sm font-medium text-text-primary">Integrity</span>
            <span className={`sec-chip ${integrityVerified ? 'good' : 'warn'}`}>
              {integrityVerified ? 'Verified on latest message' : 'Awaiting verified message'}
            </span>
          </div>
          <div className="my-1 border-t border-border" />
          {TECHNOLOGY.map((tech) => {
            let ok = toStatus(
              tech.stateKey === 'session' ? sessionReady
                : tech.stateKey === 'signature' ? signatureVerified
                  : tech.stateKey === 'integrity' ? integrityVerified
                    : encryptionActive
            )
            return <TechRow key={tech.name} name={tech.name} role={tech.role} ok={ok} />
          })}
        </div>
      )}
    </section>
  )
}
