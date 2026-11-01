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

export function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/data" element={<DataManagement />} />
            <Route path="/generate" element={<Generate />} />
            <Route path="/viewer" element={<Viewer />} />
            <Route path="/validation" element={<Validation />} />
            <Route path="/comparison" element={<Comparison />} />
            <Route path="/repair" element={<Repair />} />
            <Route path="*" element={<Dashboard />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
