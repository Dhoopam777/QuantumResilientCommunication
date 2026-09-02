const Status = ({ label, value, ok }) => (
  <div className="flex items-center justify-between gap-3 text-xs">
    <span className="text-text-muted">{label}</span>
    <span className={ok ? 'text-success' : 'text-warning'}>{value}</span>
  </div>
)

export default function SecurityStatus({ user, authenticated, sessionReady, messages }) {
  const latest = [...messages].reverse().find((message) => !message.is_deleted)
  const signatureVerified = latest?.signature_status === 'verified'
  const integrityVerified = latest?.integrity_status === 'verified'
  const encryptedAttachment = latest?.attachments?.some((attachment) => attachment.encryption_algorithm === 'AES-256-GCM')

  return (
    <section className="border-b border-border bg-surface px-4 py-2" aria-label="Security and encryption status">
      <div className="grid gap-x-6 gap-y-1 sm:grid-cols-3">
        <div><div className="mb-1 text-xs font-semibold text-text-primary">Authentication</div><Status label="Email Verification" value={user?.is_email_verified ? 'Verified' : 'Not verified'} ok={Boolean(user?.is_email_verified)} /><Status label="Password Authentication" value={authenticated ? 'Verified' : 'Not authenticated'} ok={authenticated} /><Status label="JWT Session" value={authenticated ? 'Authenticated' : 'Not authenticated'} ok={authenticated} /></div>
        <div><div className="mb-1 text-xs font-semibold text-text-primary">PQC</div><Status label="Key Exchange" value={sessionReady ? 'ML-KEM-768' : 'Not established'} ok={sessionReady} /><Status label="Digital Signature" value={signatureVerified ? 'ML-DSA-65 verified' : 'Awaiting verified message'} ok={signatureVerified} /></div>
        <div><div className="mb-1 text-xs font-semibold text-text-primary">Message Security</div><Status label="Encryption" value={latest?.encryption_version === 'AES-256-GCM' ? 'AES-256-GCM' : 'No encrypted message'} ok={latest?.encryption_version === 'AES-256-GCM'} /><Status label="Integrity" value={integrityVerified ? 'SHA-256 verified' : 'Not verified'} ok={integrityVerified} /><Status label="Attachment" value={encryptedAttachment ? 'Encrypted to decrypted' : 'No encrypted attachment'} ok={Boolean(encryptedAttachment)} /></div>
      </div>
    </section>
  )
}
