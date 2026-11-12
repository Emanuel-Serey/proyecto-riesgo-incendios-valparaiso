import { StrictMode } from 'react'

import {
  createRoot
} from 'react-dom/client'

import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import 'leaflet/dist/leaflet.css'

import './index.css'

import App from './App.jsx'
import AdminReportes from './AdminReportes.jsx'
import ImagenAmpliable from './ImagenAmpliable.jsx'


createRoot(
  document.getElementById('root')
).render(

  <StrictMode>

    <BrowserRouter>

      <ImagenAmpliable />


      <Routes>

        <Route
          path="/"
          element={
            <App />
          }
        />


        <Route
          path="/admin"
          element={
            <AdminReportes />
          }
        />


        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />

      </Routes>

    </BrowserRouter>

  </StrictMode>,

)