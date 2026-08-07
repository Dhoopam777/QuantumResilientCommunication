import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import Register from './pages/Register'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CreateConversation from './pages/CreateConversation'
import ChatPage from './pages/ChatPage'
import Profile from './pages/Profile'
import TokenViewer from './pages/TokenViewer'
import ConversationRequests from './pages/ConversationRequests'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/test" element={<Navigate to="/test/chat" replace />} />
          <Route path="/test/register" element={<Layout><Register /></Layout>} />
          <Route path="/test/login" element={<Layout><Login /></Layout>} />
          <Route path="/test/dashboard" element={<Navigate to="/test/chat" replace />} />
          <Route path="/test/chat" element={<ChatPage />} />
          <Route path="/test/chat/:conversationId" element={<ChatPage />} />
          <Route path="/test/chat/:conversationId/details" element={<ChatPage />} />
          <Route path="/test/conversations/new" element={<Layout><CreateConversation /></Layout>} />
          <Route path="/test/profile" element={<Profile />} />
          <Route path="/test/requests" element={<ConversationRequests />} />
          <Route path="/test/tokens" element={<Layout><TokenViewer /></Layout>} />
          <Route path="*" element={<Navigate to="/test" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}