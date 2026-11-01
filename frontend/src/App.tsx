import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppProvider } from "./state/AppContext.js";
import { Layout } from "./components/Layout.js";
import { Dashboard } from "./pages/Dashboard.js";
import { DataManagement } from "./pages/DataManagement.js";
import { Generate } from "./pages/Generate.js";
import { Viewer } from "./pages/Viewer.js";
import { Validation } from "./pages/Validation.js";
import { Comparison } from "./pages/Comparison.js";
import { Repair } from "./pages/Repair.js";
import { Landing } from "./pages/Landing.js";

export function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="*" element={<Layout><Routes>
            <Route path="/workspace" element={<Dashboard />} />
            <Route path="/data" element={<DataManagement />} />
            <Route path="/generate" element={<Generate />} />
            <Route path="/viewer" element={<Viewer />} />
            <Route path="/validation" element={<Validation />} />
            <Route path="/comparison" element={<Comparison />} />
            <Route path="/repair" element={<Repair />} />
            <Route path="*" element={<Dashboard />} />
          </Routes></Layout>} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
