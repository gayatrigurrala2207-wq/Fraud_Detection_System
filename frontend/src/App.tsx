import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout, { NAVIGATION } from "./components/Layout";
import Health from "./pages/Health";
import Overview from "./pages/Overview";
import PlannedView from "./pages/PlannedView";
import Settings from "./pages/Settings";

const IMPLEMENTED: Record<string, ReactElement> = {
  "/": <Overview />,
  "/health": <Health />,
  "/settings": <Settings />,
};

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        {NAVIGATION.map((item) => (
          <Route
            key={item.path}
            path={item.path}
            element={IMPLEMENTED[item.path] ?? <PlannedView item={item} />}
          />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
