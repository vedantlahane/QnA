import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function InputPanel({ onSend }: { onSend: (message: string) => void }) {
  const [text, setText] = useState("");

  return (
    <div className="flex space-x-2 mt-4">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Ask your question..."
        onKeyDown={(e) => e.key === "Enter" && onSend(text)}
      />
      <Button onClick={() => onSend(text)}>Send</Button>
    </div>
  );
}
