import { Navigate, Route, Routes } from 'react-router-dom'

import { Loading } from './components/ui.jsx'
import DashboardLayout from './components/DashboardLayout.jsx'
import PublicLayout from './components/PublicLayout.jsx'
import { HOME_FOR_ROLE, useAuth } from './lib/auth.jsx'

import Landing from './pages/Landing.jsx'
import About from './pages/About.jsx'
import HowItWorks from './pages/HowItWorks.jsx'
import Safety from './pages/Safety.jsx'
import Contact from './pages/Contact.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'

import HouseholdDashboard from './pages/household/Dashboard.jsx'
import Analyzer from './pages/household/Analyzer.jsx'
import RequestPickup from './pages/household/RequestPickup.jsx'
import MyPickups from './pages/household/MyPickups.jsx'
import TrackPickup from './pages/household/TrackPickup.jsx'
import Credits from './pages/household/Credits.jsx'
import ReturnHistory from './pages/household/ReturnHistory.jsx'
import Profile from './pages/household/Profile.jsx'
import Notifications from './pages/Notifications.jsx'

import HospitalDashboard from './pages/hospital/Dashboard.jsx'
import WasteAnalyzer from './pages/hospital/WasteAnalyzer.jsx'
import Quarantine from './pages/hospital/Quarantine.jsx'
import Traceability from './pages/hospital/Traceability.jsx'
import BinStatus from './pages/hospital/BinStatus.jsx'
import ModelInfo from './pages/hospital/ModelInfo.jsx'

import AdminDashboard from './pages/admin/Dashboard.jsx'
import PickupManagement from './pages/admin/PickupManagement.jsx'
import Users from './pages/admin/Users.jsx'
import Hospitals from './pages/admin/Hospitals.jsx'
import CreditsAdmin from './pages/admin/CreditsAdmin.jsx'
import EmailLog from './pages/admin/EmailLog.jsx'
import SystemSettings from './pages/admin/SystemSettings.jsx'

import CollectorJobs from './pages/collector/Jobs.jsx'

/** Blocks a route until we know who is signed in, then checks the role. */
function Protected({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return <Loading label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={HOME_FOR_ROLE[user.role] || '/'} replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/about" element={<About />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/safety" element={<Safety />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      <Route
        element={
          <Protected roles={['household']}>
            <DashboardLayout section="household" />
          </Protected>
        }
      >
        <Route path="/app" element={<HouseholdDashboard />} />
        <Route path="/app/analyze" element={<Analyzer />} />
        <Route path="/app/request" element={<RequestPickup />} />
        <Route path="/app/pickups" element={<MyPickups />} />
        <Route path="/app/pickups/:pickupId" element={<TrackPickup />} />
        <Route path="/app/credits" element={<Credits />} />
        <Route path="/app/history" element={<ReturnHistory />} />
        <Route path="/app/notifications" element={<Notifications />} />
        <Route path="/app/profile" element={<Profile />} />
      </Route>

      <Route
        element={
          <Protected roles={['hospital', 'admin']}>
            <DashboardLayout section="hospital" />
          </Protected>
        }
      >
        <Route path="/hospital" element={<HospitalDashboard />} />
        <Route path="/hospital/analyze" element={<WasteAnalyzer />} />
        <Route path="/hospital/quarantine" element={<Quarantine />} />
        <Route path="/hospital/traceability" element={<Traceability />} />
        <Route path="/hospital/bins" element={<BinStatus />} />
        <Route path="/hospital/model" element={<ModelInfo />} />
        <Route path="/hospital/notifications" element={<Notifications />} />
      </Route>

      <Route
        element={
          <Protected roles={['admin']}>
            <DashboardLayout section="admin" />
          </Protected>
        }
      >
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/pickups" element={<PickupManagement />} />
        <Route path="/admin/users" element={<Users />} />
        <Route path="/admin/hospitals" element={<Hospitals />} />
        <Route path="/admin/credits" element={<CreditsAdmin />} />
        <Route path="/admin/emails" element={<EmailLog />} />
        <Route path="/admin/model" element={<ModelInfo />} />
        <Route path="/admin/settings" element={<SystemSettings />} />
      </Route>

      <Route
        element={
          <Protected roles={['collector', 'admin']}>
            <DashboardLayout section="collector" />
          </Protected>
        }
      >
        <Route path="/collector" element={<CollectorJobs />} />
        <Route path="/collector/notifications" element={<Notifications />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
