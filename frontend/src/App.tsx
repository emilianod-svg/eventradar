import { Home } from "./pages/Home";
import { EventDetailPage } from "./pages/EventDetailPage";
import "./styles/global.css";

export default function App() {
  const detailMatch = window.location.pathname.match(/^\/events\/([^/]+)$/);

  if (detailMatch) {
    return <EventDetailPage slug={decodeURIComponent(detailMatch[1])} />;
  }

  return <Home />;
}
