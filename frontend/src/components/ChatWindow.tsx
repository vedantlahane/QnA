import {Card} from "@/components/ui/card";


interface message {
    role: "user"  | "assistant";
    content: string;
}

export function ChatWindow({messages} : {messages: message[]}) {
    return (
        <div className="flex flex-col h-full">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, index) => (
                    <Card key={index} className={`p-4 ${msg.role === "user" ? "bg-blue-100" : "bg-green-100"}`}>
                        <div className="text-sm font-semibold">{msg.role}</div>
                        <div className="text-base">{msg.content}</div>
                    </Card>
                ))}
            </div>
        </div>
    );
}