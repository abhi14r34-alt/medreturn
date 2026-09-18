import { useEffect, useRef, useState } from 'react'
import { Camera, RotateCcw, Upload, X } from 'lucide-react'

export default function ImageCapture({ onCapture, onUpload, disabled = false }) {
  const inputRef = useRef(null)
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraError, setCameraError] = useState(null)

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  const closeCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setCameraOpen(false)
  }

  const openCamera = async () => {
    setCameraError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError('Camera access is unavailable. Use HTTPS or localhost, or upload a photo instead.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' } },
        audio: false,
      })
      streamRef.current = stream
      setCameraOpen(true)
      requestAnimationFrame(() => {
        if (videoRef.current) videoRef.current.srcObject = stream
      })
    } catch (error) {
      setCameraError(error.name === 'NotAllowedError'
        ? 'Camera permission was denied. Allow camera access or upload a photo instead.'
        : 'The camera could not be opened. Upload a photo instead.')
    }
  }

  const takePhoto = () => {
    const video = videoRef.current
    if (!video?.videoWidth || !video.videoHeight) return

    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob) return
      onCapture(new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' }))
      closeCamera()
    }, 'image/jpeg', 0.92)
  }

  const handleUpload = (event) => {
    const file = event.target.files?.[0]
    if (file) onUpload(file)
    event.target.value = ''
  }

  return (
    <div>
      <div className="row" style={{ flexWrap: 'wrap' }}>
        <button className="btn pri" type="button" onClick={openCamera} disabled={disabled || cameraOpen}>
          <Camera size={16} /> Use camera
        </button>
        <button className="btn" type="button" onClick={() => inputRef.current?.click()} disabled={disabled}>
          <Upload size={16} /> Upload photo
        </button>
        <input ref={inputRef} type="file" accept="image/*" hidden onChange={handleUpload} />
      </div>

      {cameraOpen && (
        <div className="camera-panel">
          <video ref={videoRef} autoPlay playsInline muted className="camera-video" />
          <div className="row" style={{ marginTop: 10, justifyContent: 'center' }}>
            <button className="btn pri" type="button" onClick={takePhoto}>
              <Camera size={16} /> Take photo
            </button>
            <button className="btn" type="button" onClick={closeCamera}>
              <X size={16} /> Cancel
            </button>
          </div>
        </div>
      )}

      {cameraError && (
        <div className="note" style={{ marginTop: 10 }}>
          <RotateCcw size={15} /> {cameraError}
        </div>
      )}
    </div>
  )
}