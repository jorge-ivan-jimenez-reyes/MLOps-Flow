import { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

function App() {
  const [rawData, setRawData] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('input')

  const sampleData = {
    "nombre": "Juan Carlos Perez Garcia",
    "fecha_nacimiento": "15/03/1985",
    "sexo": "M",
    "telefono": "555-1234",
    "email": "juan.perez@email.com",
    "direccion": "Calle Principal 123",
    "ciudad": "Ciudad de Mexico",
    "codigo_postal": "06600"
  }

  const handleSubmit = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = JSON.parse(rawData)
      const response = await axios.post(`${API_URL}/predict`, {
        raw_data: data,
        target_resource: 'Patient'
      })
      setResult(response.data)
      setActiveTab('output')
    } catch (err) {
      if (err.response) {
        setError(err.response.data.detail || 'Error del servidor')
      } else if (err.message.includes('JSON')) {
        setError('JSON invalido. Verifica el formato.')
      } else {
        setError('Error de conexion. Verifica que el servidor este corriendo.')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadSample = () => {
    setRawData(JSON.stringify(sampleData, null, 2))
  }

  return (
    <div className="min-h-screen p-6 md:p-10">
      {/* Header */}
      <header className="max-w-6xl mx-auto mb-10">
        <div className="flex items-center gap-4 mb-2">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">FHIR Automapper</h1>
            <p className="text-dark-400">Transforma datos clinicos a formato FHIR con IA</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Input Panel */}
          <div className="bg-dark-800/50 backdrop-blur-sm rounded-2xl border border-dark-700 overflow-hidden">
            <div className="flex border-b border-dark-700">
              <button
                onClick={() => setActiveTab('input')}
                className={`flex-1 px-6 py-4 text-sm font-medium transition-colors ${
                  activeTab === 'input' 
                    ? 'text-primary-400 border-b-2 border-primary-400 bg-dark-800/50' 
                    : 'text-dark-400 hover:text-dark-200'
                }`}
              >
                Datos de Entrada
              </button>
              <button
                onClick={() => setActiveTab('output')}
                className={`flex-1 px-6 py-4 text-sm font-medium transition-colors ${
                  activeTab === 'output' 
                    ? 'text-primary-400 border-b-2 border-primary-400 bg-dark-800/50' 
                    : 'text-dark-400 hover:text-dark-200'
                }`}
              >
                Resultado FHIR
              </button>
            </div>

            <div className="p-6">
              {activeTab === 'input' ? (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-medium text-dark-300">JSON de entrada</label>
                    <button
                      onClick={loadSample}
                      className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                    >
                      Cargar ejemplo
                    </button>
                  </div>
                  <textarea
                    value={rawData}
                    onChange={(e) => setRawData(e.target.value)}
                    placeholder='{"nombre": "Juan Perez", "fecha_nacimiento": "1985-03-15", ...}'
                    className="w-full h-80 p-4 bg-dark-900 border border-dark-600 rounded-xl text-dark-100 font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 placeholder-dark-500"
                  />
                  
                  {error && (
                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm animate-slide-up">
                      {error}
                    </div>
                  )}

                  <button
                    onClick={handleSubmit}
                    disabled={loading || !rawData.trim()}
                    className={`w-full py-4 rounded-xl font-semibold text-white transition-all ${
                      loading || !rawData.trim()
                        ? 'bg-dark-600 cursor-not-allowed'
                        : 'bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-primary-400 animate-pulse-glow'
                    }`}
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Transformando...
                      </span>
                    ) : (
                      'Transformar a FHIR'
                    )}
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {result ? (
                    <div className="animate-slide-up">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-primary-500"></div>
                          <span className="text-sm text-dark-300">
                            Confianza: <span className="text-primary-400 font-semibold">{(result.confidence * 100).toFixed(0)}%</span>
                          </span>
                        </div>
                        <span className="text-xs text-dark-500">
                          {result.processing_time_ms?.toFixed(0)}ms | {result.model_version}
                        </span>
                      </div>
                      <pre className="w-full h-72 p-4 bg-dark-900 border border-dark-600 rounded-xl text-dark-100 font-mono text-sm overflow-auto">
                        {JSON.stringify(result.fhir_json, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div className="h-80 flex items-center justify-center text-dark-500">
                      <div className="text-center">
                        <svg className="w-16 h-16 mx-auto mb-4 text-dark-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p>El resultado FHIR aparecera aqui</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Info Panel */}
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-dark-800/50 backdrop-blur-sm rounded-2xl border border-dark-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Estado del Sistema</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-dark-400">Gateway API</span>
                  <span className="flex items-center gap-2 text-primary-400">
                    <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse"></span>
                    Activo
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-dark-400">ML Inference</span>
                  <span className="flex items-center gap-2 text-primary-400">
                    <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse"></span>
                    Activo
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-dark-400">Modelo</span>
                  <span className="text-dark-300">Mock Mode</span>
                </div>
              </div>
            </div>

            {/* Supported Fields */}
            <div className="bg-dark-800/50 backdrop-blur-sm rounded-2xl border border-dark-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Campos Soportados</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {['nombre', 'fecha_nacimiento', 'sexo', 'telefono', 'email', 'direccion', 'ciudad', 'codigo_postal'].map(field => (
                  <div key={field} className="flex items-center gap-2 text-dark-400">
                    <svg className="w-4 h-4 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {field}
                  </div>
                ))}
              </div>
            </div>

            {/* FHIR Info */}
            <div className="bg-gradient-to-br from-primary-900/30 to-dark-800/50 backdrop-blur-sm rounded-2xl border border-primary-700/30 p-6">
              <h3 className="text-lg font-semibold text-white mb-2">Sobre FHIR</h3>
              <p className="text-dark-300 text-sm leading-relaxed">
                FHIR (Fast Healthcare Interoperability Resources) es el estandar internacional 
                para intercambio de datos de salud. Este sistema convierte automaticamente 
                tus datos clinicos al formato Patient de FHIR R4.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto mt-10 text-center text-dark-500 text-sm">
        <p>FHIR Automapper - MLOps Flow</p>
      </footer>
    </div>
  )
}

export default App

