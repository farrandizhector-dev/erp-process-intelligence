import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import ExecutiveOverview from './pages/ExecutiveOverview'
import ProcessMap from './pages/ProcessMap'
import ComplianceCenter from './pages/ComplianceCenter'
import BottleneckExplorer from './pages/BottleneckExplorer'
import AutomationCandidates from './pages/AutomationCandidates'
import CaseDrilldown from './pages/CaseDrilldown'
import SubsidiaryBenchmark from './pages/SubsidiaryBenchmark'
import SlaRisk from './pages/SlaRisk'

export default function App() {
  return (
    <BrowserRouter basename="/erp-process-intelligence/">
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <div className="flex-1 ml-[220px] flex flex-col">
          <Header />
          <main className="flex-1 pt-12 p-6">
            <Routes>
              <Route path="/" element={<ExecutiveOverview />} />
              <Route path="/process-map" element={<ProcessMap />} />
              <Route path="/compliance" element={<ComplianceCenter />} />
              <Route path="/bottlenecks" element={<BottleneckExplorer />} />
              <Route path="/automation" element={<AutomationCandidates />} />
              <Route path="/cases" element={<CaseDrilldown />} />
              <Route path="/benchmarks" element={<SubsidiaryBenchmark />} />
              <Route path="/sla-risk" element={<SlaRisk />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
