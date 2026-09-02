import { useEffect, useRef, useState } from 'react'
import IconButton from '../common/IconButton'

export default function MessageComposer({ onSend, disabled = false, replyTo = null, onCancelReply }) {
  const [content, setContent] = useState('')
  const [files, setFiles] = useState([])
  const [error, setError] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [voicePreview, setVoicePreview] = useState(null)
  const recorderRef = useRef(null)
  const streamRef = useRef(null)

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    if (voicePreview?.url) URL.revokeObjectURL(voicePreview.url)
  }, [voicePreview])

  const clearVoicePreview = () => {
    if (voicePreview?.url) URL.revokeObjectURL(voicePreview.url)
    setVoicePreview(null)
  }

  const startRecording = async () => {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Voice recording is not supported by this browser')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm'].find((type) => MediaRecorder.isTypeSupported(type))
      if (!mimeType) {
        stream.getTracks().forEach((track) => track.stop())
        setError('This browser cannot record WebM audio')
        return
      }
      const chunks = []
      const recorder = new MediaRecorder(stream, { mimeType })
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data)
      }
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunks, { type: 'audio/webm' })
        if (blob.size === 0) {
          setError('No audio was captured')
          return
        }
        clearVoicePreview()
        const file = new File([blob], `voice-${Date.now()}.webm`, { type: 'audio/webm' })
        setVoicePreview({ file, url: URL.createObjectURL(blob) })
      }
      streamRef.current = stream
      recorderRef.current = recorder
      recorder.start()
      setIsRecording(true)
    } catch (recordingError) {
      setError(recordingError?.name === 'NotAllowedError' ? 'Microphone permission was denied' : 'Unable to start microphone recording')
    }
  }

  const stopRecording = () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    setIsRecording(false)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const outgoingFiles = voicePreview ? [voicePreview.file] : files
    if ((!content.trim() && outgoingFiles.length === 0) || disabled || isRecording) return
    setError('')
    try {
      await onSend(content, replyTo, outgoingFiles, voicePreview ? 'audio' : 'text')
      setContent('')
      setFiles([])
      clearVoicePreview()
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'Unable to send message')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border p-3 flex flex-col gap-2 flex-shrink-0">
      {replyTo && (
        <div className="flex items-center gap-2 bg-surface-elevated border border-border rounded-lg px-3 py-2">
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-primary truncate">{replyTo.is_deleted ? 'Deleted message' : 'Replying to message'}</div>
            <div className="text-xs text-text-muted truncate">{replyTo.content_encrypted}</div>
          </div>
          <button type="button" onClick={onCancelReply} className="icon-btn !p-1 text-xs" title="Cancel reply" aria-label="Cancel reply">x</button>
        </div>
      )}
      <div className="flex items-end gap-2">
        <IconButton label="Emoji" disabled title="Emoji picker coming soon">:</IconButton>
        <label className="icon-btn cursor-pointer" title="Attach encrypted image">
          <span aria-hidden="true">+</span>
          <input type="file" accept="image/png,image/jpeg,image/webp" multiple className="hidden" disabled={disabled} onChange={(event) => setFiles(Array.from(event.target.files || []))} />
        </label>
        <IconButton label={isRecording ? 'Stop recording' : 'Record voice message'} disabled={disabled} title={isRecording ? 'Stop recording' : 'Record voice message'} onClick={isRecording ? stopRecording : startRecording}>
          {isRecording ? 'Stop' : 'Voice'}
        </IconButton>
        <textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder={replyTo ? 'Reply...' : 'Type a message...'} className="input-base flex-1 resize-none" rows={1} disabled={disabled} aria-label="Message" onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            handleSubmit(event)
          }
        }} />
        <button type="submit" className="btn-primary !px-3 !py-2" disabled={(!content.trim() && files.length === 0 && !voicePreview) || disabled || isRecording} aria-label="Send message">Send</button>
      </div>
      {files.length > 0 && <div className="text-xs text-text-muted truncate">{files.map((file) => file.name).join(', ')}</div>}
      {isRecording && <div className="text-xs text-danger">Recording voice message...</div>}
      {voicePreview && <div className="flex items-center gap-2 text-xs text-text-muted"><audio controls src={voicePreview.url} aria-label="Voice message preview" /><button type="button" className="icon-btn !p-1" onClick={clearVoicePreview} aria-label="Discard voice message" title="Discard voice message">x</button></div>}
      {error && <div className="text-xs text-danger" role="alert">{error}</div>}
    </form>
  )
}
