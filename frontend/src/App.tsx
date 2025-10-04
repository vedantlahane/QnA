import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import MainPanel from './components/MainPanel';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'chat' | 'history'>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen text-white bg-[#0a0e1a] bg-[radial-gradient(ellipse_at_top,_rgba(25,40,85,0.35),_transparent_70%)]">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <MainPanel
        currentView={currentView}
        onViewChange={setCurrentView}
      />
    </div>
  );
};

export default App;
