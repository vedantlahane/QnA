import React from 'react';
import Header from './Header';
import ChatDisplay from './ChatDisplay';
import InputSection from './InputSection';

interface MainPanelProps {
  currentView: 'chat' | 'history';
  onViewChange: (view: 'chat' | 'history') => void;
}

const MainPanel: React.FC<MainPanelProps> = ({ currentView, onViewChange }) => {
  return (
    <div className="flex flex-1 flex-col bg-[radial-gradient(ellipse_at_top,_rgba(30,45,85,0.25),_transparent_65%)]">
      <Header currentView={currentView} onViewChange={onViewChange} />
      <div className="flex-1 overflow-y-auto">
        <ChatDisplay view={currentView} />
      </div>
      <InputSection />
    </div>
  );
};

export default MainPanel;
