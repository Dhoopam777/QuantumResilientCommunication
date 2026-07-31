import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import Register from './pages/Register'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ConversationList from './pages/ConversationList'
import CreateConversation from './pages/CreateConversation'
import ChatWindow from './pages/ChatWindow'
import TokenViewer from './pages/TokenViewer'
import Profile from './pages/Profile'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/test" element={<Navigate to="/test/register" replace />} />
            <Route path="/test/register" element={<Register />} />
            <Route path="/test/login" element={<Login />} />
            <Route path="/test/dashboard" element={<Dashboard />} />
            <Route path="/test/conversations" element={<ConversationList />} />
            <Route path="/test/conversations/new" element={<CreateConversation />} />
            <Route path="/test/conversations/:conversationId" element={<ChatWindow />} />
            <Route path="/test/profile" element={<Profile />} />
            <Route path="/test/tokens" element={<TokenViewer />} />
            <Route path="*" element={<Navigate to="/test" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AuthProvider>
  )
}