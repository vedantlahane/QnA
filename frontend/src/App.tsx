import { useState } from "react";
import { ChatWindow } from "./components/ChatWindow";
import { InputPanel } from "./components/InputPanel";
import { sendQuestion } from "./services/api";

interface message {
  role: "user" | "assistant";
  content: string;
}

function App() {
  const [messages, setMessages] = useState<message[]>([]);

  const handleSend = async (text: string) => {
    if (!text.trim()) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);

    const result = await sendQuestion(text);
    const responseData = await result.json();
    setMessages((prev) => [...prev, { role: "assistant", content: responseData.answer || "No response" }]);
  };

  return (
    <div className="max-w-xl mx-auto mt-10">
      <h1 className="text-2xl font-bold mb-4">🧠 QnA Chatbot</h1>
      <ChatWindow messages={messages} />
      <InputPanel onSend={handleSend} />
    </div>
  );
}

export default App;
