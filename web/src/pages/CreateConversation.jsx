import { useAuth } from '../context/AuthContext'
import UserSearch from '../components/chat/UserSearch'

export default function CreateConversation() {
  const { isLoggedIn } = useAuth()

  if (!isLoggedIn) {
    return <p className="text-gray-500">Please log in first.</p>
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Start a conversation</h1>
        <p className="text-sm text-text-secondary mt-1">
          Search for another user by their username and send them a request.
          They can accept it to begin chatting — no IDs are needed.
        </p>
      </div>
      <div className="bg-surface border border-border rounded-xl p-4">
        <UserSearch />
      </div>
    </div>
  )
}
