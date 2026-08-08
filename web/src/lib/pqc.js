import { ml_kem768 } from '@noble/post-quantum/ml-kem.js'
import { ml_dsa65 } from '@noble/post-quantum/ml-dsa.js'
import { cryptoApi } from './api'

const DB_NAME = 'qrc-device-keys'
const STORE = 'keys'
const ALGORITHM = 'ML-KEM-768+ML-DSA-65'
const textEncoder = new TextEncoder()

const b64 = (bytes) => {
  let value = ''
  bytes.forEach((byte) => { value += String.fromCharCode(byte) })
  return window.btoa(value)
}
const fromB64 = (value) => Uint8Array.from(window.atob(value), (char) => char.charCodeAt(0))

function openStore() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function readKeys() {
  const db = await openStore()
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE).objectStore(STORE).get('identity')
    request.onsuccess = () => resolve(request.result || null)
    request.onerror = () => reject(request.error)
  })
}

async function writeKeys(keys) {
  const db = await openStore()
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE, 'readwrite').objectStore(STORE).put(keys, 'identity')
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
  })
}

async function writeSession(id, key) {
  const db = await openStore()
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE, 'readwrite').objectStore(STORE).put(key, `session:${id}`)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
  })
}

async function readSession(id) {
  const db = await openStore()
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE).objectStore(STORE).get(`session:${id}`)
    request.onsuccess = () => resolve(request.result || null)
    request.onerror = () => reject(request.error)
  })
}

export async function ensureDeviceIdentity() {
  let keys = await readKeys()
  if (!keys) {
    const kem = ml_kem768.keygen()
    const signature = ml_dsa65.keygen()
    keys = {
      kemSecretKey: kem.secretKey,
      kemPublicKey: kem.publicKey,
      signatureSecretKey: signature.secretKey,
      signaturePublicKey: signature.publicKey,
    }
    await writeKeys(keys)
  }
  const response = await cryptoApi.uploadDeviceKeys({
    kem_public_key: b64(keys.kemPublicKey),
    signature_public_key: b64(keys.signaturePublicKey),
    algorithm_version: ALGORITHM,
  })
  if (response.status >= 400) throw new Error('Unable to register device keys')
  return keys
}

export async function encapsulateSession(publicKey) {
  const result = ml_kem768.encapsulate(fromB64(publicKey))
  return {
    ciphertext: b64(result.cipherText),
    sharedSecret: result.sharedSecret,
  }
}

export async function decapsulateSession(ciphertext) {
  const keys = await readKeys()
  if (!keys) throw new Error('Device keys unavailable')
  return ml_kem768.decapsulate(fromB64(ciphertext), keys.kemSecretKey)
}

export async function deriveSessionKey(sharedSecret, ciphertext) {
  const keyMaterial = await crypto.subtle.importKey('raw', sharedSecret, 'HKDF', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt: fromB64(ciphertext),
      info: textEncoder.encode('qrc/ml-kem-768/session/aes-256'),
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

export async function establishClientSession(username) {
  const publicResponse = await cryptoApi.publicKey(username)
  if (publicResponse.status !== 200) throw new Error('Recipient public key unavailable')
  const encapsulated = await encapsulateSession(publicResponse.data.kem_public_key)
  const sessionResponse = await cryptoApi.establishSession(username, {
    kem_ciphertext: encapsulated.ciphertext,
  })
  if (sessionResponse.status !== 201) throw new Error('Session establishment failed')
  const key = await deriveSessionKey(encapsulated.sharedSecret, encapsulated.ciphertext)
  await writeSession(sessionResponse.data.session_id, key)
  return key
}

export async function restoreSession(session) {
  const cached = await readSession(session.session_id)
  if (cached) return cached
  const sharedSecret = await decapsulateSession(session.kem_ciphertext)
  const key = await deriveSessionKey(sharedSecret, session.kem_ciphertext)
  await writeSession(session.session_id, key)
  return key
}

export async function encryptMessage(key, plaintext) {
  const nonce = crypto.getRandomValues(new Uint8Array(12))
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv: nonce, tagLength: 128 },
    key,
    textEncoder.encode(plaintext),
  ))
  return { ciphertext: b64(ciphertext.slice(0, -16)), nonce: b64(nonce), tag: b64(ciphertext.slice(-16)) }
}

export async function decryptMessage(key, ciphertext, nonce, tag) {
  const combined = new Uint8Array([...fromB64(ciphertext), ...fromB64(tag)])
  const plaintext = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: fromB64(nonce), tagLength: 128 },
    key,
    combined,
  )
  return new TextDecoder().decode(plaintext)
}

export async function signMessage(payload) {
  const keys = await readKeys()
  if (!keys) throw new Error('Device keys unavailable')
  const canonical = JSON.stringify(payload, Object.keys(payload).sort())
  return b64(ml_dsa65.sign(textEncoder.encode(canonical), keys.signatureSecretKey))
}

export { ALGORITHM }
