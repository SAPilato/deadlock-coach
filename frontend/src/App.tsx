import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Matches from "./pages/Matches";
import MatchReport from "./pages/MatchReport";
import Trends from "./pages/Trends";
import Settings from "./pages/Settings";
import BuildLab from "./pages/BuildLab";
import MacroMap from "./pages/MacroMap";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/matches/:id" element={<MatchReport />} />
        <Route path="/trends" element={<Trends />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/build" element={<BuildLab />} />
        <Route path="/map" element={<MacroMap />} />
      </Routes>
    </Layout>
  );
}
