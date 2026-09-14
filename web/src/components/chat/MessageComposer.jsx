import { useEffect, useRef, useState } from 'react'
import IconButton from '../common/IconButton'
import { EmojiIcon, AttachIcon, MicIcon, StopIcon, SendIcon, CloseIcon, FileIcon } from '../icons'

export default function MessageComposer({ onSend, disabled = false, replyTo = null, onCancelReply }) {
  const [content, setContent] = useState('')
  const [files, setFiles] = useState([])
  const [error, setError] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [voicePreview, setVoicePreview] = useState(null)
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const textareaRef = useRef(null)

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

  const canSend = (content.trim() || files.length > 0 || Boolean(voicePreview)) && !disabled && !isRecording

  const autoGrow = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border p-3 flex flex-col gap-2 flex-shrink-0">
      {replyTo && (
        <div className="flex items-center gap-2 glass rounded-xl px-3 py-2 panel-enter">
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-accent truncate">{replyTo.is_deleted ? 'Deleted message' : 'Replying…'}</div>
            <div className="text-xs text-text-muted truncate">{replyTo.content_decrypted || replyTo.content_encrypted || ''}</div>
          </div>
          <button type="button" onClick={onCancelReply} className="icon-btn !w-7 !h-7" title="Cancel reply" aria-label="Cancel reply">
            <CloseIcon className="w-4 h-4" />
          </button>
        </div>
      )}
      <div className="flex items-end gap-2">
        <IconButton label="Emoji" disabled title="Emoji picker coming soon" className="!w-9 !h-9 rounded-full">
          <EmojiIcon className="w-5 h-5" />
        </IconButton>
        <label className="icon-btn !w-9 !h-9 rounded-full cursor-pointer" title="Attach encrypted image">
          <AttachIcon className="w-5 h-5" />
          <input type="file" accept="image/png,image/jpeg,image/webp" multiple className="hidden" disabled={disabled} onChange={(event) => setFiles(Array.from(event.target.files || []))} />
        </label>
        <IconButton
          label={isRecording ? 'Stop recording' : 'Record voice message'}
          disabled={disabled}
          title={isRecording ? 'Stop recording' : 'Record voice message'}
          onClick={isRecording ? stopRecording : startRecording}
          className={`!w-9 !h-9 rounded-full ${isRecording ? '!text-danger' : ''}`}
        >
          {isRecording ? <StopIcon className="w-4 h-4" /> : <MicIcon className="w-5 h-5" />}
        </IconButton>
        <div className="flex-1 min-w-0">
          <textarea
            ref={textareaRef}
            value={content}
            onChange={(event) => { setContent(event.target.value); autoGrow() }}
            placeholder={replyTo ? 'Reply…' : 'Type a message…'}
            className="input-base flex-1 resize-none rounded-2xl py-2.5 pl-4 pr-4 max-h-40"
            rows={1}
            disabled={disabled}
            aria-label="Message"
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                handleSubmit(event)
              }
            }}
          />
        </div>
        <button
          type="submit"
          className="btn-primary !px-3 !py-2 !rounded-full !w-11 !h-11 shrink-0 flex items-center justify-center"
          disabled={!canSend}
          aria-label="Send message"
          title="Send message"
        >
          <SendIcon className="w-5 h-5" />
        </button>
      </div>
      {files.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <FileIcon className="w-3.5 h-3.5" />
          <span className="truncate">{files.map((file) => file.name).join(', ')}</span>
        </div>
      )}
      {isRecording && (
        <div className="flex items-center gap-2 text-xs text-danger">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-danger opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-danger" />
          </span>
          Recording voice message…
        </div>
      )}
      {voicePreview && (
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <audio controls src={voicePreview.url} aria-label="Voice message preview" className="h-9 max-w-[220px]" />
          <button type="button" className="icon-btn !w-7 !h-7" onClick={clearVoicePreview} aria-label="Discard voice message" title="Discard voice message">
            <CloseIcon className="w-4 h-4" />
          </button>
        </div>
      )}
      {error && <div className="text-xs text-danger" role="alert">{error}</div>}
    </form>
  )
}