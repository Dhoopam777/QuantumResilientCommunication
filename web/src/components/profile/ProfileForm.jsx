import { useState } from 'react'
import Input from '../common/Input'
import TextArea from '../common/TextArea'
import Button from '../common/Button'

export default function ProfileForm({ user, onSave, saving = false }) {
  const [formData, setFormData] = useState({
    display_name: user?.display_name || '',
    bio: user?.bio || '',
    profile_picture_url: user?.profile_picture_url || '',
    status_message: user?.status_message || '',
  })

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-4">
      <h3 className="font-semibold text-sm text-text-primary">Edit Profile</h3>

      {/* Avatar upload UI (placeholder) */}
      <div>
        <label className="block text-xs font-medium text-text-secondary mb-1">Profile Picture</label>
        <div className="flex items-center gap-3">
          {formData.profile_picture_url ? (
            <img
              src={formData.profile_picture_url}
              alt="Profile"
              className="w-16 h-16 rounded-full object-cover border border-border"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-accent text-white flex items-center justify-center text-xl font-bold">
              {(user?.display_name || user?.username || '?').slice(0, 2).toUpperCase()}
            </div>
          )}
          <div className="flex-1">
            <Input
              name="profile_picture_url"
              value={formData.profile_picture_url}
              onChange={handleChange}
              placeholder="https://..."
              aria-label="Profile picture URL"
            />
            <p className="text-xs text-text-muted mt-1">Avatar upload coming soon</p>
          </div>
        </div>
      </div>

      <Input
        label="Display Name"
        name="display_name"
        value={formData.display_name}
        onChange={handleChange}
        placeholder="Display name shown to others"
      />

      <Input
        label="Status Message"
        name="status_message"
        value={formData.status_message}
        onChange={handleChange}
        placeholder="What's on your mind?"
        maxLength={200}
      />

      <TextArea
        label="Bio"
        name="bio"
        value={formData.bio}
        onChange={handleChange}
        placeholder="Tell us about yourself"
        rows={3}
      />

      <Button type="submit" disabled={saving}>
        {saving ? 'Saving...' : 'Save Profile'}
      </Button>
    </form>
  )
}